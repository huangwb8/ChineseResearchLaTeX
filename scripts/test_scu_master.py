"""四川大学独立工程的打包与真实编译回归。"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects/thesis-scu-master"
SPEC = importlib.util.spec_from_file_location("scu_pack_release", ROOT / "scripts/pack_release.py")
pack = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pack
SPEC.loader.exec_module(pack)


def test_scu_release_bundles_preserve_sources_and_isolate_profile(tmp_path):
    for overleaf in (False, True):
        fn = pack.pack_project_overleaf if overleaf else pack.pack_project
        archive = fn(PROJECT, tmp_path, "v-test-scu")
        with zipfile.ZipFile(archive) as z:
            names = set(z.namelist())
            assert {"main.tex", "assets/branding/scu-wordmark.png",
                    "docs/specification.md", "extraTex/back/statements.tex"} <= names
            assert not any(".latex-cache" in n for n in names)
            if overleaf:
                profiles = {n for n in names if n.startswith("styles/profiles/")}
                assert profiles == {"styles/profiles/bthesis-profile-thesis-scu-master.def"}
                assert "styles/bthesis-style-thesis-scu-master.tex" in names
                assert not any(n.startswith("styles/fonts/") for n in names)
                assert "styles/bensz-thesis" in z.read("extraTex/@config.tex").decode()
            else:
                assert "template.json" in names
                assert "scripts/thesis_build.py" in names
                assert "thesis-scu-master.code-workspace" in names


@pytest.fixture(scope="module")
def compiled_bundle(tmp_path_factory):
    xelatex = shutil.which("xelatex") or "/Library/TeX/texbin/xelatex"
    if not Path(xelatex).is_file():
        pytest.skip("需要XeLaTeX进行独立工程编译验证")
    work = tmp_path_factory.mktemp("scu-independent")
    bundle = work / "project"
    pack.populate_overleaf_bundle(bundle, PROJECT)
    main = bundle / "main.tex"
    text = main.read_text(encoding="utf-8")
    probe = r"""
\AtBeginDocument{%
  \normalsize
  \typeout{SCU-NORMAL-BASELINE=\the\baselineskip}%
  \typeout{SCU-TEXT-WIDTH=\the\textwidth}%
  \typeout{SCU-TEXT-HEIGHT=\the\textheight}%
}
\AtEndDocument{\typeout{SCU-FOOTNOTE-COUNT=\arabic{footnote}}}
"""
    main.write_text(text.replace(r"\begin{document}", probe + "\n" + r"\begin{document}"), encoding="utf-8")
    # 复制官方wrapper到隔离目录，避免其TEXINPUTS注入仓库公共包而掩盖缺包。
    tools_dir = work / "isolated-tools/scripts"
    tools_dir.mkdir(parents=True)
    wrapper = tools_dir / "thesis_project_tool.py"
    shutil.copyfile(ROOT / "packages/bensz-thesis/scripts/thesis_project_tool.py", wrapper)
    result = subprocess.run(
        [sys.executable, str(wrapper), "build", "--project-dir", str(bundle)],
        cwd=work, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return bundle


def test_scu_pdf_paper_layout_and_continuous_notes(compiled_bundle):
    pdf = PdfReader(compiled_bundle / "main.pdf")
    for page in pdf.pages:
        assert float(page.mediabox.width) * 25.4 / 72 == pytest.approx(197, abs=0.02)
        assert float(page.mediabox.height) * 25.4 / 72 == pytest.approx(273, abs=0.02)
    log = (compiled_bundle / ".latex-cache/main.log").read_text(errors="replace")
    assert "SCU-NORMAL-BASELINE=20.075" in log  # 20 bp换算为TeX pt
    assert "SCU-TEXT-WIDTH=412.564" in log  # 145 mm
    assert "SCU-TEXT-HEIGHT=640.187" in log  # 225 mm
    assert "SCU-FOOTNOTE-COUNT=2" in log  # 两章各一注，未随chapter重置
    for failure in ("Overfull", "undefined references", "Missing character:", "Package fontspec Warning", "LaTeX Error"):
        assert failure not in log
    # 书签使用Unicode文本，不依赖各PDF库对Fandol字形映射的差异。
    titles = "\n".join(item.title for item in pdf.outline if not isinstance(item, list))
    for required in ("独创性声明", "学位论文使用授权书", "参考文献"):
        assert required in titles
    text = "\n".join(p.extract_text() for p in pdf.pages)
    for author in ("Flory", "de Gennes"):
        assert author in text
