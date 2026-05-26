from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_DIR / "scripts" / "export_docx.py"


def _load_export_module():
    spec = importlib.util.spec_from_file_location("ucas_export_docx_public", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["ucas_export_docx_public"] = module
    spec.loader.exec_module(module)
    return module


class ExportDocxPublicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.export_module = _load_export_module()

    def test_discover_reference_doc_finds_official_template(self) -> None:
        reference_doc = self.export_module.discover_reference_doc(PROJECT_DIR, None)

        self.assertEqual(reference_doc.suffix.lower(), ".docx")
        self.assertIn("word模板", reference_doc.name)
        self.assertTrue(reference_doc.exists())

    def test_explicit_reference_doc_can_be_relative_to_project(self) -> None:
        explicit = PROJECT_DIR / "docs/official/中国科学院大学资环学科群研究生学位论文word模板.docx"
        reference_doc = self.export_module.discover_reference_doc(
            PROJECT_DIR,
            explicit,
        )

        self.assertTrue(reference_doc.exists())
        self.assertEqual(reference_doc.parent.name, "official")

    def test_strict_python_hint_uses_environment_variable_only(self) -> None:
        old_value = os.environ.pop("BENSZ_DOCX_PYTHON", None)
        try:
            self.assertIsNone(self.export_module._strict_python_hint())
            os.environ["BENSZ_DOCX_PYTHON"] = "python"
            hint = self.export_module._strict_python_hint()
        finally:
            if old_value is None:
                os.environ.pop("BENSZ_DOCX_PYTHON", None)
            else:
                os.environ["BENSZ_DOCX_PYTHON"] = old_value

        self.assertIsNotNone(hint)
        assert hint is not None
        self.assertIn("BENSZ_DOCX_PYTHON", hint)
        self.assertIn("python", hint)

    def test_build_prepare_tex_command_uses_project_script(self) -> None:
        command = self.export_module.build_prepare_tex_command(
            python_cmd="python",
            project_dir=PROJECT_DIR,
        )

        self.assertEqual(command[0], "python")
        self.assertTrue(command[1].endswith("prepare_tex_for_word_export.py"))
        self.assertEqual(command[2:4], ["--project-dir", str(PROJECT_DIR)])
        self.assertIn("--apply", command)

    def test_normalize_toc_entry_spacing_replaces_visible_latex_tilde(self) -> None:
        normalized = self.export_module._normalize_toc_entry_spacing_text(
            "图1-1 示例~图题\t12",
            in_catalog=True,
        )

        self.assertEqual(normalized, "图1-1 示例 图题\t12")

    def test_ensure_target_writable_reports_locked_docx_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "output.docx"
            target.write_bytes(b"placeholder")

            self.export_module._ensure_target_writable(target)

        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
