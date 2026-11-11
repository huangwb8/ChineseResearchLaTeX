"""综述质量与交付公开入口回归；只使用合成学术数据。"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
import subprocess
import sys
import zipfile
import shutil
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/research-literature-review"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

from publish_deliverables import PublishError, publish_deliverables
from generate_validation_report import generate_markdown_report, parse_review_tex_result
from pipeline_runner import PipelineRunner


def cli(script, *args):
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          text=True, capture_output=True)


def document():
    return (r"\documentclass{article}\begin{document}\begin{abstract}Evidence synthesis.\end{abstract}"
            r"\section{Introduction}Context.\cite{a}\section{Topic A}A."
            r"\section{Topic B}B.\section{Topic C}C.\section{Discussion}Limits."
            r"\section{Perspectives}Testable question.\section{Conclusion}Conclusion."
            r"\bibliographystyle{gbt7714-nsfc}\bibliography{topic_参考文献}\end{document}")


def bundle(tmp_path):
    source = tmp_path / "source"
    supporting = source / "supporting"
    supporting.mkdir(parents=True)
    (source / "topic_review.pdf").write_bytes(b"%PDF-1.4\nfixture\n")
    with zipfile.ZipFile(source / "topic_review.docx", "w") as archive:
        archive.writestr("word/document.xml", '<document/>')
    (supporting / "topic_review.tex").write_text(document(), encoding="utf-8")
    (supporting / "topic_参考文献.bib").write_text('@article{a,title={Evidence},author={Doe, Jane},year={2024}}', encoding="utf-8")
    for name in ("工作条件", "验证报告"):
        (supporting / f"topic_{name}.md").write_text("Evidence and limits.\n", encoding="utf-8")
    return source


def test_publisher_requires_pdf_and_word_before_target_write(tmp_path):
    source = bundle(tmp_path)
    (source / "topic_review.docx").unlink()
    target = tmp_path / "published"
    with pytest.raises(PublishError):
        publish_deliverables(source, target, include_supporting=True)
    assert not target.exists()


def test_full_publication_carries_only_referenced_resources(tmp_path):
    source = bundle(tmp_path)
    support = source / "supporting"
    (support / "figures").mkdir()
    (support / "figures/plot.png").write_bytes(b"fixture")
    tex = support / "topic_review.tex"
    tex.write_text(tex.read_text().replace(r"\end{document}", r"\includegraphics{figures/plot.png}\end{document}"))
    result = publish_deliverables(source, tmp_path / "published", include_supporting=True)
    assert "materials/figures/plot.png" in result.published
    assert not any(name.endswith(".bst") for name in result.published)
    assert "README.md" not in result.published
    expected = (SKILL / "references/latex-template/gbt7714-nsfc").as_posix()
    assert rf"\bibliographystyle{{{expected}}}" in (tmp_path / "published/topic_review.tex").read_text()
    assert (tmp_path / "published/references/topic_参考文献.bib").exists()
    assert r"\bibliography{references/topic_参考文献}" in (tmp_path / "published/topic_review.tex").read_text()
    assert r"\includegraphics{materials/figures/plot.png}" in (tmp_path / "published/topic_review.tex").read_text()


def test_publication_preserves_curated_materials_and_relative_links(tmp_path):
    source = bundle(tmp_path)
    materials = source / "supporting/materials"
    materials.mkdir()
    contents = {"阅读地图.md": "![热度](研究热度.png)\n[数据](研究热度.csv)",
                "研究热度.png": "image", "研究热度.csv": "year,count\n2025,12", "研究热度.pdf": "figure"}
    for name, content in contents.items():
        (materials / name).write_text(content, encoding="utf-8")
    (source / "supporting/unused-draft.md").write_text("internal")
    target = tmp_path / "published"
    publish_deliverables(source, target, include_supporting=True)
    assert {p.name for p in target.iterdir()} == {
        "topic_review.docx", "topic_review.pdf", "topic_review.tex", "references", "qc", "materials"}
    assert {p.name for p in (target / "materials").iterdir()} == set(contents)
    assert (target / "materials/阅读地图.md").read_text() == contents["阅读地图.md"]
    from validate_workdir_cleanliness import validate_publish_dir
    assert validate_publish_dir(target, include_supporting=True) == []


def test_publication_rewrites_nested_tex_and_graphicspath_without_changing_source(tmp_path):
    source = bundle(tmp_path)
    support = source / "supporting"
    (support / "figures").mkdir()
    (support / "sections").mkdir()
    (support / "figures/plot.png").write_bytes(b"image")
    (support / "sections/part.tex").write_text(r"\includegraphics[width=1cm]{plot}")
    tex = support / "topic_review.tex"
    original = document().replace(r"\end{document}", r"\graphicspath{{figures/}}\input{sections/part}\end{document}")
    original += "\n% \\includegraphics{missing-comment.png}\n"
    tex.write_text(original)
    target = tmp_path / "published"
    publish_deliverables(source, target, include_supporting=True)
    assert tex.read_text() == original
    assert r"\input{materials/sections/part.tex}" in (target / tex.name).read_text()
    assert (target / "materials/sections/part.tex").read_text() == r"\includegraphics[width=1cm]{materials/figures/plot.png}"
    from validate_workdir_cleanliness import validate_publish_dir
    assert validate_publish_dir(target, include_supporting=True) == []


@pytest.mark.parametrize("name", ["word_budget_final.csv", "pipeline_state.json", "compile.log", "script.py"])
def test_publication_rejects_internal_materials_before_writing(tmp_path, name):
    source = bundle(tmp_path)
    materials = source / "supporting/materials"
    materials.mkdir()
    (materials / name).write_text("internal")
    with pytest.raises(PublishError):
        publish_deliverables(source, tmp_path / "published", include_supporting=True)
    assert not (tmp_path / "published").exists()


def test_materials_symlink_rejected_and_readers_only_excludes_materials(tmp_path):
    source = bundle(tmp_path)
    materials = source / "supporting/materials"
    materials.mkdir()
    (materials / "private.txt").symlink_to(source / "supporting/topic_工作条件.md")
    with pytest.raises(PublishError):
        publish_deliverables(source, tmp_path / "rejected", include_supporting=True)
    target = tmp_path / "readers"
    publish_deliverables(source, target)
    assert {p.name for p in target.iterdir()} == {"topic_review.pdf", "topic_review.docx"}


def test_publish_cleanliness_rejects_flat_support_and_unknown_root_directory(tmp_path):
    source = bundle(tmp_path)
    target = tmp_path / "published"
    publish_deliverables(source, target, include_supporting=True)
    misplaced = target / "topic_参考文献.bib"
    misplaced.write_text("old flat layout")
    unknown = target / "other"
    unknown.mkdir()
    from validate_workdir_cleanliness import validate_publish_dir
    assert set(validate_publish_dir(target, include_supporting=True)) == {misplaced, unknown}
    with pytest.raises(PublishError):
        publish_deliverables(source, target, include_supporting=True, force=True)
    assert misplaced.read_text() == "old flat layout"


def test_publication_does_not_copy_stale_bundled_bst_or_internal_readme(tmp_path):
    source = bundle(tmp_path)
    support = source / "supporting"
    (support / "gbt7714-nsfc.bst").write_text("stale local copy")
    (support / "README.md").write_text("internal notes")
    target = tmp_path / "published"
    publish_deliverables(source, target, include_supporting=True)
    from validate_workdir_cleanliness import validate_publish_dir
    assert validate_publish_dir(target, include_supporting=True) == []
    assert not (target / "gbt7714-nsfc.bst").exists()
    assert not (target / "README.md").exists()
    # 不删除已有的用户文件，包括上次手工交付留下的文件。
    (target / "README.md").write_text("user original")
    with pytest.raises(PublishError):
        publish_deliverables(source, target, include_supporting=True, force=True)
    assert (target / "README.md").read_text() == "user original"


def test_publication_accepts_bundled_absolute_bst_but_rejects_arbitrary_external_bst(tmp_path):
    source = bundle(tmp_path)
    tex = source / "supporting/topic_review.tex"
    bundled = (SKILL / "references/latex-template/gbt7714-nsfc").as_posix()
    tex.write_text(document().replace("{gbt7714-nsfc}", "{" + bundled + "}"))
    publish_deliverables(source, tmp_path / "published", include_supporting=True)
    external = tmp_path / "outside.bst"
    external.write_text("external")
    tex.write_text(document().replace("{gbt7714-nsfc}", "{" + external.with_suffix("").as_posix() + "}"))
    with pytest.raises(PublishError):
        publish_deliverables(source, tmp_path / "rejected", include_supporting=True)
    assert not (tmp_path / "rejected").exists()


@pytest.mark.parametrize("dependency", ["figures/missing.png", "../../outside.png"])
def test_missing_or_escaping_dependency_rejected(tmp_path, dependency):
    source = bundle(tmp_path)
    tex = source / "supporting/topic_review.tex"
    tex.write_text(tex.read_text() + rf"\includegraphics{{{dependency}}}")
    with pytest.raises(PublishError):
        publish_deliverables(source, tmp_path / "published", include_supporting=True)
    assert not (tmp_path / "published").exists()


def test_publish_rejects_source_symlink(tmp_path):
    source = bundle(tmp_path)
    pdf = source / "topic_review.pdf"
    pdf.unlink()
    (tmp_path / "external.pdf").write_bytes(b"private")
    pdf.symlink_to(tmp_path / "external.pdf")
    with pytest.raises(PublishError):
        publish_deliverables(source, tmp_path / "published", include_supporting=True)


def test_missing_required_supporting_file_fails(tmp_path):
    source = bundle(tmp_path)
    (source / "supporting/topic_验证报告.md").unlink()
    with pytest.raises(PublishError):
        publish_deliverables(source, tmp_path / "published", include_supporting=True)


@pytest.mark.parametrize("output", ["not passed", "✓ counted citations; validation failed", ""])
def test_report_does_not_infer_success_from_arbitrary_words(output):
    assert not parse_review_tex_result(output)["passed"]


def test_report_preserves_unverified_boundaries():
    report = generate_markdown_report({"passed": True}, {"passed": True}, None, "premium", "test")
    assert "所有验证项通过" not in report
    assert "系统综述已满足质量标准" not in report
    assert "未验证" in report
    assert "**摘要**: ✅ 存在" not in report


def test_tex_requires_real_conclusion_and_ignores_commented_citations(tmp_path):
    tex = tmp_path / "review.tex"
    bib = tmp_path / "refs.bib"
    bib.write_text('@article{a,title={Evidence}}')
    tex.write_text(document().replace(r"\section{Conclusion}", "% \\section{Conclusion}\n"))
    result = cli("validate_review_tex.py", "--tex", tex, "--bib", bib)
    assert result.returncode != 0
    tex.write_text(document() + "\n% \\cite{not-in-bib}\n")
    result = cli("validate_review_tex.py", "--tex", tex, "--bib", bib)
    assert result.returncode == 0, result.stderr


def test_evidence_cards_retain_interpretation_and_full_abstract(tmp_path):
    data = {"id": "study-1", "title": "Trial example", "year": 2024,
            "abstract": "Background. " * 100 + "Primary outcome: no demonstrated benefit.",
            "extraction": {"population": "defined population", "limitation": "imprecise"},
            "alignment": {"directness": "indirect"}, "evidence_role": "contradictory"}
    src = tmp_path / "papers.jsonl"; dst = tmp_path / "cards.jsonl"
    src.write_text(json.dumps(data) + "\n")
    result = cli("build_evidence_cards.py", "--input", src, "--output", dst)
    assert result.returncode == 0, result.stderr
    card = json.loads(dst.read_text())
    assert card["abstract"] == data["abstract"]
    assert card["extraction"] == data["extraction"]
    assert card["alignment"] == data["alignment"]
    assert card["evidence_role"] == "contradictory"
    assert card["source_id"] == "study-1"


@pytest.mark.parametrize("failure", ["report", "subtopics"])
def test_stage_validation_propagates_required_failure(tmp_path, monkeypatch, failure):
    runner = PipelineRunner(topic="test", domain="general", config_path=SKILL / "config.yaml",
                            work_dir=tmp_path / "run", review_level="basic", output_stem="test")
    for key in ("working_conditions", "review_tex", "references_bib"):
        p = runner._output_path(key); p.parent.mkdir(parents=True, exist_ok=True); p.write_text("fixture")
        runner.state.output_files[key] = str(p)
    selected = runner.artifacts_dir / "selected.jsonl"
    selected.write_text(json.dumps({"abstract": "a" * 100}) + "\n")
    runner.state.input_files["selected_papers"] = str(selected)
    runner.state.metrics["reference_count"] = 1
    def capture(name, args):
        if name == "validate_counts.py": return True, '{"passed":true}'
        if name == "validate_subtopic_count.py": return failure != "subtopics", "subtopics result"
        return True, "✓ LaTeX review validation passed (cites=1, bib_keys=1)"
    def run(name, args):
        if name == "generate_validation_report.py":
            if failure == "report": return False
            Path(args[args.index("--output") + 1]).write_text("report")
        return True
    monkeypatch.setattr(runner, "_run_script_capture_output", capture)
    monkeypatch.setattr(runner, "_run_script", run)
    runner.state.completed_stages = ["5_write", "6_validate", "7_export"]
    assert runner.run_stage_6_validate() is False
    assert "6_validate" not in runner.state.completed_stages
    assert "7_export" not in runner.state.completed_stages


@pytest.mark.parametrize("contents", ["{broken json", "[]\n", "\n"])
def test_invalid_selected_records_cannot_claim_abstract_coverage(tmp_path, contents):
    from generate_validation_report import compute_abstract_stats
    selected = tmp_path / "selected.jsonl"
    selected.write_text(contents)
    with pytest.raises(ValueError):
        compute_abstract_stats(selected, 80)


def test_compiler_rejects_unresolved_citation_and_keeps_log(tmp_path, monkeypatch):
    import compile_latex_with_bibtex as compiler
    tex = tmp_path / "review.tex"; tex.write_text(document())
    monkeypatch.setattr(compiler, "_check_tool", lambda _: True)
    def run(*args, **kwargs):
        (tmp_path / "review.pdf").write_bytes(b"%PDF fixture")
        (tmp_path / "review.log").write_text("LaTeX Warning: There were undefined references.\n")
    monkeypatch.setattr(compiler, "_run", run)
    with pytest.raises(RuntimeError):
        compiler.compile_pdf(tex, tmp_path / "result.pdf", keep_aux=False)
    assert (tmp_path / "review.log").exists()
    assert not (tmp_path / "result.pdf").exists()


def test_report_cannot_force_success(tmp_path):
    result = cli("generate_validation_report.py", "--force-pass", "--output", tmp_path / "report.md")
    assert result.returncode != 0
    assert not (tmp_path / "report.md").exists()


def test_render_template_refuses_overwrite(tmp_path):
    from render_review_template import render
    body = tmp_path / "body.tex"; body.write_text(r"\section{Introduction}Text.")
    bib = tmp_path / "refs.bib"; bib.write_text("@article{a,title={Test}}")
    output = tmp_path / "review.tex"; output.write_text("user original")
    with pytest.raises(FileExistsError):
        render("Test & review", body, bib, output)
    assert output.read_text() == "user original"


def test_runner_passes_config_to_export_scripts(tmp_path, monkeypatch):
    runner = PipelineRunner(topic="test", domain="general", config_path=SKILL / "config.yaml",
                            work_dir=tmp_path / "run", review_level="basic", output_stem="test")
    calls = []
    class Result:
        returncode = 0
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: calls.append(kw) or Result())
    assert runner._run_script("convert_latex_to_word.py", [])
    assert calls[0]["env"]["SLR_CONFIG_PATH"] == str(SKILL / "config.yaml")


@pytest.mark.skipif(not all(shutil.which(tool) for tool in ("xelatex", "bibtex", "pandoc")),
                    reason="真实导出需要 XeLaTeX、BibTeX 与 Pandoc")
@pytest.mark.parametrize("style", ["gbt7714-nsfc", "plain"])
def test_real_pdf_word_and_isolated_rebuild(tmp_path, monkeypatch, style):
    # 其它 runner 用例可能设置过 scope；本用例显式限定在自己的临时目录。
    monkeypatch.setenv("SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT", str(tmp_path))
    source = bundle(tmp_path); support = source / "supporting"
    for p in source.glob("*_review.*"):
        p.unlink()
    tex = support / "topic_review.tex"; tex.unlink()
    body = support / "body.tex"
    # 同时验证归类后的正文片段、图片与书目，不只检查文件名。
    import struct
    import zlib
    def chunk(kind, data):
        return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data))
    (support / "figures").mkdir()
    (support / "figures/plot.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack("!2I5B", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"\x00\x40\x80\xc0")) + chunk(b"IEND", b""))
    (support / "sections").mkdir()
    (support / "sections/extra.tex").write_text(r"补充片段。\includegraphics[width=1cm]{figures/plot.png}", encoding="utf-8")
    body.write_text(r"\begin{abstract}这是合成格式测试。\end{abstract}"
                    r"\section{引言}合成内容。\cite{a}\subsection{边界}仅验证转换。"
                    r"\begin{tabular}{ll}项目 & 结果\\正文 & 保留\end{tabular}"
                    r"\input{sections/extra}", encoding="utf-8")
    result = cli("render_review_template.py", "--title", "合成格式测试", "--body", body,
                 "--bib", support / "topic_参考文献.bib", "--output", tex)
    assert result.returncode == 0, result.stderr
    text = tex.read_text(encoding="utf-8")
    assert str(SKILL / "references/latex-template/gbt7714-nsfc") in text
    if style == "plain":
        text = re.sub(r"\\bibliographystyle\{[^}]+\}", lambda _: r"\bibliographystyle{plain}", text)
    tex.write_text(text, encoding="utf-8")
    for script, args in [("compile_latex_with_bibtex.py", [tex, source / "topic_review.pdf"]),
                         ("convert_latex_to_word.py", [tex, support / "topic_参考文献.bib", source / "topic_review.docx"])]:
        result = cli(script, *args)
        assert result.returncode == 0, result.stderr
    published = tmp_path / "published"
    publish_deliverables(source, published, include_supporting=True)
    assert not list(published.glob("*.bst"))
    assert not (published / "README.md").exists()
    with zipfile.ZipFile(published / "topic_review.docx") as archive:
        xml = ET.fromstring(archive.read("word/document.xml"))
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        styles = {e.get("{" + ns["w"] + "}val") for e in xml.findall(".//w:pStyle", ns)}
        assert "Heading1" in styles and "Heading2" in styles and "Heading3" not in styles
        assert len(xml.findall(".//w:tbl", ns)) == 1
        assert xml.findall(".//w:vertAlign", ns), "数字上标引文应保留"
        text = "".join(xml.itertext())
        assert "摘要" in text and "参考文献" in text
        assert b"themeColor" not in archive.read("word/styles.xml"), "主题色不能覆盖黑色标题"
    (published / "topic_review.pdf").unlink()
    env = {k: v for k, v in os.environ.items() if k not in {"TEXINPUTS", "BSTINPUTS"}}
    for command in (["xelatex", "-interaction=nonstopmode", "-halt-on-error", "topic_review.tex"],
                    ["bibtex", "topic_review"],
                    ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "topic_review.tex"],
                    ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "topic_review.tex"]):
        result = subprocess.run(command, cwd=published, env=env, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout[-2000:]
    assert (published / "topic_review.pdf").stat().st_size > 1000
