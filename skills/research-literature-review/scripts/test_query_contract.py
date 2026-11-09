from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

# 先加载 review 模块，避免兼容检索入口修改 sys.path 后绑定到 search 的同名模块。
import query_contract  # noqa: E402
import pipeline_runner  # noqa: E402
import run_pipeline  # noqa: E402
import multi_query_search  # noqa: E402


def write_queries(path: Path, count: int = 5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "queries": [
            {"query": f"query {index}", "rationale": f"reason {index}"}
            for index in range(1, count + 1)
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class QuerySchemaTests(unittest.TestCase):
    def test_search_validator_isolated_from_review_query_contract(self) -> None:
        search_scripts = SKILL_ROOT.parent / "research-literature-search" / "scripts"
        probe = f"""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, {str(SCRIPT_DIR)!r})
import query_contract
sys.path.insert(0, {str(search_scripts)!r})
from search_runner import run_search

def provider(query, **kwargs):
    return [{{'id': 'W1', 'title': 'Valid paper', 'publication_year': 2024}}]

from validate_bundle import validate_bundle
tmp = tempfile.TemporaryDirectory()
root = Path(tmp.name)
queries = root / 'queries.json'
queries.write_text(json.dumps({{'queries': ['q1', 'q2', 'q3', 'q4', 'q5']}}))
bundle = root / 'bundle'
run_search(topic='topic', query_file=queries, output_dir=bundle, scope_root=root,
           provider_order=['openalex'], provider_functions={{'openalex': provider}})
assert validate_bundle(bundle) == []
tmp.cleanup()
"""
        completed = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_supported_json_shapes_are_normalized(self) -> None:
        cases = [
            {"queries": [{"query": " alpha ", "rationale": " why "}, "beta"]},
            [{"query": "alpha"}, "beta"],
            ["alpha", "beta"],
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            for index, payload in enumerate(cases):
                with self.subTest(index=index):
                    path = Path(tmpdir) / f"queries-{index}.json"
                    path.write_text(json.dumps(payload), encoding="utf-8")
                    plan = query_contract.load_query_plan(path, min_queries=2, max_queries=25)
                    self.assertEqual([item["query"] for item in plan.queries], ["alpha", "beta"])
                    self.assertEqual(plan.requested_count, 2)
                    self.assertEqual(plan.accepted_count, 2)

    def test_invalid_or_out_of_range_queries_fail_closed(self) -> None:
        cases = [
            ("", "无法解析"),
            ("{}", "queries"),
            ('{"queries": []}', "至少"),
            ('{"queries": ["", "  "]}', "至少"),
            ('{"queries": ["one"]}', "至少"),
            (json.dumps([f"q{i}" for i in range(26)]), "至多"),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            for index, (content, message) in enumerate(cases):
                with self.subTest(index=index):
                    path = Path(tmpdir) / f"invalid-{index}.json"
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaisesRegex(query_contract.QueryInputError, message):
                        query_contract.load_query_plan(path, min_queries=5, max_queries=25)

    def test_shared_output_stem_handles_spaces_slashes_and_chinese(self) -> None:
        for raw, expected in [
            ("alpha beta", "alpha-beta"),
            ("alpha/beta topic", "alphabeta-topic"),
            ("中文 主题", "中文-主题"),
            ("explicit stem", "explicit-stem"),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(query_contract.normalize_output_stem(raw), expected)
                self.assertEqual(run_pipeline._sanitize_topic(raw), expected)
                self.assertEqual(pipeline_runner.PipelineRunner._sanitize_topic_for_filename(raw), expected)

    def test_resume_identity_preserves_topic_and_explicit_output_stem(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir) / "opaque-run-id"
            state_path = work_dir / "output" / "pipeline_state.json"
            state_path.parent.mkdir(parents=True)
            state_path.write_text(
                json.dumps(
                    {
                        "topic": "中文 主题",
                        "file_stem": "explicit-stem",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            topic, stem = pipeline_runner._load_resume_identity(work_dir)
            self.assertEqual(topic, "中文 主题")
            self.assertEqual(stem, "explicit-stem")


class PipelineQueryInputTests(unittest.TestCase):
    def make_runner(
        self,
        work_dir: Path,
        *,
        topic: str = "alpha beta",
        output_stem: str | None = None,
        query_file: Path | None = None,
        allow_fallback: bool = False,
        fallback_reason: str | None = None,
    ) -> pipeline_runner.PipelineRunner:
        return pipeline_runner.PipelineRunner(
            topic=topic,
            domain="general",
            config_path=SKILL_ROOT / "config.yaml",
            work_dir=work_dir,
            review_level="basic",
            output_stem=output_stem,
            query_file=query_file,
            allow_single_query_fallback=allow_fallback,
            fallback_reason=fallback_reason,
        )

    @staticmethod
    def fake_search(script_name: str, args: list[str]) -> bool:
        output = Path(args[args.index("--output") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"id": "paper-1"}\n', encoding="utf-8")
        if script_name == "multi_query_search.py":
            search_log = Path(args[args.index("--search-log") + 1])
            search_log.write_text(
                json.dumps(
                    {
                        "search_mode": "multi_query",
                        "query_source": args[args.index("--query-source") + 1],
                        "requested_query_count": 5,
                        "accepted_query_count": 5,
                        "fallback_reason": "",
                    }
                ),
                encoding="utf-8",
            )
        return True

    def test_stage_zero_writes_query_template_and_prepare_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self.make_runner(Path(tmpdir) / "run")
            self.assertTrue(runner.run_stage_0_setup())
            template = runner.work_dir / "input" / "queries.json"
            self.assertTrue(template.exists())
            self.assertEqual(json.loads(template.read_text(encoding="utf-8")), {"queries": []})

    def test_explicit_query_file_is_staged_and_uses_multi_query_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "external queries.json"
            write_queries(source)
            runner = self.make_runner(root / "run", query_file=source)

            with patch.object(runner, "_run_script", side_effect=self.fake_search) as run_script:
                self.assertTrue(runner.run_stage_1_search())

            self.assertEqual(run_script.call_args.args[0], "multi_query_search.py")
            staged = runner.work_dir / "input" / "queries.json"
            self.assertTrue(staged.exists())
            self.assertEqual(runner.state.input_files["query_file"], str(staged))
            self.assertEqual(runner.state.search_mode, "multi_query")
            self.assertEqual(runner.state.accepted_query_count, 5)
            self.assertEqual(len(runner.state.query_file_sha256), 64)

    def test_each_supported_autodiscovery_location_uses_multi_query(self) -> None:
        locations = [
            lambda runner: runner.work_dir / "input" / "queries.json",
            lambda runner: runner.work_dir / "input" / f"queries_{runner.file_stem}.json",
            lambda runner: runner.artifacts_dir / f"queries_{runner.file_stem}.json",
            lambda runner: runner.artifacts_dir / "queries_alpha beta.json",
        ]
        for index, locate in enumerate(locations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as tmpdir:
                runner = self.make_runner(Path(tmpdir) / "run")
                write_queries(locate(runner))
                with patch.object(runner, "_run_script", side_effect=self.fake_search) as run_script:
                    self.assertTrue(runner.run_stage_1_search())
                self.assertEqual(run_script.call_args.args[0], "multi_query_search.py")
                self.assertEqual(runner.state.search_mode, "multi_query")

    def test_missing_queries_fail_closed_without_writing_papers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self.make_runner(Path(tmpdir) / "run")
            output = runner.artifacts_dir / f"papers_{runner.file_stem}.jsonl"
            with patch.object(runner, "_run_script") as run_script:
                self.assertFalse(runner.run_stage_1_search())
            run_script.assert_not_called()
            self.assertFalse(output.exists())

    def test_existing_papers_without_query_audit_do_not_complete_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self.make_runner(Path(tmpdir) / "run")
            papers = runner.artifacts_dir / "papers-existing.jsonl"
            papers.write_text('{"id": "paper-1"}\n', encoding="utf-8")
            runner.state.input_files["papers"] = str(papers)

            with patch.object(runner, "_run_script") as run_script:
                self.assertFalse(runner.run_stage_1_search())

            run_script.assert_not_called()
            self.assertNotIn("1_search", runner.state.completed_stages)

    def test_invalid_query_file_and_candidate_conflict_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self.make_runner(Path(tmpdir) / "invalid")
            invalid = runner.work_dir / "input" / "queries.json"
            invalid.write_text('{"queries": ["only one"]}', encoding="utf-8")
            with patch.object(runner, "_run_script") as run_script:
                self.assertFalse(runner.run_stage_1_search())
            run_script.assert_not_called()

            conflict = self.make_runner(Path(tmpdir) / "conflict")
            write_queries(conflict.work_dir / "input" / "queries.json")
            write_queries(conflict.artifacts_dir / f"queries_{conflict.file_stem}.json")
            with patch.object(conflict, "_run_script") as run_script:
                self.assertFalse(conflict.run_stage_1_search())
            run_script.assert_not_called()

    def test_single_query_requires_explicit_fallback_and_is_audited(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self.make_runner(
                Path(tmpdir) / "run",
                allow_fallback=True,
                fallback_reason="temporary orchestrator compatibility",
            )
            with patch.object(runner, "_run_script", side_effect=self.fake_search) as run_script:
                self.assertTrue(runner.run_stage_1_search())

            self.assertEqual(run_script.call_args.args[0], "openalex_search.py")
            self.assertEqual(runner.state.search_mode, "single_query")
            self.assertEqual(runner.state.fallback_reason, "temporary orchestrator compatibility")
            log = json.loads(Path(runner.state.output_files["search_log"]).read_text(encoding="utf-8"))
            self.assertEqual(log["search_mode"], "single_query")
            self.assertEqual(log["query_source"], "explicit_cli_fallback")
            self.assertEqual(log["accepted_query_count"], 1)
            self.assertTrue(log["warning"])

    def test_explicit_fallback_works_after_stage_zero_unfilled_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self.make_runner(
                Path(tmpdir) / "run",
                allow_fallback=True,
                fallback_reason="stage-zero compatibility",
            )
            self.assertTrue(runner.run_stage_0_setup())

            with patch.object(runner, "_run_script", side_effect=self.fake_search) as run_script:
                self.assertTrue(runner.run_stage_1_search())

            self.assertEqual(run_script.call_args.args[0], "openalex_search.py")
            self.assertEqual(runner.state.search_mode, "single_query")

    def test_resume_rejects_missing_or_changed_query_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "queries.json"
            write_queries(source)
            runner = self.make_runner(root / "run", query_file=source)
            with patch.object(runner, "_run_script", side_effect=self.fake_search):
                self.assertTrue(runner.run_stage_1_search())
            runner.save_state()

            staged = Path(runner.state.input_files["query_file"])
            write_queries(staged, count=6)
            resumed = self.make_runner(root / "run")
            self.assertFalse(resumed.run(resume_from=99))

            write_queries(staged, count=5)
            runner.state.query_file_sha256 = query_contract.sha256_file(staged)
            runner.save_state()
            staged.unlink()
            resumed = self.make_runner(root / "run")
            self.assertFalse(resumed.run(resume_from=99))

    def test_three_query_mock_dry_run_completes_stages_zero_to_two(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            config = json.loads(json.dumps(pipeline_runner.yaml.safe_load(
                (SKILL_ROOT / "config.yaml").read_text(encoding="utf-8")
            )))
            config["query_input"]["min_queries"] = 3
            config_path = root / "config.yaml"
            config_path.write_text(
                pipeline_runner.yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )
            query_file = root / "queries.json"
            write_queries(query_file, count=3)
            runner = pipeline_runner.PipelineRunner(
                topic="mock dry run",
                domain="general",
                config_path=config_path,
                work_dir=root / "run",
                review_level="basic",
                output_stem="mock dry run",
                query_file=query_file,
            )

            def fake_stage_script(script_name: str, args: list[str]) -> bool:
                if script_name == "multi_query_search.py":
                    result = self.fake_search(script_name, args)
                    log_path = Path(args[args.index("--search-log") + 1])
                    data = json.loads(log_path.read_text(encoding="utf-8"))
                    data["requested_query_count"] = 3
                    data["accepted_query_count"] = 3
                    log_path.write_text(json.dumps(data), encoding="utf-8")
                    return result
                if script_name == "dedupe_papers.py":
                    output = Path(args[args.index("--output") + 1])
                    mapping = Path(args[args.index("--map") + 1])
                    output.write_text('{"id": "paper-1"}\n', encoding="utf-8")
                    mapping.write_text("{}\n", encoding="utf-8")
                    return True
                return False

            with patch.object(runner, "_run_script", side_effect=fake_stage_script):
                self.assertTrue(runner.run_stage_0_setup())
                self.assertTrue(runner.run_stage_1_search())
                self.assertTrue(runner.run_stage_2_dedupe())

            self.assertEqual(runner.state.completed_stages, ["0_setup", "1_search", "2_dedupe"])
            self.assertEqual(runner.state.search_mode, "multi_query")
            self.assertEqual(runner.state.accepted_query_count, 3)


class MultiQuerySearchLogTests(unittest.TestCase):
    def test_three_query_mock_run_records_contract_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            query_file = root / "queries.json"
            write_queries(query_file, count=3)
            output = root / "papers.jsonl"
            search_log = root / "search-log.json"
            fake_papers = [{"id": "paper-1", "title": "A", "year": 2025}]

            argv = [
                "multi_query_search.py",
                "--queries",
                str(query_file),
                "--output",
                str(output),
                "--search-log",
                str(search_log),
                "--min-queries",
                "3",
                "--max-queries",
                "25",
                "--query-source",
                "mock-fixture",
                "--scope-root",
                str(root),
            ]
            with patch.object(sys, "argv", argv), patch.object(
                multi_query_search,
                "multi_search",
                return_value=(fake_papers, [], {}, {}),
            ):
                self.assertEqual(multi_query_search.main(), 0)

            data = json.loads(search_log.read_text(encoding="utf-8"))
            self.assertEqual(data["search_mode"], "multi_query")
            self.assertEqual(data["query_source"], "mock-fixture")
            self.assertEqual(data["requested_query_count"], 3)
            self.assertEqual(data["accepted_query_count"], 3)


if __name__ == "__main__":
    unittest.main()
