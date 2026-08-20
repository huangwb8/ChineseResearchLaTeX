from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "pipeline_runner.py"
SPEC = importlib.util.spec_from_file_location("pipeline_runner", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
import sys

sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ResumeStateTests(unittest.TestCase):
    def make_runner(self, work_dir: Path):
        return MODULE.PipelineRunner(
            topic="checkpoint test",
            domain="general",
            config_path=SKILL_ROOT / "config.yaml",
            work_dir=work_dir,
            review_level="basic",
            output_stem="checkpoint-test",
        )

    def test_explicit_resume_from_loads_existing_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self.make_runner(Path(tmpdir) / "run")
            state_path = runner._state_file()
            existing = MODULE.PipelineState(
                topic="original topic",
                domain="medicine",
                started_at="2026-08-08T00:00:00",
                current_stage="4_select",
                completed_stages=["0_setup", "1_search", "2_dedupe", "3_score", "4_select"],
                input_files={"papers": "input/papers.json"},
                output_files={"references_bib": "references.bib"},
                metrics={"selected": 42},
            )
            existing.to_json(state_path)

            organizer = SimpleNamespace(returncode=0, stdout="no moves needed", stderr="")
            with patch.object(MODULE.subprocess, "run", return_value=organizer):
                self.assertTrue(runner.run(resume_from=99))

            self.assertEqual(runner.state.topic, "original topic")
            self.assertEqual(runner.state.output_files["references_bib"], "references.bib")
            self.assertEqual(runner.state.metrics["selected"], 42)
            self.assertEqual(runner.state.completed_stages[-1], "4_select")

    def test_corrupt_checkpoint_stops_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = self.make_runner(Path(tmpdir) / "run")
            state_path = runner._state_file()
            original = "{not valid json\n"
            state_path.write_text(original, encoding="utf-8")

            self.assertFalse(runner.run(resume_from=5))
            self.assertEqual(state_path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
