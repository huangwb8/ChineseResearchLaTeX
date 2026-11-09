"""本地缺陷的公开 CLI 回归；数据均为合成输入。"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/research-literature-review"
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))


def cli(script, root, *args):
    env = {**os.environ, "SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT": str(root),
           "SLR_CONFIG_PATH": str(SKILL / "config.yaml"), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          cwd=root, env=env, capture_output=True, text=True)


def selected_file(root):
    path = root / "selected.jsonl"
    path.write_text(json.dumps({"id": "p1", "title": "Synthetic evidence", "score": 8,
                               "subtopic": "Mechanism", "abstract": "Evidence " * 20}) + "\n")
    return path


def test_budget_generation_accepts_bundled_config_but_rejects_external_config(tmp_path):
    work = tmp_path / "run"
    work.mkdir()
    selected = selected_file(work)
    args = ["--selected", selected, "--output-dir", work, "--review-level", "standard"]
    result = cli("plan_word_budget.py", work, *args, "--config", SKILL / "config.yaml")
    assert result.returncode == 0, result.stderr
    assert (work / "word_budget_final.csv").is_file()
    external = tmp_path / "external.yaml"
    shutil.copyfile(SKILL / "config.yaml", external)
    link = work / "config-link.yaml"
    link.symlink_to(external)
    for path in (external, link):
        rejected = cli("plan_word_budget.py", work, *args, "--config", path)
        assert rejected.returncode != 0
        assert "路径不在工作目录内" in rejected.stderr


@pytest.mark.parametrize("level,target", [("standard", 8000), ("basic", 4500)])
def test_budget_validation_uses_requested_review_level(tmp_path, level, target):
    selected = selected_file(tmp_path)
    budget = tmp_path / "budget.csv"
    budget.write_text(f"文献ID,大纲,综字数,述字数\np1,Mechanism,{target},0\n")
    args = ["--budget", budget, "--selected", selected, "--config", SKILL / "config.yaml",
            "--review-level", level]
    result = cli("validate_word_budget.py", tmp_path, *args)
    assert result.returncode == 0, result.stdout + result.stderr
    wrong = cli("validate_word_budget.py", tmp_path, *args, "--target-words", target * 2)
    assert wrong.returncode != 0


@pytest.mark.parametrize("separator", ["\u0085", "\u2028", "\u2029"])
def test_legacy_dedupe_keeps_unicode_inside_json_records(tmp_path, separator):
    source = tmp_path / "papers.jsonl"
    abstract = "First" + separator + "second"
    source.write_text(json.dumps({"id": "a", "title": "Synthetic evidence", "abstract": abstract,
                                  "year": 2024}, ensure_ascii=False) + "\n", encoding="utf-8")
    output = tmp_path / "deduped.jsonl"
    result = cli("dedupe_papers.py", tmp_path, "--input", source, "--output", output,
                 "--map", tmp_path / "map.json")
    assert result.returncode == 0, result.stderr
    with output.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    assert len(rows) == 1
    assert rows[0]["abstract"] == abstract


def test_citation_distribution_supports_natbib_options_multiline_and_comments():
    from validate_citation_distribution import extract_citations, parse_paragraphs
    text = ("Evidence \\citep[see][p.~2]{a,b} and \\citet*{c}. % \\cite{ignored}\n"
            "Further \\citeauthor{d} and \\citep\n{e,f}.\n\n"
            "No citation.\\% literal percent \\cite{g}\n")
    citations = extract_citations(text)
    assert [item[3] for item in citations] == [["a", "b"], ["c"], ["d"], ["e", "f"], ["g"]]
    assert [item[2] for item in citations] == [1, 1, 2, 2, 5]
    assert [p["cite_count"] for p in parse_paragraphs(text)] == [4, 1]
    assert parse_paragraphs("\\citet\n{a} reports evidence.")[0]["cite_count"] == 1


def test_standard_selection_excludes_explicit_do_not_cite_without_changing_audit():
    from select_references import _select_papers
    rows = [{"id": str(i), "title": f"Evidence {i}", "score": 9,
             "abstract": "Evidence " * 20, "do_not_cite": i == 0} for i in range(2)]
    selected, rationale = _select_papers(rows, 10, 20, 15, .6, .8, min_abstract_chars=80)
    assert [p["id"] for p in selected] == ["1"]
    assert rows[0]["do_not_cite"] is True
    assert rationale["do_not_cite_candidates"] == 1
    neighbors, _ = _select_papers(rows, 10, 20, 15, .6, .8, min_abstract_chars=80,
                                  purpose="novelty-check")
    assert neighbors[0]["do_not_cite"] is True


def test_bib_generation_normalizes_literal_metadata_newlines():
    from select_references import _render_bib_entry
    bib, _ = _render_bib_entry("a", {"title": r"First\nSecond\r\nThird\tFourth",
                                     "abstract": r"Result\nNext", "authors": ["Doe, Jane"],
                                     "venue": "Journal", "year": 2024})
    assert "title = {First Second Third Fourth}" in bib
    assert "abstract = {Result Next}" in bib
    # 合法数学宏必须保持；已有转义不能再次转义。
    macro, _ = _render_bib_entry("b", {"title": r"A \nabla B \& C"})
    assert r"A \nabla B \& C" in macro


def test_report_consumes_actual_validator_output(tmp_path):
    from generate_validation_report import parse_review_tex_result
    tex = tmp_path / "review.tex"
    tex.write_text(r"\documentclass{article}\begin{document}\begin{abstract}A.\end{abstract}"
                   r"\section{Introduction}I.\citep{a}\section{Topic A}A.\section{Topic B}B."
                   r"\section{Topic C}C.\section{Discussion}D.\section{Outlook}O."
                   r"\section{Conclusion}C.\end{document}")
    bib = tmp_path / "refs.bib"
    bib.write_text("@article{a,title={Evidence}}\n")
    result = cli("validate_review_tex.py", tmp_path, "--tex", tex, "--bib", bib)
    assert result.returncode == 0, result.stdout + result.stderr
    parsed = parse_review_tex_result(result.stdout)
    assert parsed["passed"] is True
    assert parsed["cites"] == parsed["bib_keys"] == 1
    assert parsed["sections"]


def test_runner_budget_uses_its_config_and_propagates_target(tmp_path, monkeypatch):
    from pipeline_runner import PipelineRunner
    from validate_word_budget import read_budget
    monkeypatch.setenv("SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT", str(tmp_path))
    config = tmp_path / "config.yaml"
    config.write_text((SKILL / "config.yaml").read_text().replace("min: 6000", "min: 7000")
                      .replace("max: 10000", "max: 11000"))
    monkeypatch.chdir(tmp_path.parent)
    runner = PipelineRunner(topic="test", domain="general", config_path=config.relative_to(tmp_path.parent),
                            work_dir=tmp_path, review_level="standard", output_stem="test")
    assert runner.config_path == config
    selected = selected_file(tmp_path)
    runner.state.input_files["selected_papers"] = str(selected)
    assert runner.run_stage_4_5_word_budget()
    budget = Path(runner.state.output_files["word_budget_final"])
    assert read_budget(budget)[1] == pytest.approx(9000, abs=5)
    # 验证阶段必须使用同一目标，而不是 validator 的默认 premium 中点。
    tex = runner.layout.supporting_dir / "test_review.tex"
    tex.parent.mkdir(parents=True, exist_ok=True)
    tex.write_text("Synthetic document")
    bib = tex.with_suffix(".bib")
    bib.write_text("@article{a,title={Evidence}}")
    wc = tex.with_suffix(".md")
    wc.write_text("Synthetic working conditions")
    runner.state.output_files.update(review_tex=str(tex), references_bib=str(bib), working_conditions=str(wc))
    checked = []
    def run_script(name, args):
        if name == "validate_word_budget.py":
            checked.append(args)
            result = cli(name, tmp_path, *args)
            assert result.returncode == 0, result.stdout + result.stderr
        return False
    monkeypatch.setattr(runner, "_run_script", run_script)
    monkeypatch.setattr(runner, "_run_script_capture_output", lambda *args: (False, ""))
    assert not runner.run_stage_6_validate()
    assert checked
    assert checked[0][checked[0].index("--review-level") + 1] == "standard"


def test_search_contract_legacy_import_and_invalid_query_paths(tmp_path):
    search = ROOT / "skills/research-literature-search"
    probe = f'''
import sys
from pathlib import Path
import yaml
sys.path.insert(0, {str(search / 'scripts')!r})
import rls_contract as contract
import query_contract as legacy
from manifest import SEARCH_SKILL_VERSION
assert legacy.QueryPlan is contract.QueryPlan
assert legacy.load_query_plan is contract.load_query_plan
assert SEARCH_SKILL_VERSION == yaml.safe_load(Path({str(search / 'config.yaml')!r}).read_text())['skill_info']['version']
plan = legacy.normalize_query_payload(['q1', 'q2', 'q3', 'q4', 'q5'])
assert [q['query_id'] for q in plan.queries] == ['q01', 'q02', 'q03', 'q04', 'q05']
try:
    contract.normalize_query_payload(['only one'])
except contract.QueryInputError:
    pass
else:
    raise AssertionError('invalid query count accepted')
'''
    result = subprocess.run([sys.executable, "-c", probe], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(not all(shutil.which(tool) for tool in ("xelatex", "bibtex", "pandoc")),
                    reason="真实导出需要 XeLaTeX、BibTeX 与 Pandoc")
def test_runner_export_forwards_local_template_override(tmp_path, monkeypatch):
    import yaml
    from pipeline_runner import PipelineRunner
    monkeypatch.setenv("SYSTEMATIC_LITERATURE_REVIEW_SCOPE_ROOT", str(tmp_path))
    styles = tmp_path / "styles"
    styles.mkdir()
    shutil.copyfile(SKILL / "references/latex-template/gbt7714-nsfc.bst", styles / "local-override.bst")
    config = tmp_path / "config.yaml"
    data = yaml.safe_load((SKILL / "config.yaml").read_text())
    data["latex"]["template_path_override"] = str(styles)
    config.write_text(yaml.safe_dump(data, allow_unicode=True))
    runner = PipelineRunner(topic="test", domain="general", config_path=config, work_dir=tmp_path,
                            review_level="basic", output_stem="test")
    tex = runner._output_path("review_tex")
    tex.parent.mkdir(parents=True, exist_ok=True)
    bib = runner._output_path("references_bib")
    bib.write_text('@article{a,title={Synthetic evidence},author={Doe, Jane},year={2024}}')
    tex.write_text(r"\documentclass{article}\begin{document}Evidence.\cite{a}"
                   r"\bibliographystyle{local-override}\bibliography{test_参考文献}\end{document}")
    runner.state.output_files.update(review_tex=str(tex), references_bib=str(bib))
    assert runner.run_stage_7_export()
    assert Path(runner.state.output_files["review_pdf"]).stat().st_size > 1000
    assert Path(runner.state.output_files["review_word"]).stat().st_size > 1000


@pytest.mark.skipif(not shutil.which("kpsewhich"), reason="需要 TeX 发行版的 kpsewhich")
def test_compiler_resolves_system_bst(tmp_path):
    import compile_latex_with_bibtex as compiler
    tex = tmp_path / "review.tex"
    tex.write_text(r"\bibliographystyle{plain}")
    paths = compiler._verify_bst_in_template(tex, [tmp_path])
    assert Path(paths[0]).is_file()
    tex.write_text(r"\bibliographystyle{nonexistent-bensz-style}")
    with pytest.raises(FileNotFoundError):
        compiler._verify_bst_in_template(tex, [tmp_path])
