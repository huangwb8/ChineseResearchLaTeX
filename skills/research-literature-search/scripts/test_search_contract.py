from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from candidate_schema import CandidateNormalizationError, SCHEMA_VERSION, adapt_legacy_record, normalize_record, validate_candidate  # noqa: E402
from normalize_papers import normalize_records  # noqa: E402
from query_contract import CONTRACT_VERSION, QueryInputError, load_query_plan  # noqa: E402
from search_runner import resolve_preprint_profile, run_search  # noqa: E402
from validate_bundle import validate_bundle  # noqa: E402
from dedupe_papers import dedupe_records  # noqa: E402
from search_runner import enrich_abstracts  # noqa: E402


class SearchContractTests(unittest.TestCase):
    def test_legacy_output_stems_normalizes_whitespace(self) -> None:
        from query_contract import legacy_output_stems, normalize_output_stem
        self.assertEqual(legacy_output_stems("a  b"), [])

    def test_string_publication_type_is_atomic(self) -> None:
        from search_runner import _filter_record
        record = {"year": 2024, "publication": {"publication_type": "review"}}
        self.assertTrue(_filter_record(record, {"publication_types": "review"}))

    def test_query_matches_input_is_not_mutated(self) -> None:
        from candidate_schema import normalize_record
        source = {"title": "x", "query_matches": ["q01"]}
        normalize_record(source, query_id="q02")
        self.assertEqual(source["query_matches"], ["q01"])
    def test_preprint_profile_is_domain_aware_without_excluding_records(self) -> None:
        name, policy = resolve_preprint_profile("computer science", "auto")
        self.assertEqual(name, "computer_science")
        self.assertEqual(policy["preprint_priority"], "high")
        name, policy = resolve_preprint_profile("clinical medicine", "auto")
        self.assertEqual(name, "medicine")
        self.assertEqual(policy["preprint_priority"], "low")

    def test_unknown_preprint_profile_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            resolve_preprint_profile("topic", "unknown")
    def test_priority_fallback_topup_uses_later_provider_only_when_needed(self) -> None:
        calls: list[str] = []

        def openalex(query: str, **_: object) -> list[dict[str, object]]:
            calls.append("openalex")
            return [{"id": f"W{i}", "title": f"A paper {i}", "publication_year": 2024} for i in range(10)]

        def semantic(query: str, **_: object) -> list[dict[str, object]]:
            calls.append("semantic_scholar")
            return [{"paperId": "S1", "title": "Another paper", "year": 2023}]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queries = root / "queries.json"
            queries.write_text(json.dumps({"queries": [f"q{i}" for i in range(5)]}), encoding="utf-8")
            manifest = run_search(
                topic="topic",
                query_file=queries,
                output_dir=root / "bundle",
                scope_root=root,
                provider_order=["openalex", "semantic_scholar"],
                max_results_per_query=2,
                provider_functions={"openalex": openalex, "semantic_scholar": semantic},
            )
            self.assertEqual(calls, ["openalex"] * 5)
            self.assertEqual(manifest["provider_policy"]["retrieval_strategy"], "priority-fallback-topup")
            self.assertEqual(manifest["provider_policy"]["topup_threshold"], 0.7)

    def test_priority_fallback_records_topup_attempt(self) -> None:
        def openalex(query: str, **_: object) -> list[dict[str, object]]:
            return []

        def semantic(query: str, **_: object) -> list[dict[str, object]]:
            return [{"paperId": "S1", "title": "A paper", "year": 2023}]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queries = root / "queries.json"
            queries.write_text(json.dumps({"queries": [f"q{i}" for i in range(5)]}), encoding="utf-8")
            manifest = run_search(
                topic="topic",
                query_file=queries,
                output_dir=root / "bundle",
                scope_root=root,
                provider_order=["openalex", "semantic_scholar"],
                max_results_per_query=2,
                provider_functions={"openalex": openalex, "semantic_scholar": semantic},
            )
            self.assertTrue(any(item["provider"] == "semantic_scholar" and item["status"] == "success" for item in manifest["attempts"]))
    def test_query_plan_adds_stable_ids_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queries.json"
            path.write_text(json.dumps({"queries": [" alpha ", {"query": "beta", "rationale": "why"}]}), encoding="utf-8")
            plan = load_query_plan(path, min_queries=2, max_queries=5)
            self.assertEqual([item["query_id"] for item in plan.queries], ["q01", "q02"])
            self.assertEqual(len(plan.sha256), 64)
            self.assertEqual(CONTRACT_VERSION, "rls.v1")

    def test_invalid_query_count_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "queries.json"
            path.write_text(json.dumps({"queries": ["one"]}), encoding="utf-8")
            with self.assertRaises(QueryInputError):
                load_query_plan(path)

    def test_legacy_adapter_is_explicitly_marked(self) -> None:
        record = adapt_legacy_record({"id": "old-1", "title": "A paper", "year": "2022"})
        self.assertEqual(record["schema_version"], SCHEMA_VERSION)
        self.assertIn("legacy_adapted", record["quality_warnings"])
        self.assertFalse(validate_candidate(record))

    def test_crossref_shape_is_normalized_at_single_boundary(self) -> None:
        record = normalize_record(
            {
                "title": ["Crossref title"],
                "container-title": ["Journal of Tests"],
                "published-print": {"date-parts": [[2021, 4, 2]]},
                "author": [{"given": "Ada", "family": "Lovelace"}],
                "DOI": "10.1000/crossref",
            },
            provider="crossref",
        )
        self.assertEqual(record["title"], "Crossref title")
        self.assertEqual(record["venue"], "Journal of Tests")
        self.assertEqual(record["year"], 2021)
        self.assertEqual(record["authors"], ["Ada Lovelace"])
        self.assertEqual(record["identifiers"]["doi"], "10.1000/crossref")

    def test_openalex_null_primary_source_preserves_candidate_with_warning(self) -> None:
        record = normalize_record(
            {
                "id": "https://openalex.org/W1",
                "title": "OpenAlex paper without a primary source",
                "publication_year": 2024,
                "primary_location": {"source": None},
            },
            provider="openalex",
        )
        self.assertIsNone(record["venue"])
        self.assertIn("missing_venue", record["quality_warnings"])
        self.assertFalse(validate_candidate(record))

    def test_batch_normalizer_skips_null_records_with_audit_issue(self) -> None:
        issues: list[dict[str, object]] = []
        records = normalize_records(
            [None, {"id": "W1", "title": "Valid paper", "publication_year": 2024}],
            provider="openalex",
            issues=issues,
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "Valid paper")
        self.assertEqual(issues[0]["code"], "empty_record")
        self.assertEqual(issues[0]["index"], 1)

    def test_batch_normalizer_skips_record_that_cannot_be_normalized(self) -> None:
        issues: list[dict[str, object]] = []
        records = normalize_records([{"id": "missing-title"}], provider="openalex", issues=issues)
        self.assertEqual(records, [])
        self.assertEqual(issues[0]["code"], "normalization_failed")

    def test_normalizing_null_raises_controlled_error(self) -> None:
        with self.assertRaises(CandidateNormalizationError) as caught:
            normalize_record(None)
        self.assertEqual(caught.exception.code, "empty_record")

    def test_runner_audits_mixed_empty_and_invalid_provider_records(self) -> None:
        def fake_openalex(query: str, **_: object) -> list[object]:
            return [None, "not-an-object", {"id": "W1", "title": "Valid paper", "publication_year": 2024}]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queries = root / "queries.json"
            queries.write_text(json.dumps({"queries": [f"q{i}" for i in range(5)]}), encoding="utf-8")
            manifest = run_search(
                topic="topic",
                query_file=queries,
                output_dir=root / "bundle",
                scope_root=root,
                provider_order=["openalex"],
                provider_functions={"openalex": fake_openalex},
            )
            self.assertEqual(manifest["counts"]["empty_records"], 5)
            self.assertEqual(manifest["counts"]["invalid_records"], 5)
            self.assertTrue(any("skipped" in warning for warning in manifest["warnings"]))
            self.assertEqual(manifest["status"], "partial_success")
            search_log = json.loads((root / "bundle" / "search_log.json").read_text(encoding="utf-8"))
            self.assertEqual(search_log["empty_records"], 5)
            self.assertEqual(search_log["invalid_records"], 5)

    def test_runner_reports_no_valid_candidates_for_all_null_records(self) -> None:
        def fake_openalex(query: str, **_: object) -> list[object]:
            return [None]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queries = root / "queries.json"
            queries.write_text(json.dumps({"queries": [f"q{i}" for i in range(5)]}), encoding="utf-8")
            manifest = run_search(
                topic="topic",
                query_file=queries,
                output_dir=root / "bundle",
                scope_root=root,
                provider_order=["openalex"],
                provider_functions={"openalex": fake_openalex},
            )
            self.assertEqual(manifest["status"], "failed")
            self.assertEqual(manifest["failure_code"], "no_valid_candidates")
            self.assertEqual(manifest["counts"]["empty_records"], 5)

    def test_offline_provider_run_writes_consumable_bundle(self) -> None:
        def fake_openalex(query: str, **_: object) -> list[dict[str, object]]:
            return [{"id": "W1", "title": "A shared paper", "publication_year": 2023, "doi": "https://doi.org/10.1000/test", "primary_location": {"source": None}}]

        def fake_semantic(query: str, **_: object) -> list[dict[str, object]]:
            return []

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queries = root / "queries.json"
            queries.write_text(json.dumps({"queries": [f"q{i}" for i in range(5)]}), encoding="utf-8")
            bundle = root / "bundle"
            manifest = run_search(topic="topic", query_file=queries, output_dir=bundle, scope_root=root, provider_order=["openalex"], provider_functions={"openalex": fake_openalex, "semantic_scholar": fake_semantic})
            self.assertIn(manifest["status"], {"success", "partial_success"})
            self.assertEqual(manifest["contract_version"], CONTRACT_VERSION)
            self.assertEqual(validate_bundle(bundle), [])
            self.assertTrue((bundle / "provenance.jsonl").exists())
            candidate = json.loads((bundle / "candidates_deduped.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertIn("missing_venue", candidate["quality_warnings"])

    def test_manifest_hash_tamper_and_unsafe_path_fail_closed(self) -> None:
        def fake_openalex(query: str, **_: object) -> list[dict[str, object]]:
            return [{"id": "W1", "title": "A study", "publication_year": 2024}]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queries = root / "queries.json"
            queries.write_text(json.dumps({"queries": [f"q{i}" for i in range(5)]}), encoding="utf-8")
            bundle = root / "bundle"
            run_search(topic="topic", query_file=queries, output_dir=bundle, scope_root=root, provider_order=["openalex"], provider_functions={"openalex": fake_openalex})
            manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
            (bundle / "candidates_deduped.jsonl").write_text("tampered\n", encoding="utf-8")
            self.assertTrue(any("hash mismatch" in error for error in validate_bundle(bundle)))
            manifest["artifacts"]["search_log"]["path"] = "../outside.json"
            (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            self.assertTrue(any("unsafe" in error or "escapes" in error for error in validate_bundle(bundle)))

    def test_output_path_violation_returns_structured_failure_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queries = root / "queries.json"
            queries.write_text(json.dumps({"queries": [f"q{i}" for i in range(5)]}), encoding="utf-8")
            result = run_search(topic="topic", query_file=queries, output_dir=root / "outside", scope_root=root / "allowed")
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["failure_code"], "path_violation")
            self.assertFalse((root / "outside").exists())

    def test_dedupe_merge_preserves_identifiers_from_both_records(self) -> None:
        def record(title: str, doi: str | None, rid: str, preprint: bool) -> dict[str, object]:
            row = normalize_record({"title": title, "year": 2024, "doi": doi, "id": rid, "venue": "arXiv" if preprint else "Journal", "publication": {"is_preprint": preprint}}, provider="openalex")
            return row

        canonical, edges = dedupe_records([
            record("A study of signals", None, "pre", True),
            record("A study of signals", "10.1000/published", "pub", False),
        ])
        self.assertEqual(len(canonical), 1)
        self.assertEqual(canonical[0]["identifiers"]["doi"], "10.1000/published")
        self.assertTrue(edges)
        self.assertEqual(edges[0]["reason"], "cross_doi_preprint_to_published")

    def test_enrichment_does_not_mark_successful_fill_as_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "selected.jsonl"
            target = root / "enriched.jsonl"
            source.write_text(json.dumps({"title": "A study", "abstract": "short", "quality_warnings": []}) + "\n", encoding="utf-8")

            def fake_source(query: str, **_: object) -> list[dict[str, object]]:
                return [{"abstract": "A sufficiently long abstract that is returned by the provider for this test."}]

            summary = enrich_abstracts(source, target, min_chars=20, fetchers={"semantic_scholar": fake_source})
            row = json.loads(target.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(summary["filled"], 1)
            self.assertNotIn("missing_abstract", row["quality_warnings"])


if __name__ == "__main__":
    unittest.main()
