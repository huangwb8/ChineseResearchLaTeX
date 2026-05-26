from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_DIR / "scripts"


def _load_module(module_name: str, path: Path):
    test_module_name = f"ucas_tests_{module_name}"
    spec = importlib.util.spec_from_file_location(test_module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[test_module_name] = module
    spec.loader.exec_module(module)
    return module


class PrepareTexForWordExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.normalize_module = _load_module(
            "normalize_time_unit_spacing",
            SCRIPTS_DIR / "normalize_time_unit_spacing.py",
        )
        cls.fix_spacing_module = _load_module(
            "fix_spacing",
            SCRIPTS_DIR / "fix_spacing.py",
        )
        cls.prepare_module = _load_module(
            "prepare_tex_for_word_export",
            SCRIPTS_DIR / "prepare_tex_for_word_export.py",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        for module_name in (
            "ucas_tests_normalize_time_unit_spacing",
            "ucas_tests_fix_spacing",
            "ucas_tests_prepare_tex_for_word_export",
        ):
            sys.modules.pop(module_name, None)

    def test_normalize_text_handles_trailing_chinese_after_d(self) -> None:
        normalized, hits, _ = self.normalize_module._normalize_text(
            "图注：观测时期为 60 d和 160 d。"
        )
        self.assertEqual(hits, 2)
        self.assertEqual(normalized, "图注：观测时期为 60~d和 160~d。")

    def test_normalize_text_handles_rpm_g_and_preserves_mg_per_kg(self) -> None:
        normalized, hits, _ = self.normalize_module._normalize_text(
            "设备转速为 500 rpm，样品质量为 5.28 g，指标X为 0.28 mg/kg。"
        )
        self.assertEqual(hits, 3)
        self.assertEqual(
            normalized,
            "设备转速为 500~rpm，样品质量为 5.28~g，指标X为 0.28~mg/kg。",
        )

    def test_fix_spacing_keeps_structured_labels_and_comparisons_intact(self) -> None:
        text = "样品 ABC、ABC 指标、pH 6.5、P < 0.05、第 2章、第 3节、图 3-1、表 3-2、fresh weight / dry weight。"

        fixed, changes = self.fix_spacing_module.fix_spacing_in_text(text)

        self.assertEqual(changes, 2)
        self.assertEqual(
            fixed,
            "样品ABC、ABC指标、pH 6.5、P < 0.05、第 2章、第 3节、图 3-1、表 3-2、fresh weight / dry weight。",
        )

    def test_fix_spacing_leaves_time_unit_spacing_for_normalizer(self) -> None:
        fixed, changes = self.fix_spacing_module.fix_spacing_in_text("60 d")

        normalized, hits, _ = self.normalize_module._normalize_text("60 d")

        self.assertEqual(changes, 0)
        self.assertEqual(fixed, "60 d")
        self.assertEqual(hits, 1)
        self.assertEqual(normalized, "60~d")

    def test_fix_spacing_preserves_command_separator_spaces_before_cjk(self) -> None:
        text = (
            "\\item 示例作者。\n"
            "\\noindent 具体时间：2024年。\n"
            "\\midrule 一 & 方法 \\\\\n"
            "\\toprule 化合物 & 数值 \\\\\n"
            "\\endlastfoot 染料木素\n"
        )

        fixed, _ = self.fix_spacing_module.fix_spacing_in_text(text)

        self.assertIn("\\item 示例作者。", fixed)
        self.assertIn("\\noindent 具体时间：2024年。", fixed)
        self.assertIn("\\midrule 一 & 方法", fixed)
        self.assertIn("\\toprule 化合物 & 数值", fixed)
        self.assertIn("\\endlastfoot 染料木素", fixed)

    def test_fix_spacing_writes_lf_when_apply_runs_on_windows_style_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "chapter1.tex"
            target.write_bytes("样品 ABC。\r\n60 d。\r\n".encode("utf-8"))

            self.fix_spacing_module.process_file(
                target_path=target,
                source_path=target,
                dry_run=False,
                backup_current=False,
            )

            raw = target.read_bytes()
        self.assertNotIn(b"\r\n", raw)
        self.assertIn(b"\n", raw)

    def test_build_steps_apply_mode_uses_fix_then_normalize(self) -> None:
        steps = self.prepare_module.build_steps(
            python_cmd="python",
            project_dir=Path("projects/thesis-ucas-doctor"),
            apply=True,
        )
        self.assertEqual(len(steps), 2)
        self.assertIn("fix_spacing.py", steps[0].command[1])
        self.assertIn(str(Path("projects/thesis-ucas-doctor") / "scripts"), steps[0].command[1])
        self.assertEqual(
            steps[0].command[2:],
            [],
        )
        self.assertIn("normalize_time_unit_spacing.py", steps[1].command[1])
        self.assertEqual(
            steps[1].command[2:],
            [
                "--project-dir",
                str(Path("projects/thesis-ucas-doctor")),
                "--glob",
                "extraTex/*.tex",
                "--apply",
            ],
        )

    def test_build_steps_dry_run_mode_propagates_preview_flags(self) -> None:
        steps = self.prepare_module.build_steps(
            python_cmd="python",
            project_dir=Path("projects/thesis-ucas-doctor"),
            apply=False,
        )
        self.assertEqual(
            steps[0].command[2:],
            ["--dry-run"],
        )
        self.assertEqual(
            steps[1].command[2:],
            [
                "--project-dir",
                str(Path("projects/thesis-ucas-doctor")),
                "--glob",
                "extraTex/*.tex",
            ],
        )

    def test_from_backup_rebuild_must_run_before_time_unit_normalize(self) -> None:
        backup_text = "图注：观测时期为 60 d和 160 d。\n"

        normalized_first, hits, _ = self.normalize_module._normalize_text(backup_text)
        rebuilt_from_backup, _ = self.fix_spacing_module.fix_spacing_in_text(backup_text)
        rebuilt_then_normalized, hits_after_rebuild, _ = self.normalize_module._normalize_text(
            rebuilt_from_backup
        )

        self.assertEqual(hits, 2)
        self.assertIn("60 d和160 d", rebuilt_from_backup)
        self.assertNotIn("~d", rebuilt_from_backup)
        self.assertNotEqual(rebuilt_from_backup, normalized_first)
        self.assertEqual(hits_after_rebuild, 2)
        self.assertEqual(rebuilt_then_normalized, "图注：观测时期为60~d和160~d。\n")

    # ── fix_spacing.py 哨兵键碰撞回归测试 ──

    def test_fix_spacing_preserves_math_subscript(self) -> None:
        """$_2$ 不应被「第 X 章」的哨兵键覆盖替换。"""
        fixed, _ = self.fix_spacing_module.fix_spacing_in_text(
            "样品 ABC 含量低于 0.3 mg/kg，HNO$_3$ 消解后测定。详见第 3 章。"
        )
        self.assertIn("HNO$_3$", fixed)
        self.assertNotIn("HNO第", fixed)
        self.assertIn("第 3 章", fixed)

    def test_fix_spacing_preserves_math_greek(self) -> None:
        r"""$\mu$ 不应被哨兵键覆盖。"""
        fixed, _ = self.fix_spacing_module.fix_spacing_in_text(
            r"检出限为 0.45 $\mu$g/kg，方法见第 2 章。"
        )
        self.assertIn(r"$\mu$", fixed)
        self.assertNotIn("第", fixed[: fixed.index("方法")])

    def test_fix_spacing_preserves_cite_command(self) -> None:
        r"""\cite{...} 不应被哨兵键覆盖。"""
        fixed, _ = self.fix_spacing_module.fix_spacing_in_text(
            r"参照相关标准\cite{gb15618-2018}执行，详见第 4 章。"
        )
        self.assertIn(r"\cite{gb15618-2018}", fixed)
        self.assertIn("第 4 章", fixed)

    def test_fix_spacing_preserves_graphicspath(self) -> None:
        r"""\graphicspath 不应被哨兵键覆盖。"""
        fixed, _ = self.fix_spacing_module.fix_spacing_in_text(
            r"\graphicspath{{assets/chapter2/}}"
        )
        self.assertIn(r"\graphicspath{{assets/chapter2/}}", fixed)

    def test_fix_spacing_preserves_math_superscript_negative(self) -> None:
        r"""$^{-1}$ 不应被哨兵键覆盖。"""
        fixed, _ = self.fix_spacing_module.fix_spacing_in_text(
            "处理量为 8.0 mg$^{-1}$，与第 2 章方法一致。"
        )
        self.assertIn("$^{-1}$", fixed)

    def test_fix_spacing_preserves_math_eta_squared(self) -> None:
        r"""$\eta^2$ 不应被哨兵键覆盖。"""
        fixed, _ = self.fix_spacing_module.fix_spacing_in_text(
            r"效应量 $\eta^2$ 达到 0.15，按第 3 章标准判定。"
        )
        self.assertIn(r"$\eta^2$", fixed)

    def test_fix_spacing_preserves_inline_math_with_braces(self) -> None:
        r"""$C_{\mathrm{crop}}$ 不应被哨兵键覆盖。"""
        fixed, _ = self.fix_spacing_module.fix_spacing_in_text(
            r"式中 $C_{\mathrm{sample}}$ 为样品指标浓度。"
        )
        self.assertIn(r"$C_{\mathrm{sample}}$", fixed)

    def test_fix_spacing_sentinels_all_restored(self) -> None:
        """所有哨兵键在输出中均应被恢复，不残留。"""
        fixed, _ = self.fix_spacing_module.fix_spacing_in_text(
            r"HNO$_3$ 消解，$\mu$g/kg 检出限，\cite{gb15618-2018} 标准，第 2 章方法。"
        )
        self.assertNotIn(self.fix_spacing_module.SENTINEL_PREFIX, fixed)

    def test_fix_spacing_mixed_math_and_chapter_labels(self) -> None:
        """多轮交替：数学模式与章节标签混合出现时互不干扰。"""
        text = (
            r"如第 1 章所述，样品 ABC 含量（$\mu$g/kg）与 pH 呈相关。"
            "第 2 章进一步验证了 HNO$_3$--HF--HClO$_4$ 消解体系的适用性。"
            "第 3 章报告了 $C_{\\mathrm{source}}$ 与 $C_{\\mathrm{sample}}$ 的比值分布。"
            r"第 4 章讨论了 $\eta^2$ 效应量与 $P < 0.05$ 显著性。"
        )
        fixed, _ = self.fix_spacing_module.fix_spacing_in_text(text)
        self.assertIn(r"$\mu$", fixed)
        self.assertIn("HNO$_3$", fixed)
        self.assertIn(r"$C_{\mathrm{source}}$", fixed)
        self.assertIn(r"$C_{\mathrm{sample}}$", fixed)
        self.assertIn(r"$\eta^2$", fixed)
        self.assertIn("第 1 章", fixed)
        self.assertIn("第 2 章", fixed)
        self.assertIn("第 3 章", fixed)
        self.assertIn("第 4 章", fixed)


if __name__ == "__main__":
    unittest.main()
