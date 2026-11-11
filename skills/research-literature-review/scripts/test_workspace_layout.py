from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LAYOUT = load_module("layout_paths", SKILL_ROOT / "scripts" / "layout_paths.py")
PUBLISH = load_module("publish_deliverables", SKILL_ROOT / "scripts" / "publish_deliverables.py")
RUNNER = load_module("pipeline_runner_layout", SKILL_ROOT / "scripts" / "pipeline_runner.py")
ORGANIZER = load_module("organize_run_dir_layout", SKILL_ROOT / "scripts" / "organize_run_dir.py")
CLEANLINESS = load_module("validate_workdir_cleanliness_layout", SKILL_ROOT / "scripts" / "validate_workdir_cleanliness.py")


class WorkspaceLayoutTests(unittest.TestCase):
    def test_runner_writes_declared_outputs_inside_internal_deliverables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir) / "run"
            runner = RUNNER.PipelineRunner(
                topic="layout test",
                domain="general",
                config_path=SKILL_ROOT / "config.yaml",
                work_dir=work_dir,
                review_level="basic",
                output_stem="layout-test",
            )
            output = runner._output_path("review_tex")
            self.assertEqual(output.parent, work_dir.resolve() / "output" / "deliverables" / "supporting")
            self.assertNotEqual(output.parent, work_dir.resolve())

    def test_runner_reads_legacy_checkpoint_layout_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir) / "run"
            legacy_state = work_dir / ".systematic-literature-review" / "pipeline_state.json"
            legacy_state.parent.mkdir(parents=True)
            legacy_state.write_text('{"topic": "legacy", "domain": "general"}', encoding="utf-8")

            runner = RUNNER.PipelineRunner(
                topic="layout test",
                domain="general",
                config_path=SKILL_ROOT / "config.yaml",
                work_dir=work_dir,
                review_level="basic",
                output_stem="layout-test",
            )

            self.assertEqual(runner._state_file(), legacy_state.resolve())
            self.assertEqual(runner._output_path("review_tex").parent, work_dir.resolve())

    def test_layout_uses_configured_hidden_dir_and_deliverables(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = LAYOUT.LayoutPaths.from_config(Path(tmpdir), {"layout": {"hidden_dir_name": "output"}})
            self.assertEqual(paths.hidden_dir, Path(tmpdir).resolve() / "output")
            self.assertEqual(paths.deliverables_dir, Path(tmpdir).resolve() / "output" / "deliverables")
            self.assertEqual(paths.artifacts_dir, Path(tmpdir).resolve() / "output" / "artifacts")

    def test_publish_copies_only_allowlisted_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source"
            target = root / "publish"
            source.mkdir()
            (source / "topic_review.pdf").write_bytes(b"pdf")
            (source / "topic_review.docx").write_bytes(b"docx")
            (source / "evidence_cards_topic.jsonl").write_text("{}\n", encoding="utf-8")

            with self.assertRaises(PUBLISH.PublishError):
                PUBLISH.publish_deliverables(source, target)

    def test_publish_succeeds_when_source_contains_only_core_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source"
            target = root / "publish"
            source.mkdir()
            (source / "topic_review.pdf").write_bytes(b"pdf")
            (source / "topic_review.docx").write_bytes(b"docx")

            result = PUBLISH.publish_deliverables(source, target)

            self.assertEqual(sorted(p.name for p in target.iterdir()), ["topic_review.docx", "topic_review.pdf"])
            self.assertEqual(result.published, ["topic_review.docx", "topic_review.pdf"])

    def test_publish_can_include_supporting_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source"
            target = root / "publish"
            source.mkdir()
            (source / "supporting").mkdir()
            (source / "topic_review.pdf").write_bytes(b"pdf")
            (source / "topic_review.docx").write_bytes(b"docx")
            (source / "supporting" / "topic_review.tex").write_text("% tex\n", encoding="utf-8")
            for name in ("topic_参考文献.bib", "topic_工作条件.md", "topic_验证报告.md"):
                (source / "supporting" / name).write_text("fixture\n", encoding="utf-8")

            PUBLISH.publish_deliverables(source, target, include_supporting=True)

            self.assertEqual(
                sorted(p.name for p in target.iterdir()),
                sorted(["topic_review.pdf", "topic_review.docx", "topic_review.tex", "references", "qc"]),
            )
            self.assertTrue((target / "references/topic_参考文献.bib").is_file())
            self.assertTrue((target / "qc/topic_工作条件.md").is_file())
            self.assertTrue((target / "qc/topic_验证报告.md").is_file())

    def test_publish_rejects_unexpected_existing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source = root / "source"
            target = root / "publish"
            source.mkdir()
            target.mkdir()
            (source / "topic_review.pdf").write_bytes(b"pdf")
            (target / "word_budget_final.csv").write_text("internal\n", encoding="utf-8")

            with self.assertRaises(PUBLISH.PublishError):
                PUBLISH.publish_deliverables(source, target)

    def test_organizer_uses_configured_hidden_dir_and_moves_budget_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir) / "run"
            work_dir.mkdir()
            leaked = work_dir / "word_budget_final.csv"
            leaked.write_text("internal\n", encoding="utf-8")

            moved = ORGANIZER.organize_run_dir(
                work_dir,
                {"layout": {"hidden_dir_name": "output"}},
                apply=True,
            )

            self.assertEqual(moved, ["word_budget_final.csv"])
            self.assertFalse(leaked.exists())
            self.assertTrue((work_dir / "output" / "artifacts" / leaked.name).exists())

    def test_publish_dir_cleanliness_rejects_intermediate_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            publish_dir = Path(tmpdir) / "publish"
            publish_dir.mkdir()
            (publish_dir / "topic_review.pdf").write_bytes(b"pdf")
            (publish_dir / "word_budget_final.csv").write_text("internal\n", encoding="utf-8")

            unexpected = CLEANLINESS.validate_publish_dir(publish_dir)

            self.assertEqual([path.name for path in unexpected], ["word_budget_final.csv"])


if __name__ == "__main__":
    unittest.main()
