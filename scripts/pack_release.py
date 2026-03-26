#!/usr/bin/env python3
"""
pack_release.py - 打包 projects/ 下各子项目为 Release Assets

用法：
  python scripts/pack_release.py --tag v3.3.0          # 仅打包
  python scripts/pack_release.py --tag v3.3.0 --upload # 打包并上传到 GitHub Release

打包规范：
  - 输出目录：./tests/release-{tag}/（如 ./tests/release-v3.3.0/）
  - 每个子项目默认生成两类 zip：
      1. 普通包：{项目名}-{tag}.zip
      2. Overleaf 包：{项目名}-Overleaf-{tag}.zip
  - 普通包保留：
      1. STANDARD_PROJECT_INCLUDE_ITEMS 白名单中的文件/目录
      2. 项目根目录下的 *.code-workspace 文件与 *.tex 文件
  - Overleaf 包保留：
      1. OVERLEAF_PROJECT_INCLUDE_ITEMS 中的最小可编译项目文件
      2. 项目根目录下的 *.tex 文件
      3. 按项目类型裁剪后的公共包运行时文件，并统一放到 styles/ 目录
  - Overleaf 包不会把无关模板实现、VS Code 配置、构建脚本、示例 PDF/DOCX、Word 模板等本地开发产物一起打进 zip
  - 不存在的白名单项自动跳过（如 .vscode/ 不存在时不报错）
  - 不修改 projects/ 目录内任何文件
  - zip 生成操作仅在 tests/ 目录进行
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

# zip 内保留的项目文件/目录（与 README / AGENTS.md 保持一致）
STANDARD_PROJECT_INCLUDE_ITEMS = [
    ".vscode",
    "artifacts",
    "assets",
    "bibs",
    "bibtex-style",
    "code",
    "extraTex",
    "figures",
    "references",
    "scripts",
    "styles",
    "template",
    "main.docx",
    "main.pdf",
    "main.tex",
    "main-zh.pdf",
    "main-en.pdf",
    "main-zh.tex",
    "main-en.tex",
    "template.json",
    "README.md",
]
STANDARD_PROJECT_ROOT_INCLUDE_GLOBS = (
    "*.code-workspace",
    "*.tex",
)

OVERLEAF_PROJECT_INCLUDE_ITEMS = [
    "assets",
    "bibs",
    "bibtex-style",
    "code",
    "extraTex",
    "figures",
    "references",
    "styles",
    "README.md",
]
OVERLEAF_PROJECT_ROOT_INCLUDE_GLOBS = ("*.tex",)

REPO_ROOT = Path(__file__).parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"
NSFC_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-nsfc"
PAPER_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-paper"
THESIS_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-thesis"
CV_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-cv"
FONTS_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-fonts"
TESTS_DIR = REPO_ROOT / "tests"

NSFC_SHARED_RUNTIME_FILES = [
    "bensz-nsfc-common.sty",
    "bensz-nsfc-core.sty",
    "bensz-nsfc-layout.sty",
    "bensz-nsfc-typography.sty",
    "bensz-nsfc-headings.sty",
    "bensz-nsfc-bibliography.sty",
]
PAPER_SHARED_RUNTIME_FILES = [
    "bensz-paper.sty",
    "bml-core.sty",
    "bml-layout.sty",
    "bml-headings.sty",
    "bml-typography.sty",
    "bml-floats.sty",
    "bml-bibliography.sty",
    "bml-review.sty",
]
THESIS_SHARED_RUNTIME_FILES = [
    "bensz-thesis.sty",
    "bthesis-core.sty",
]
CV_SHARED_RUNTIME_FILES = [
    "bensz-cv.cls",
    "resume.cls",
    "fontawesome.sty",
    "fontawesomesymbols-generic.tex",
    "fontawesomesymbols-pdftex.tex",
    "fontawesomesymbols-xeluatex.tex",
    "linespacing_fix.sty",
    "zh_CN-Adobefonts_external.sty",
    "zh_CN-Adobefonts_internal.sty",
    "NotoSansSC_external.sty",
    "NotoSerifCJKsc_external.sty",
]

FONTS_PACKAGE_ENTRY = "bensz-fonts.sty"
NSFC_TEMPLATE_IDS = {
    "NSFC_General": "general",
    "NSFC_Local": "local",
    "NSFC_Young": "young",
}
SKIP_FILE_NAMES = {".DS_Store", "Thumbs.db"}
SKIP_FILE_SUFFIXES = {".pyc", ".pyo"}
SKIP_DIR_NAMES = {"__pycache__", ".latex-cache", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def configure_windows_stdio_utf8() -> None:
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def should_skip_path(path: Path) -> bool:
    if path.name in SKIP_FILE_NAMES:
        return True
    if path.suffix in SKIP_FILE_SUFFIXES:
        return True
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def iter_tree_files(root: Path):
    for file in sorted(root.rglob("*")):
        if file.is_file() and not should_skip_path(file):
            yield file


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_file(source: Path, destination: Path) -> None:
    ensure_parent(destination)
    shutil.copy2(source, destination)


def copy_tree_contents(source_dir: Path, destination_dir: Path) -> None:
    for file in iter_tree_files(source_dir):
        copy_file(file, destination_dir / file.relative_to(source_dir))


def write_text_file(path: Path, content: str) -> None:
    ensure_parent(path)
    path.write_text(content, encoding="utf-8")


def add_project_contents(zf: zipfile.ZipFile, project_dir: Path) -> None:
    added_arcnames: set[str] = set()

    def add_file(file_path: Path, arcname: Path | str) -> None:
        arcname_str = str(arcname)
        if arcname_str in added_arcnames or should_skip_path(file_path):
            return
        zf.write(file_path, arcname=arcname_str)
        added_arcnames.add(arcname_str)

    for item_name in STANDARD_PROJECT_INCLUDE_ITEMS:
        item_path = project_dir / item_name
        if not item_path.exists():
            continue
        if item_path.is_file():
            add_file(item_path, item_name)
            continue
        for file in iter_tree_files(item_path):
            add_file(file, file.relative_to(project_dir))

    for pattern in STANDARD_PROJECT_ROOT_INCLUDE_GLOBS:
        for root_file in sorted(project_dir.glob(pattern)):
            if root_file.is_file():
                add_file(root_file, root_file.name)


def copy_project_contents(
    target_dir: Path,
    project_dir: Path,
    include_items: list[str],
    root_globs: tuple[str, ...],
    *,
    rewrite_text: callable | None = None,
) -> None:
    copied_relpaths: set[Path] = set()

    def copy_entry(file_path: Path, relative_path: Path) -> None:
        if relative_path in copied_relpaths or should_skip_path(file_path):
            return
        destination = target_dir / relative_path
        if rewrite_text is not None and file_path.suffix == ".tex":
            content = file_path.read_text(encoding="utf-8")
            rewritten = rewrite_text(relative_path, content)
            write_text_file(destination, rewritten)
        else:
            copy_file(file_path, destination)
        copied_relpaths.add(relative_path)

    for item_name in include_items:
        item_path = project_dir / item_name
        if not item_path.exists():
            continue
        if item_path.is_file():
            copy_entry(item_path, Path(item_name))
            continue
        for file in iter_tree_files(item_path):
            copy_entry(file, file.relative_to(project_dir))

    for pattern in root_globs:
        for root_file in sorted(project_dir.glob(pattern)):
            if root_file.is_file():
                copy_entry(root_file, Path(root_file.name))


def zip_directory(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(source_dir.rglob("*")):
            if file.is_file() and not should_skip_path(file):
                zf.write(file, arcname=file.relative_to(source_dir))


def detect_project_kind(project_dir: Path) -> str:
    if project_dir.name.startswith("paper-"):
        return "paper"
    if project_dir.name.startswith("cv-"):
        return "cv"
    if project_dir.name.startswith("thesis-"):
        return "thesis"
    if (project_dir / "extraTex" / "@config.tex").exists() and project_dir.name.startswith("NSFC_"):
        return "nsfc"
    return "generic"


def detect_nsfc_template_id(project_dir: Path) -> str:
    template_id = NSFC_TEMPLATE_IDS.get(project_dir.name)
    if template_id is None:
        raise ValueError(f"无法识别 NSFC 项目类型：{project_dir.name}")
    return template_id


def detect_paper_template_id(project_dir: Path) -> str:
    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        return project_dir.name
    content = main_tex.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"template\s*=\s*([a-zA-Z0-9._-]+)", content)
    return match.group(1) if match else project_dir.name


def detect_thesis_template_id(project_dir: Path) -> str:
    return project_dir.name


def build_overleaf_runtime_def() -> str:
    return "\n".join(
        [
            "% Auto-generated by scripts/pack_release.py for Overleaf release bundles.",
            r"\renewcommand{\NSFCPackageRootDir}{./styles/}",
            r"\renewcommand{\NSFCAssetsDir}{./styles/assets/}",
            r"\renewcommand{\NSFCAssetFontsDir}{./styles/fonts/}",
            r"\renewcommand{\NSFCAssetBibStyleBase}{./styles/assets/bibtex-style/gbt7714-nsfc}",
            "",
        ]
    )


def project_contains_package(project_dir: Path, package_name: str) -> bool:
    for tex_file in project_dir.rglob("*.tex"):
        if should_skip_path(tex_file):
            continue
        content = tex_file.read_text(encoding="utf-8", errors="ignore")
        if re.search(rf"\\usepackage(?:\[[^\]]*\])?\{{{re.escape(package_name)}\}}", content):
            return True
    return False


def select_overleaf_font_files(project_dir: Path) -> set[str]:
    project_kind = detect_project_kind(project_dir)

    if project_kind == "nsfc":
        return {"Kaiti.ttf", "TimesNewRoman.ttf"}

    if project_kind == "paper":
        return set()

    if project_kind == "thesis":
        config_files = (
            project_dir / "extraTex" / "@config.tex",
            project_dir / "extraTex" / "config-pre.tex",
        )
        times_new_roman_templates = {
            "template=thesis-sysu-doctor",
            "template=thesis-ucas-doctor",
        }
        for config_file in config_files:
            if not config_file.exists():
                continue
            content = config_file.read_text(encoding="utf-8", errors="ignore")
            if any(template_marker in content for template_marker in times_new_roman_templates):
                return {"TimesNewRoman.ttf"}
        return set()

    if project_kind == "cv":
        fonts = {
            "FontAwesome.otf",
            "Fontin-SmallCaps.otf",
            "texgyretermes-bold.otf",
            "texgyretermes-bolditalic.otf",
            "texgyretermes-italic.otf",
            "texgyretermes-regular.otf",
        }
        if project_contains_package(project_dir, "NotoSerifCJKsc_external"):
            fonts.update({"NotoSerifCJKsc-Bold.otf", "NotoSerifCJKsc-Regular.otf"})
        if project_contains_package(project_dir, "NotoSansSC_external"):
            fonts.update({"NotoSansSC-Bold.otf", "NotoSansSC-Regular.otf"})
        if project_contains_package(project_dir, "zh_CN-Adobefonts_external"):
            fonts.update(
                {
                    "AdobeFangsongStd-Regular.otf",
                    "AdobeHeitiStd-Regular.otf",
                    "AdobeKaitiStd-Regular.otf",
                    "AdobeSongStd-Light.otf",
                }
            )
        return fonts

    return set()


def copy_fonts_runtime_bundle(target_dir: Path, font_files: set[str]) -> None:
    if not font_files:
        return

    entry_file = FONTS_PACKAGE_DIR / FONTS_PACKAGE_ENTRY
    if not entry_file.exists():
        raise FileNotFoundError(f"缺少 Overleaf 打包所需文件：{entry_file}")
    copy_file(entry_file, target_dir / FONTS_PACKAGE_ENTRY)

    for font_name in sorted(font_files):
        font_path = FONTS_PACKAGE_DIR / "fonts" / font_name
        if not font_path.exists():
            raise FileNotFoundError(f"缺少 Overleaf 字体文件：{font_path}")
        copy_file(font_path, target_dir / "fonts" / font_name)


def build_nsfc_runtime_bundle(runtime_dir: Path, project_dir: Path) -> None:
    for file_name in NSFC_SHARED_RUNTIME_FILES:
        file_path = NSFC_PACKAGE_DIR / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"缺少 Overleaf 打包所需文件：{file_path}")
        if file_name == "bensz-nsfc-common.sty":
            content = file_path.read_text(encoding="utf-8")
            content = content.replace(
                r"\RequirePackage{bensz-nsfc-core}",
                r"\makeatletter\input{styles/bensz-nsfc-core.sty}\makeatother",
            )
            write_text_file(runtime_dir / file_name, content)
            continue
        if file_name == "bensz-nsfc-core.sty":
            content = file_path.read_text(encoding="utf-8")
            content = content.replace(
                r"\InputIfFileExists{bensz-nsfc-runtime.def}{}{}",
                r"\InputIfFileExists{styles/bensz-nsfc-runtime.def}{}{}",
            )
            content = content.replace(
                r"\InputIfFileExists{profiles/bensz-nsfc-profile-\NSFCtype.def}{}{%",
                r"\InputIfFileExists{styles/profiles/bensz-nsfc-profile-\NSFCtype.def}{}{%",
            )
            content = content.replace(
                r"\InputIfFileExists{templates/bensz-nsfc-\NSFCtype.tex}{}{%",
                r"\InputIfFileExists{styles/templates/bensz-nsfc-\NSFCtype.tex}{}{%",
            )
            write_text_file(runtime_dir / file_name, content)
            continue
        copy_file(file_path, runtime_dir / file_name)

    copy_tree_contents(NSFC_PACKAGE_DIR / "assets", runtime_dir / "assets")

    template_id = detect_nsfc_template_id(project_dir)
    profile_name = f"bensz-nsfc-profile-{template_id}.def"
    template_name = f"bensz-nsfc-{template_id}.tex"
    copy_file(NSFC_PACKAGE_DIR / "profiles" / profile_name, runtime_dir / "profiles" / profile_name)
    copy_file(NSFC_PACKAGE_DIR / "templates" / template_name, runtime_dir / "templates" / template_name)

    copy_fonts_runtime_bundle(runtime_dir, select_overleaf_font_files(project_dir))
    write_text_file(runtime_dir / "bensz-nsfc-runtime.def", build_overleaf_runtime_def())


def build_paper_runtime_bundle(runtime_dir: Path, project_dir: Path) -> None:
    for file_name in PAPER_SHARED_RUNTIME_FILES:
        file_path = PAPER_PACKAGE_DIR / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"缺少 Overleaf 打包所需文件：{file_path}")
        if file_name == "bensz-paper.sty":
            content = file_path.read_text(encoding="utf-8")
            content = content.replace(
                r"\IfFileExists{bensz-fonts.sty}{\RequirePackage{bensz-fonts}}{}",
                r"\IfFileExists{styles/bensz-fonts.sty}{\makeatletter\input{styles/bensz-fonts.sty}\makeatother}{}",
            )
            content = content.replace(
                r"\RequirePackage{bml-core}",
                r"\makeatletter\input{styles/bml-core.sty}\makeatother",
            )
            write_text_file(runtime_dir / file_name, content)
            continue
        if file_name == "bml-core.sty":
            content = file_path.read_text(encoding="utf-8")
            content = content.replace(
                r"\InputIfFileExists{profiles/bml-profile-\bml@template.def}{}{%",
                r"\InputIfFileExists{styles/profiles/bml-profile-\bml@template.def}{}{%",
            )
            for module_name in (
                "bml-layout",
                "bml-headings",
                "bml-typography",
                "bml-floats",
                "bml-bibliography",
                "bml-review",
            ):
                content = content.replace(
                    rf"\RequirePackage{{{module_name}}}",
                    rf"\makeatletter\input{{styles/{module_name}.sty}}\makeatother",
                )
            write_text_file(runtime_dir / file_name, content)
            continue
        copy_file(file_path, runtime_dir / file_name)

    profile_id = detect_paper_template_id(project_dir)
    profile_name = f"bml-profile-{profile_id}.def"
    copy_file(PAPER_PACKAGE_DIR / "profiles" / profile_name, runtime_dir / "profiles" / profile_name)
    copy_fonts_runtime_bundle(runtime_dir, select_overleaf_font_files(project_dir))


def build_thesis_runtime_bundle(runtime_dir: Path, project_dir: Path) -> None:
    template_id = detect_thesis_template_id(project_dir)
    profile_name = f"bthesis-profile-{template_id}.def"
    style_name = f"bthesis-style-{template_id}.tex"

    for file_name in THESIS_SHARED_RUNTIME_FILES:
        file_path = THESIS_PACKAGE_DIR / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"缺少 Overleaf 打包所需文件：{file_path}")
        if file_name == "bensz-thesis.sty":
            content = file_path.read_text(encoding="utf-8")
            content = content.replace(
                r"\IfFileExists{bensz-fonts.sty}{\RequirePackage{bensz-fonts}}{}",
                "\\makeatletter\n\\@ifundefined{benszthesislocalfontsloaded}{\\IfFileExists{styles/bensz-fonts.sty}{\\input{styles/bensz-fonts.sty}\\global\\let\\benszthesislocalfontsloaded\\@empty}{}}{}\n\\makeatother",
            )
            content = content.replace(
                r"\RequirePackage{bthesis-core}",
                r"\makeatletter\input{styles/bthesis-core.sty}\makeatother",
            )
            write_text_file(runtime_dir / file_name, content)
            continue
        if file_name == "bthesis-core.sty":
            content = file_path.read_text(encoding="utf-8")
            content = content.replace(
                r"\InputIfFileExists{profiles/bthesis-profile-\bthesis@template.def}{}{%",
                r"\InputIfFileExists{styles/profiles/bthesis-profile-\bthesis@template.def}{}{%",
            )
            write_text_file(runtime_dir / file_name, content)
            continue
        copy_file(file_path, runtime_dir / file_name)

    copy_file(THESIS_PACKAGE_DIR / "profiles" / profile_name, runtime_dir / "profiles" / profile_name)

    style_source = THESIS_PACKAGE_DIR / "styles" / style_name
    style_content = style_source.read_text(encoding="utf-8")
    if template_id == "thesis-sysu-doctor":
        style_content = style_content.replace(
            r"\RequirePackage{bensz-fonts}",
            "\\makeatletter\n\\@ifundefined{benszthesislocalfontsloaded}{\\IfFileExists{styles/bensz-fonts.sty}{\\input{styles/bensz-fonts.sty}\\global\\let\\benszthesislocalfontsloaded\\@empty}{}}{}\n\\makeatother",
        )
    write_text_file(runtime_dir / style_name, style_content)
    if template_id == "thesis-ucas-doctor":
        copy_tree_contents(THESIS_PACKAGE_DIR / "styles" / "ucas", runtime_dir / "ucas")

    copy_fonts_runtime_bundle(runtime_dir, select_overleaf_font_files(project_dir))


def build_cv_runtime_bundle(runtime_dir: Path, project_dir: Path) -> None:
    for file_name in CV_SHARED_RUNTIME_FILES:
        file_path = CV_PACKAGE_DIR / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"缺少 Overleaf 打包所需文件：{file_path}")
        content = file_path.read_text(encoding="utf-8")
        if file_name == "bensz-cv.cls":
            content = content.replace(
                r"\RequirePackage{bensz-fonts}",
                r"\relax",
            )
            content = content.replace(
                r"\LoadClass{resume}",
                r"\makeatletter\input{styles/resume.cls}\makeatother",
            )
            write_text_file(runtime_dir / file_name, content)
            continue
        if file_name == "resume.cls":
            content = content.replace(
                r"\RequirePackage{fontawesome}",
                "\\makeatletter\n\\@ifundefined{benszcvlocalfontsloaded}{\\input{styles/bensz-fonts.sty}\\global\\let\\benszcvlocalfontsloaded\\@empty}{}\n\\@ifundefined{benszcvlocalfontawesomeloaded}{\\input{styles/fontawesome.sty}\\global\\let\\benszcvlocalfontawesomeloaded\\@empty}{}\n\\makeatother",
            )
            content = content.replace(
                r"\RequirePackage{bensz-fonts}",
                r"\relax",
            )
            write_text_file(runtime_dir / file_name, content)
            continue
        if file_name == "fontawesome.sty":
            content = content.replace(
                r"\RequirePackage{bensz-fonts}",
                r"\relax",
            )
            content = content.replace(
                "Path = \\BenszFontsDir ,\nExtension = .otf ,",
                "Path = \\BenszFontsDir ,",
            )
            content = content.replace(
                "]{FontAwesome}",
                "]{FontAwesome.otf}",
            )
            content = content.replace(
                r"\input{fontawesomesymbols-generic.tex}",
                r"\input{styles/fontawesomesymbols-generic.tex}",
            )
            content = content.replace(
                r"\input{fontawesomesymbols-xeluatex.tex}",
                r"\input{styles/fontawesomesymbols-xeluatex.tex}",
            )
            content = content.replace(
                r"\input{fontawesomesymbols-pdftex.tex}",
                r"\input{styles/fontawesomesymbols-pdftex.tex}",
            )
            write_text_file(runtime_dir / file_name, content)
            continue
        if file_name in {
            "NotoSansSC_external.sty",
            "NotoSerifCJKsc_external.sty",
            "zh_CN-Adobefonts_external.sty",
        }:
            content = content.replace(
                r"\RequirePackage{bensz-fonts}",
                r"\relax",
            )
            write_text_file(runtime_dir / file_name, content)
            continue
        copy_file(file_path, runtime_dir / file_name)

    copy_fonts_runtime_bundle(runtime_dir, select_overleaf_font_files(project_dir))


def rewrite_tex_command_target(content: str, command: str, original: str, replacement: str) -> str:
    pattern = re.compile(
        rf"(\\{command}(?:\[[\s\S]*?\])?\{{){re.escape(original)}(\}})",
        re.MULTILINE,
    )
    return pattern.sub(rf"\1{replacement}\2", content)


def rewrite_overleaf_project_tex(relative_path: Path, content: str, project_dir: Path) -> str:
    project_kind = detect_project_kind(project_dir)
    rewritten = content

    if project_kind == "nsfc":
        rewritten = rewrite_tex_command_target(
            rewritten,
            "usepackage",
            "bensz-nsfc-common",
            "styles/bensz-nsfc-common",
        )
        return rewritten

    if project_kind == "paper":
        rewritten = rewrite_tex_command_target(
            rewritten,
            "usepackage",
            "bensz-paper",
            "styles/bensz-paper",
        )
        rewritten = rewrite_tex_command_target(
            rewritten,
            "usepackage",
            "benszmanuscriptlatex",
            "styles/benszmanuscriptlatex",
        )
        return rewritten

    if project_kind == "thesis":
        rewritten = rewrite_tex_command_target(
            rewritten,
            "usepackage",
            "bensz-thesis",
            "styles/bensz-thesis",
        )
        return rewritten

    if project_kind == "cv":
        rewritten = rewrite_tex_command_target(
            rewritten,
            "documentclass",
            "bensz-cv",
            "styles/bensz-cv",
        )
        for package_name in (
            "NotoSansSC_external",
            "NotoSerifCJKsc_external",
            "linespacing_fix",
            "zh_CN-Adobefonts_external",
            "zh_CN-Adobefonts_internal",
        ):
            rewritten = rewrite_tex_command_target(
                rewritten,
                "usepackage",
                package_name,
                f"styles/{package_name}",
            )
        return rewritten

    return rewritten


def populate_overleaf_bundle(bundle_dir: Path, project_dir: Path) -> None:
    copy_project_contents(
        bundle_dir,
        project_dir,
        OVERLEAF_PROJECT_INCLUDE_ITEMS,
        OVERLEAF_PROJECT_ROOT_INCLUDE_GLOBS,
        rewrite_text=lambda relative_path, content: rewrite_overleaf_project_tex(relative_path, content, project_dir),
    )

    runtime_dir = bundle_dir / "styles"
    project_kind = detect_project_kind(project_dir)
    if project_kind == "nsfc":
        build_nsfc_runtime_bundle(runtime_dir, project_dir)
    elif project_kind == "paper":
        build_paper_runtime_bundle(runtime_dir, project_dir)
    elif project_kind == "thesis":
        build_thesis_runtime_bundle(runtime_dir, project_dir)
    elif project_kind == "cv":
        build_cv_runtime_bundle(runtime_dir, project_dir)


def get_git_tag() -> str:
    """从 git 获取最新 tag。"""
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True, text=True, cwd=REPO_ROOT
    )
    if result.returncode != 0:
        sys.exit("错误：无法自动获取 git tag，请通过 --tag 手动指定。")
    return result.stdout.strip()


def pack_project(project_dir: Path, output_dir: Path, tag: str) -> Path:
    """将单个子项目打包为普通 zip，返回 zip 路径。"""
    zip_name = f"{project_dir.name}-{tag}.zip"
    zip_path = output_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        add_project_contents(zf, project_dir)

    return zip_path


def pack_project_overleaf(project_dir: Path, output_dir: Path, tag: str) -> Path:
    """将单个子项目打包为可直接上传 Overleaf 的 zip，返回 zip 路径。"""
    zip_name = f"{project_dir.name}-Overleaf-{tag}.zip"
    zip_path = output_dir / zip_name

    staging_root = TESTS_DIR / ".pack_release_tmp"
    staging_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{project_dir.name}-overleaf-", dir=staging_root) as temp_dir:
        bundle_dir = Path(temp_dir) / project_dir.name
        bundle_dir.mkdir(parents=True, exist_ok=True)
        populate_overleaf_bundle(bundle_dir, project_dir)
        zip_directory(bundle_dir, zip_path)

    return zip_path


def upload_asset(tag: str, zip_path: Path) -> None:
    """通过 gh CLI 上传 zip 到 GitHub Release。"""
    result = subprocess.run(
        ["gh", "release", "upload", tag, str(zip_path), "--clobber"],
        cwd=REPO_ROOT
    )
    if result.returncode != 0:
        sys.exit(f"错误：上传 {zip_path.name} 失败。")


def main() -> None:
    configure_windows_stdio_utf8()
    parser = argparse.ArgumentParser(description="打包 Release Assets")
    parser.add_argument("--tag", help="版本 tag（如 v3.3.0），省略则自动从 git 获取")
    parser.add_argument("--upload", action="store_true", help="打包后上传到 GitHub Release")
    args = parser.parse_args()

    tag = args.tag or get_git_tag()
    output_dir = TESTS_DIR / f"release-{tag}"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not NSFC_PACKAGE_DIR.exists():
        sys.exit(f"错误：未找到 NSFC 公共包目录 {NSFC_PACKAGE_DIR}")
    if not PAPER_PACKAGE_DIR.exists():
        sys.exit(f"错误：未找到 SCI 公共包目录 {PAPER_PACKAGE_DIR}")
    if not THESIS_PACKAGE_DIR.exists():
        sys.exit(f"错误：未找到 Thesis 公共包目录 {THESIS_PACKAGE_DIR}")
    if not CV_PACKAGE_DIR.exists():
        sys.exit(f"错误：未找到 CV 公共包目录 {CV_PACKAGE_DIR}")

    projects = sorted(p for p in PROJECTS_DIR.iterdir() if p.is_dir())
    if not projects:
        sys.exit(f"错误：{PROJECTS_DIR} 下没有找到子项目。")

    print(f"Tag: {tag}  |  输出目录: {output_dir.relative_to(REPO_ROOT)}")
    print("-" * 50)

    zips = []
    for project in projects:
        standard_zip = pack_project(project, output_dir, tag)
        standard_size_kb = standard_zip.stat().st_size // 1024
        print(f"  ✓ {standard_zip.name}  ({standard_size_kb} KB)")
        zips.append(standard_zip)

        overleaf_zip = pack_project_overleaf(project, output_dir, tag)
        overleaf_size_kb = overleaf_zip.stat().st_size // 1024
        print(f"  ✓ {overleaf_zip.name}  ({overleaf_size_kb} KB)")
        zips.append(overleaf_zip)

    if args.upload:
        print("\n上传到 GitHub Release...")
        for zip_path in zips:
            upload_asset(tag, zip_path)
            print(f"  ↑ {zip_path.name}")

    print(f"\n完成：{len(zips)} 个 zip 已生成。")


if __name__ == "__main__":
    main()
