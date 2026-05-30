from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "packages" / "bensz-thesis" / "scripts" / "thesis_docx_tool.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("thesis_docx_tool", MODULE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_strip_comments_preserves_escaped_percent() -> None:
    tool = load_tool()

    source = "保留\\%百分号 % 删除注释\n下一行% 删除"

    assert tool.strip_comments(source) == "保留\\%百分号 \n下一行"


def test_collect_sources_follows_inputs_recursively_and_reports_missing(tmp_path: Path) -> None:
    tool = load_tool()
    project = tmp_path
    (project / "extraTex" / "body").mkdir(parents=True)
    (project / "extraTex" / "@config.tex").write_text("% setup only\n", encoding="utf-8")
    (project / "main.tex").write_text(
        "% \\input{extraTex/body/commented-out.tex}\n"
        "\\input{extraTex/@config.tex}\n"
        "\\input{extraTex/body/chapter-01.tex}\n"
        "\\include{extraTex/body/missing}\n",
        encoding="utf-8",
    )
    (project / "extraTex" / "body" / "chapter-01.tex").write_text(
        "第一章正文\n\\input{extraTex/body/section-a.tex}\n",
        encoding="utf-8",
    )
    (project / "extraTex" / "body" / "section-a.tex").write_text("小节正文\n", encoding="utf-8")

    state = tool.DocxExportState(project / ".latex-cache" / "docx")
    collected = tool.collect_tex_sources(project / "main.tex", project, state)

    rel_paths = [item.path.relative_to(project).as_posix() for item in collected]
    assert rel_paths == [
        "main.tex",
        "extraTex/body/chapter-01.tex",
        "extraTex/body/section-a.tex",
    ]
    assert "extraTex/@config.tex" in state.skipped_files
    assert state.missing_sources == ["extraTex/body/missing.tex"]


def test_latex_to_markdown_converts_headings_figures_lists_and_citations(tmp_path: Path) -> None:
    tool = load_tool()
    project = tmp_path
    (project / "figures").mkdir()
    (project / "figures" / "demo.png").write_bytes(b"png")
    state = tool.DocxExportState(project / ".latex-cache" / "docx")

    markdown = tool.convert_latex_to_markdown(
        r"""
\chapter{绪论}
\section*{研究背景}
本文引用 \cite{smith2024, wang2025}。
\begin{itemize}
\item 第一条
\item 第二条
\end{itemize}
\begin{figure}
\includegraphics[width=.6\textwidth]{figures/demo}
\caption{示例图}
\end{figure}
""",
        project_dir=project,
        source_dir=project,
        state=state,
        graphic_search_dirs=[Path("figures")],
    )

    assert "# 绪论" in markdown
    assert "## 研究背景" in markdown
    assert "[@smith2024; @wang2025]" in markdown
    assert "- 第一条" in markdown
    assert "![示例图](figures/demo.png)" in markdown


def test_complex_objects_degrade_to_placeholder_and_save_original(tmp_path: Path) -> None:
    tool = load_tool()
    project = tmp_path
    state = tool.DocxExportState(project / ".latex-cache" / "docx")

    markdown = tool.convert_latex_to_markdown(
        r"""
\begin{algorithm}
\caption{复杂算法}
\begin{algorithmic}
\State do something
\end{algorithmic}
\end{algorithm}
""",
        project_dir=project,
        source_dir=project,
        state=state,
        graphic_search_dirs=[],
    )

    assert "复杂算法" in markdown
    assert "需在 Word 中人工整理" in markdown
    assert state.unsupported_counts["algorithm"] == 1
    saved = sorted((project / ".latex-cache" / "docx" / "unsupported").glob("algorithm-*.tex"))
    assert len(saved) == 1
    assert "\\begin{algorithm}" in saved[0].read_text(encoding="utf-8")


def test_reference_doc_discovery_allows_default_and_prefers_project_locations(tmp_path: Path) -> None:
    tool = load_tool()
    project = tmp_path
    assert tool.discover_reference_doc(project, None) is None

    artifacts_ref = project / "artifacts" / "reference.docx"
    artifacts_ref.parent.mkdir()
    artifacts_ref.write_bytes(b"docx")
    assert tool.discover_reference_doc(project, None) == artifacts_ref.resolve()

    explicit = project / "custom.docx"
    explicit.write_bytes(b"docx")
    assert tool.discover_reference_doc(project, explicit) == explicit.resolve()


def test_write_quality_report_records_core_export_facts(tmp_path: Path) -> None:
    tool = load_tool()
    report = tmp_path / "main_docx_quality_report.md"
    state = tool.DocxExportState(tmp_path / ".latex-cache" / "docx")
    state.included_sources = [tmp_path / "main.tex"]
    state.missing_assets.append("figures/missing.png")
    state.unsupported_counts["table"] = 2
    state.heading_counts[1] = 1

    tool.write_quality_report(
        report_path=report,
        docx_path=tmp_path / "main.docx",
        markdown_path=tmp_path / ".latex-cache" / "docx" / "main.md",
        reference_doc=None,
        state=state,
        pandoc_version="pandoc 3.0",
        style_before={"usage": {}, "unknown": {}},
        style_after={"usage": {}, "unknown": {}},
        style_remap={},
        fallback_used=False,
    )

    text = report.read_text(encoding="utf-8")
    assert "Pandoc default" in text
    assert "pandoc 3.0" in text
    assert "included source files" in text
    assert "figures/missing.png" in text
    assert "`table`: `2`" in text
    assert "update TOC" in text


