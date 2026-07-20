from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PATH = REPO_ROOT / "projects" / "GXNSF_General" / "scripts" / "gxnsf_build.py"


def load_wrapper():
    assert WRAPPER_PATH.exists(), "GXNSF 项目必须提供独立构建 wrapper"
    spec = importlib.util.spec_from_file_location("gxnsf_build_under_test", WRAPPER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_rejects_missing_tex_file(tmp_path: Path):
    wrapper = load_wrapper()

    assert wrapper.build(tmp_path, "missing.tex") == 2


def test_build_stops_after_first_xelatex_failure(tmp_path: Path, monkeypatch):
    wrapper = load_wrapper()
    (tmp_path / "main.tex").write_text("test", encoding="utf-8")
    calls = []

    def fake_run(command, project_dir, env):
        calls.append(command)
        return 7

    monkeypatch.setattr(wrapper, "_run", fake_run)

    assert wrapper.build(tmp_path, "main.tex") == 7
    assert len(calls) == 1


def test_build_runs_twice_and_copies_final_pdf(tmp_path: Path, monkeypatch):
    wrapper = load_wrapper()
    (tmp_path / "main.tex").write_text("test", encoding="utf-8")
    calls = []

    def fake_run(command, project_dir, env):
        calls.append(command)
        cache_dir = tmp_path / ".latex-cache"
        cache_dir.mkdir(exist_ok=True)
        (cache_dir / "main.pdf").write_bytes(b"pdf")
        return 0

    monkeypatch.setattr(wrapper, "_run", fake_run)

    assert wrapper.build(tmp_path, "main.tex") == 0
    assert len(calls) == 2
    assert (tmp_path / "main.pdf").read_bytes() == b"pdf"

    command = calls[0]
    assert command[0] == "xelatex"
    assert "-halt-on-error" in command
    assert "-file-line-error" in command
    assert f"-output-directory={tmp_path / '.latex-cache'}" in command
    assert command[-1] == "main.tex"


def test_build_returns_failure_when_second_xelatex_run_fails(tmp_path: Path, monkeypatch):
    wrapper = load_wrapper()
    (tmp_path / "main.tex").write_text("test", encoding="utf-8")
    results = iter((0, 9))
    calls = []

    def fake_run(command, project_dir, env):
        calls.append((command, project_dir, env))
        return next(results)

    monkeypatch.setattr(wrapper, "_run", fake_run)

    assert wrapper.build(tmp_path, "main.tex") == 9
    assert len(calls) == 2
    assert all(call_project_dir == tmp_path for _, call_project_dir, _ in calls)
    assert all("TEXINPUTS" in env for _, _, env in calls)


def test_build_returns_failure_when_xelatex_does_not_create_pdf(tmp_path: Path, monkeypatch):
    wrapper = load_wrapper()
    (tmp_path / "main.tex").write_text("test", encoding="utf-8")
    monkeypatch.setattr(wrapper, "_run", lambda command, project_dir, env: 0)

    assert wrapper.build(tmp_path, "main.tex") == 1


def test_template_source_keeps_official_outline_and_layout_contract():
    project_dir = REPO_ROOT / "projects" / "GXNSF_General"
    main_tex = (project_dir / "main.tex").read_text(encoding="utf-8")
    config_tex = (project_dir / "extraTex" / "@config.tex").read_text(encoding="utf-8")

    expected_parts = (
        "（一）立项依据与研究内容（4000—8000字）：",
        "（二）研究基础与工作条件",
        "（三）项目的组织实施",
        "（四）其他附件清单（相关附件材料在申报时上传至申报系统）",
    )
    part_positions = [main_tex.index(part) for part in expected_parts]
    content_inputs = [
        line
        for line in main_tex.splitlines()
        if line.startswith(r"\input{extraTex/") and "@config.tex" not in line
    ]

    assert part_positions == sorted(part_positions)
    assert len(content_inputs) == 15
    assert r"\geometry{a4paper,left=3.175cm,right=3.175cm,top=2.54cm,bottom=2.54cm}" in config_tex
    assert r"\newcommand{\GXNSFFontSize}{\fontsize{16pt}{28.3pt}\selectfont}" in config_tex
    assert r"\setlength{\parindent}{32pt}" in config_tex
    assert r"\BenszFontsGXNSFSetupFangsongFallback" in config_tex
    assert r"\BenszFontsGXNSFSetupKaiFallback" in config_tex
    assert r"\IfFontExistsTF{方正仿宋_GBK}" in config_tex
    assert r"\IfFontExistsTF{方正仿宋简体}" in config_tex
    assert r"\IfFontExistsTF{方正楷体_GBK}" in config_tex
    assert r"\IfFontExistsTF{方正楷体简体}" in config_tex
    assert r"\IfFontExistsTF{FZKai-Z03S}" not in config_tex
    assert r"\GXNSFPreferOriginalFonts" in config_tex
    assert r"\PackageError{GXNSF}{Missing required package bensz-fonts}" in config_tex
    assert r"\justifying" in config_tex
    assert r"\usepackage{bensz-nsfc" not in config_tex


def test_shared_font_package_exposes_gxnsf_original_font_fallbacks():
    font_package = (REPO_ROOT / "packages" / "bensz-fonts" / "bensz-fonts.sty").read_text(
        encoding="utf-8"
    )

    assert r"\newcommand{\BenszFontsGXNSFSetupFangsongFallback}" in font_package
    assert r"\newcommand{\BenszFontsGXNSFSetupKaiFallback}" in font_package
    assert "FZFangSong-Z02.ttf" in font_package
    assert "FZKai-Z03.ttf" in font_package
    assert (REPO_ROOT / "packages" / "bensz-fonts" / "fonts" / "FZFangSong-Z02.ttf").exists()
    assert (REPO_ROOT / "packages" / "bensz-fonts" / "fonts" / "FZKai-Z03.ttf").exists()


def test_clean_removes_only_project_cache_and_latex_intermediates(tmp_path: Path):
    wrapper = load_wrapper()
    cache_dir = tmp_path / ".latex-cache"
    cache_dir.mkdir()
    (cache_dir / "main.aux").write_text("cache", encoding="utf-8")
    (tmp_path / "main.aux").write_text("aux", encoding="utf-8")
    (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")

    assert wrapper.clean(tmp_path) == 0
    assert not cache_dir.exists()
    assert not (tmp_path / "main.aux").exists()
    assert (tmp_path / "keep.txt").exists()
