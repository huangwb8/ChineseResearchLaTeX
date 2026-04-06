#!/usr/bin/env python3
"""
Release 资产打包与上传脚本。

将 projects/ 下各子项目打包为两类 Release Assets：

  1. 普通 zip（如 ``NSFC_General-v3.5.2.zip``）
     面向本地用户，假设已通过 ``scripts/install.py`` 安装了公共包（bensz-fonts / bensz-nsfc
     / bensz-paper / bensz-thesis / bensz-cv），zip 内仅包含项目文件与 VS Code 工程配置。

  2. Overleaf zip（如 ``NSFC_General-Overleaf-v3.5.2.zip``）
     面向 Overleaf 用户，上传后可直接编译。zip 内嵌裁剪后的公共包运行时文件（.sty / .cls /
     字体 / profile / template），统一放置在 ``styles/`` 目录下，并重写 ``\\usepackage``
     路径以适配扁平目录结构。

典型用法::

    python scripts/pack_release.py --tag v3.5.2          # 仅本地打包
    python scripts/pack_release.py --tag v3.5.2 --upload # 打包并上传到 GitHub Release

依赖：
  - ``git`` ：获取版本 tag
  - ``gh``  CLI（GitHub CLI）：上传资产到 GitHub Release（仅 ``--upload`` 时需要）

打包规范：
  - 输出目录：``./tests/release-{tag}/``（如 ``./tests/release-v3.5.2/``）
  - 普通包保留：
      1. ``STANDARD_PROJECT_INCLUDE_ITEMS`` 白名单中的文件/目录
      2. 项目根目录下的 ``*.code-workspace`` 文件与 ``*.tex`` 文件
  - Overleaf 包保留：
      1. ``OVERLEAF_PROJECT_INCLUDE_ITEMS`` 中的最小可编译项目文件
      2. 项目根目录下的 ``*.tex`` 文件
      3. 按项目类型裁剪后的公共包运行时文件，统一放到 ``styles/`` 目录
  - Overleaf 包不会把无关模板实现、VS Code 配置、构建脚本、示例 PDF/DOCX、
    Word 模板等本地开发产物一起打进 zip
  - 不存在的白名单项自动跳过（如 ``.vscode/`` 不存在时不报错）
  - 不修改 ``projects/`` 目录内任何文件
  - zip 生成操作仅在 ``tests/`` 目录进行
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

# 普通 zip 白名单：仅包含这些文件/目录，确保用户拿到的是完整可开发的项目快照。
# - .vscode/        ：VS Code 工作区配置（LaTeX Workshop 等）
# - artifacts/      ：构建产物（如 DOCX 对照文件）
# - assets/         ：项目级静态资源
# - bibs/           ：BibTeX 参考文献数据库
# - bibtex-style/   ：自定义 .bst 样式文件
# - code/           ：项目级 Python wrapper（如 nsfc_build.py）
# - extraTex/       ：子正文片段（NSFC 正文章节、论文段落等）
# - figures/        ：图片资源
# - references/     ：项目辅助文档
# - scripts/        ：项目级构建/辅助脚本
# - styles/         ：项目级样式覆盖（普通包不嵌入公共包运行时，用户需自行安装）
# - template/       ：Word 模板等参考文件
# - main.*          ：主入口文件（tex / pdf / docx）及中英文变体
# - template.json   ：项目元数据（供脚本识别院校、学位等信息）
# - README.md       ：项目说明文档
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
# 项目根目录下按 glob 匹配的额外文件：VS Code 工作区定义与所有 .tex 入口
STANDARD_PROJECT_ROOT_INCLUDE_GLOBS = (
    "*.code-workspace",
    "*.tex",
)

# Overleaf zip 白名单：仅保留 Overleaf 编译所需的最小文件集。
# 与普通包相比，排除了 .vscode/、scripts/、template/、*.code-workspace、
# 构建产物（main.pdf / main.docx）等本地开发专属内容。
# 公共包运行时文件由各 build_*_runtime_bundle() 函数单独注入到 styles/ 目录。
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
# Overleaf 包不需要 .code-workspace，仅保留 .tex 入口文件
OVERLEAF_PROJECT_ROOT_INCLUDE_GLOBS = ("*.tex",)

# 仓库与关键目录路径
REPO_ROOT = Path(__file__).parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"
NSFC_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-nsfc"
PAPER_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-paper"
THESIS_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-thesis"
CV_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-cv"
FONTS_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-fonts"
TESTS_DIR = REPO_ROOT / "tests"

# 各产品线 Overleaf 运行时所需的共享 .sty / .cls 文件清单。
# 这些文件从 packages/bensz-*/ 目录复制，经过路径重写后注入 Overleaf zip 的 styles/ 目录。

# NSFC 公共包运行时：核心宏包 + 布局/排版/标题/参考文献模块
NSFC_SHARED_RUNTIME_FILES = [
    "bensz-nsfc-common.sty",
    "bensz-nsfc-core.sty",
    "bensz-nsfc-layout.sty",
    "bensz-nsfc-typography.sty",
    "bensz-nsfc-headings.sty",
    "bensz-nsfc-bibliography.sty",
]
# SCI 论文公共包运行时：Bensz Manuscript LaTeX (bml) 核心与各功能模块
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
# 毕业论文公共包运行时：核心宏包 + 引擎模块（样式由项目级 profile/style 提供）
THESIS_SHARED_RUNTIME_FILES = [
    "bensz-thesis.sty",
    "bthesis-core.sty",
]
# 简历公共包运行时：文档类 + 图标字体 + 中文字体配置 + 行距修复
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

# bensz-fonts 包入口文件，Overleaf 运行时需要注入此文件以提供字体路径宏
FONTS_PACKAGE_ENTRY = "bensz-fonts.sty"
# NSFC 项目目录名 → 模板 ID 映射，用于定位对应的 profile 和 template 文件
NSFC_TEMPLATE_IDS = {
    "NSFC_General": "general",
    "NSFC_Local": "local",
    "NSFC_Young": "young",
}
# 打包时应跳过的系统/编辑器垃圾文件
SKIP_FILE_NAMES = {".DS_Store", "Thumbs.db"}
SKIP_FILE_SUFFIXES = {".pyc", ".pyo"}
SKIP_DIR_NAMES = {"__pycache__", ".latex-cache", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def configure_windows_stdio_utf8() -> None:
    """在 Windows 上将 stdout/stderr 编码设为 UTF-8，避免中文路径输出乱码。"""
    if sys.platform != "win32":
        return
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def should_skip_path(path: Path) -> bool:
    """判断文件/目录路径是否应被跳过（垃圾文件、缓存目录等）。"""
    if path.name in SKIP_FILE_NAMES:
        return True
    if path.suffix in SKIP_FILE_SUFFIXES:
        return True
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def iter_tree_files(root: Path):
    """递归遍历目录树，yield 所有应保留的文件（已过滤垃圾文件和缓存目录）。"""
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
    """将项目文件按 STANDARD 白名单添加到 zip 归档中。

    依次处理 ``STANDARD_PROJECT_INCLUDE_ITEMS`` 白名单中的文件/目录，
    再按 ``STANDARD_PROJECT_ROOT_INCLUDE_GLOBS`` 匹配项目根目录下的
    ``*.code-workspace`` 和 ``*.tex`` 文件。不存在的白名单项自动跳过。
    """
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
    """将项目文件按白名单复制到目标目录，可选地对 .tex 文件执行文本重写。

    用于 Overleaf 打包流程：先将项目文件复制到临时目录，再注入运行时 bundle。
    ``rewrite_text`` 回调签名为 ``(relative_path, content) -> str``，
    用于重写 ``\\usepackage`` 路径以适配 Overleaf 的扁平 styles/ 目录结构。
    """
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
    """将整个目录递归打包为 zip（自动跳过垃圾文件和缓存目录）。"""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(source_dir.rglob("*")):
            if file.is_file() and not should_skip_path(file):
                zf.write(file, arcname=file.relative_to(source_dir))


def detect_project_kind(project_dir: Path) -> str:
    """根据项目目录名和特征文件自动识别项目类型。

    返回 ``"nsfc"`` / ``"paper"`` / ``"thesis"`` / ``"cv"`` / ``"generic"`` 之一。
    """
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
    """从 NSFC_TEMPLATE_IDS 映射中查找项目的模板 ID（如 ``"general"``）。"""
    template_id = NSFC_TEMPLATE_IDS.get(project_dir.name)
    if template_id is None:
        raise ValueError(f"无法识别 NSFC 项目类型：{project_dir.name}")
    return template_id


def detect_paper_template_id(project_dir: Path) -> str:
    """从 main.tex 中解析 ``template=xxx`` 参数，确定 SCI 论文的模板 profile 名称。"""
    main_tex = project_dir / "main.tex"
    if not main_tex.exists():
        return project_dir.name
    content = main_tex.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"template\s*=\s*([a-zA-Z0-9._-]+)", content)
    return match.group(1) if match else project_dir.name


def detect_thesis_template_id(project_dir: Path) -> str:
    """毕业论文模板 ID 直接使用项目目录名（如 ``"thesis-smu-master"``）。"""
    return project_dir.name


def build_overleaf_runtime_def() -> str:
    """生成 Overleaf 专用的 bensz-nsfc-runtime.def 内容。

    将公共包路径宏（``\\NSFCPackageRootDir`` 等）重定向到 ``./styles/`` 目录，
    使 Overleaf 环境下的相对路径引用能正确找到内嵌的运行时文件。
    """
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
    """检查项目中任一 .tex 文件是否引用了指定的宏包名。用于决定是否注入对应的字体运行时。"""
    for tex_file in project_dir.rglob("*.tex"):
        if should_skip_path(tex_file):
            continue
        content = tex_file.read_text(encoding="utf-8", errors="ignore")
        if re.search(rf"\\usepackage(?:\[[^\]]*\])?\{{{re.escape(package_name)}\}}", content):
            return True
    return False


def select_overleaf_font_files(project_dir: Path) -> set[str]:
    """根据项目类型和配置动态选择 Overleaf 打包所需的字体文件集合。

    不同项目类型对字体的需求差异较大：
    - NSFC：固定需要楷体和 Times New Roman
    - Paper：无额外字体需求（使用系统字体）
    - Thesis：仅部分模板需要 Times New Roman
    - CV：需要 FontAwesome、TeX Gyre Termes，以及项目实际引用的 CJK 字体
    """
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
    """将 bensz-fonts 入口文件和指定字体文件复制到 Overleaf 运行时目录。

    同时复制 ``bensz-fonts.sty``（提供字体路径宏定义）和实际字体文件到
    ``target_dir/fonts/`` 子目录。
    """
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


def add_runtime_directory_to_zip(zf: zipfile.ZipFile, runtime_dir: Path) -> None:
    """将运行时目录中的所有文件添加到 zip 归档（保留相对路径）。"""
    for file in iter_tree_files(runtime_dir):
        zf.write(file, arcname=file.relative_to(runtime_dir))


def build_legacy_runtime_zip(
    zf: zipfile.ZipFile,
    builder: callable,
    project_dir: Path,
    prefix: str,
) -> None:
    """在临时目录中调用 builder 构建运行时 bundle，再写入 zip 归档。

    用于向后兼容旧版打包逻辑；新版 Overleaf 打包通过 ``populate_overleaf_bundle()``
    统一入口调用。
    """
    staging_root = TESTS_DIR / ".pack_release_tmp"
    staging_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{prefix}-legacy-runtime-", dir=staging_root) as temp_dir:
        runtime_dir = Path(temp_dir)
        builder(runtime_dir, project_dir)
        add_runtime_directory_to_zip(zf, runtime_dir)


def build_nsfc_runtime_bundle(runtime_dir: Path, project_dir: Path) -> None:
    """构建 NSFC 项目的 Overleaf 运行时 bundle。

    将 ``packages/bensz-nsfc/`` 中裁剪后的共享 .sty、profile、template、
    字体和 assets 复制到 ``runtime_dir``（即 Overleaf zip 的 ``styles/`` 目录）。
    对 ``bensz-nsfc-common.sty`` 和 ``bensz-nsfc-core.sty`` 执行路径重写，
    使内部的 ``\\RequirePackage`` / ``\\InputIfFileExists`` 指向 ``styles/`` 前缀。
    """
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
    """构建 SCI 论文项目的 Overleaf 运行时 bundle。

    将 ``packages/bensz-paper/`` 中裁剪后的 bml 系列 .sty 和项目对应的
    profile 复制到 ``runtime_dir``。对 ``bensz-paper.sty`` 和 ``bml-core.sty``
    执行路径重写，使内部模块引用指向 ``styles/`` 前缀。
    """
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
    """构建毕业论文项目的 Overleaf 运行时 bundle。

    将 ``packages/bensz-thesis/`` 中裁剪后的 .sty、项目对应的 profile 和
    style 文件复制到 ``runtime_dir``。对 ``bensz-thesis.sty`` 和 ``bthesis-core.sty``
    执行路径重写；部分模板（如中山大学博士、中国科学院大学博士）还需处理字体加载
    和额外样式目录（``ucas/``）。
    """
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
    """构建简历项目的 Overleaf 运行时 bundle。

    将 ``packages/bensz-cv/`` 中裁剪后的 .cls / .sty 和 FontAwesome 图标字体
    相关文件复制到 ``runtime_dir``。对 ``bensz-cv.cls``、``resume.cls``、
    ``fontawesome.sty`` 及各字体配置 .sty 执行路径重写，禁用对已安装
    ``bensz-fonts`` 包的 ``\\RequirePackage`` 依赖，改为直接 ``\\input``
    内嵌的字体文件。
    """
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


def add_nsfc_runtime_bundle(zf: zipfile.ZipFile, project_dir: Path | None = None) -> None:
    build_legacy_runtime_zip(
        zf,
        build_nsfc_runtime_bundle,
        project_dir or (PROJECTS_DIR / "NSFC_General"),
        "nsfc",
    )


def add_paper_runtime_bundle(zf: zipfile.ZipFile, project_dir: Path | None = None) -> None:
    build_legacy_runtime_zip(
        zf,
        build_paper_runtime_bundle,
        project_dir or (PROJECTS_DIR / "paper-sci-01"),
        "paper",
    )


def add_thesis_runtime_bundle(zf: zipfile.ZipFile, project_dir: Path | None = None) -> None:
    build_legacy_runtime_zip(
        zf,
        build_thesis_runtime_bundle,
        project_dir or (PROJECTS_DIR / "thesis-smu-master"),
        "thesis",
    )


def add_cv_runtime_bundle(zf: zipfile.ZipFile, project_dir: Path | None = None) -> None:
    build_legacy_runtime_zip(
        zf,
        build_cv_runtime_bundle,
        project_dir or (PROJECTS_DIR / "cv-01"),
        "cv",
    )


def rewrite_tex_command_target(content: str, command: str, original: str, replacement: str) -> str:
    """在 .tex 内容中将指定 LaTeX 命令的目标参数进行正则替换。

    例如将 ``\\usepackage{bensz-nsfc-common}`` 替换为
    ``\\usepackage{styles/bensz-nsfc-common}``。支持带可选参数的命令形式。
    """
    pattern = re.compile(
        rf"(\\{command}(?:\[[\s\S]*?\])?\{{){re.escape(original)}(\}})",
        re.MULTILINE,
    )
    return pattern.sub(rf"\1{replacement}\2", content)


def rewrite_overleaf_project_tex(relative_path: Path, content: str, project_dir: Path) -> str:
    """为 Overleaf 打包重写 .tex 文件中的 \\usepackage / \\documentclass 路径。

    Overleaf 不支持 TEXMFHOME，公共包运行时文件被扁平放置在 ``styles/`` 目录下，
    因此需要将所有 ``\\usepackage{bensz-xxx}`` 重写为
    ``\\usepackage{styles/bensz-xxx}``，使 Overleaf 编译器能正确定位
    内嵌的 .sty / .cls 文件。不同项目类型（NSFC / Paper / Thesis / CV）
    重写的包名集合不同。
    """
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
    """组装 Overleaf zip 的完整目录结构。

    先复制项目文件（同时重写 .tex 中的包路径），再根据项目类型调用对应的
    ``build_*_runtime_bundle()`` 注入裁剪后的公共包运行时到 ``styles/`` 目录。
    """
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
    """将单个子项目打包为普通 zip。

    普通包面向本地开发用户，假设已通过 ``scripts/install.py`` 安装了公共包，
    zip 内仅包含项目文件和 VS Code 工程配置，不嵌入公共包运行时。

    Returns:
        生成的 zip 文件路径，如 ``tests/release-v3.5.2/NSFC_General-v3.5.2.zip``。
    """
    zip_name = f"{project_dir.name}-{tag}.zip"
    zip_path = output_dir / zip_name

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        add_project_contents(zf, project_dir)

    return zip_path


def pack_project_overleaf(project_dir: Path, output_dir: Path, tag: str) -> Path:
    """将单个子项目打包为可直接上传 Overleaf 的 zip。

    与普通包不同，Overleaf 包需要内嵌裁剪后的公共包运行时文件（.sty / .cls /
    字体 / profile / template），并重写 .tex 中的 ``\\usepackage`` 路径
    指向 ``styles/`` 目录，以确保 Overleaf 上传后无需额外安装即可编译。

    Returns:
        生成的 zip 文件路径，如 ``tests/release-v3.5.2/NSFC_General-Overleaf-v3.5.2.zip``。
    """
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
    """CLI 入口：遍历 projects/ 下所有子项目，生成普通 zip 与 Overleaf zip。

    典型用法::

        python scripts/pack_release.py --tag v3.5.2          # 仅本地打包
        python scripts/pack_release.py --tag v3.5.2 --upload # 打包并上传到 GitHub Release

    流程：
      1. 解析命令行参数（``--tag`` 指定版本号，``--upload`` 控制是否上传）
      2. 验证各公共包目录存在
      3. 遍历 projects/ 下所有子目录，分别调用 ``pack_project()`` 和
         ``pack_project_overleaf()`` 生成两类 zip
      4. 若指定 ``--upload``，通过 ``gh release upload`` 将所有 zip 上传到
         对应版本的 GitHub Release
    """
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