def test_project_tool_docx_command_delegates(monkeypatch, tmp_path: Path) -> None:
    project = tmp_path
    (project / "extraTex").mkdir()
    (project / "main.tex").write_text("\\begin{document}Hi\\end{document}", encoding="utf-8")

    project_tool_path = REPO_ROOT / "packages" / "bensz-thesis" / "scripts" / "thesis_project_tool.py"
    spec = importlib.util.spec_from_file_location("thesis_project_tool", project_tool_path)
    assert spec is not None and spec.loader is not None
    project_tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(project_tool)

    calls = {}

    def fake_export_docx_project(**kwargs):
        calls.update(kwargs)
        output = project / "main.docx"
        output.write_bytes(b"docx")
        return output

    monkeypatch.setattr(project_tool, "export_docx_project", fake_export_docx_project)
    monkeypatch.setattr(
        project_tool.sys,
        "argv",
        [
            "thesis_project_tool.py",
            "docx",
            "--project-dir",
            str(project),
            "--keep-markdown",
            "--skip-style-normalization",
        ],
    )

    project_tool.main()

    assert calls["project_dir"] == project.resolve()
    assert calls["tex_file"] == "main.tex"
    assert calls["keep_markdown"] is True
    assert calls["skip_style_normalization"] is True
    assert calls["allow_external_output"] is False


def test_external_inputs_and_outputs_are_blocked_by_default(tmp_path: Path) -> None:
    tool = load_tool()
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.tex").write_text("\\input{../outside.tex}\n", encoding="utf-8")
    outside = tmp_path / "outside.tex"
    outside.write_text("SECRET\n", encoding="utf-8")

    state = tool.DocxExportState(project / ".latex-cache" / "docx")
    collected = tool.collect_tex_sources(project / "main.tex", project, state)

    assert [item.path for item in collected] == [(project / "main.tex").resolve()]
    assert any("Blocked external TeX input" in warning for warning in state.warnings)
    with pytest.raises(tool.DocxExportError):
        tool._resolve_output(project, Path("../out.docx"), "main")


def test_cli_docx_smoke_generates_docx_and_report(tmp_path: Path) -> None:
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc is required for DOCX integration smoke test")

    project = tmp_path / "mini-thesis"
    (project / "extraTex" / "body").mkdir(parents=True)
    (project / "figures").mkdir()
    (project / "extraTex" / "body" / "chapter-01.tex").write_text(
        "\\chapter{绪论}\n正文含公式 $E=mc^2$。\n",
        encoding="utf-8",
    )
    (project / "main.tex").write_text(
        "\\documentclass{ctexbook}\n"
        "\\begin{document}\n"
        "\\input{extraTex/body/chapter-01.tex}\n"
        "\\end{document}\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "packages" / "bensz-thesis" / "scripts" / "thesis_project_tool.py"),
            "docx",
            "--project-dir",
            str(project),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert zipfile.is_zipfile(project / "main.docx")
    report = project / ".latex-cache" / "docx" / "main_docx_quality_report.md"
    assert report.exists()
    assert "Conversion fallback used" in report.read_text(encoding="utf-8")


def test_ucas_wrapper_preserves_legacy_default_outputs(tmp_path: Path) -> None:
    if shutil.which("pandoc") is None:
        pytest.skip("pandoc is required for wrapper integration smoke test")

    project = tmp_path / "ucas-like"
    (project / "extraTex").mkdir(parents=True)
    (project / "main.tex").write_text(
        "\\begin{document}\n\\input{extraTex/chapter1.tex}\n\\end{document}\n",
        encoding="utf-8",
    )
    (project / "extraTex" / "chapter1.tex").write_text("\\chapter{测试}\n正文。\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "projects" / "thesis-ucas-doctor" / "scripts" / "export_docx.py"),
            "--project-dir",
            str(project),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert zipfile.is_zipfile(project / "main_from_tex_资环模板.docx")
    assert (project / "main_from_tex_word_source.md").exists()
    assert (project / "main_from_tex_资环模板_质量报告.md").exists()


def test_project_tool_help_does_not_need_docx_import() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "packages" / "bensz-thesis" / "scripts" / "thesis_project_tool.py"),
            "build",
            "--help",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--project-dir" in result.stdout


def test_analyze_docx_styles_handles_minimal_docx(tmp_path: Path) -> None:
    tool = load_tool()
    docx_path = tmp_path / "minimal.docx"
    with zipfile.ZipFile(docx_path, "w") as zf:
        zf.writestr(
            "word/styles.xml",
            """
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style>
</w:styles>
""",
        )
        zf.writestr(
            "word/document.xml",
            """
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>标题</w:t></w:r></w:p></w:body>
</w:document>
""",
        )

    info = tool.analyze_docx_styles(docx_path)

    assert info["usage"]["Heading1"] == 1
    assert info["style_name_to_id"]["heading 1"] == "Heading1"
