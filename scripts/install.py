#!/usr/bin/env python3
"""
ChineseResearchLaTeX — 统一 LaTeX 包安装器

支持远程执行（无需克隆仓库）：

  # macOS / Linux / WSL
  curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py \\
    | python3 - install --packages bensz-nsfc --ref v4.0.0

  # 多包安装
  curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py \\
    | python3 - install --packages bensz-nsfc,bensz-paper,bensz-thesis,bensz-cv --ref v4.0.0

  # Windows PowerShell
  (Invoke-WebRequest -Uri "https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py" `
    -UseBasicParsing).Content | python - install --packages bensz-nsfc --ref v4.0.0

也可本地执行（在仓库根目录）：
  python3 scripts/install.py install --packages bensz-nsfc --ref v4.0.0
  python3 scripts/install.py install --packages bensz-nsfc,bensz-paper,bensz-thesis,bensz-cv --ref v4.0.0
  python3 scripts/install.py list
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

REPO_OWNER = "huangwb8"
REPO_NAME = "ChineseResearchLaTeX"
RAW_BASE = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}"
API_BASE = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

SUPPORTED_PACKAGES: dict[str, dict] = {
    "bensz-nsfc": {
        "installer_path": "packages/bensz-nsfc/scripts/install.py",
        "description": "NSFC 公共包——三套国自然模板的共享样式基础",
        "install_mode": "delegate",
    },
    "bensz-paper": {
        "installer_path": None,
        "description": "SCI 论文公共包——支持 PDF / DOCX 双输出",
        "install_mode": "texmfhome",
        "package_subdir": "packages/bensz-paper",
    },
    "bensz-thesis": {
        "installer_path": None,
        "description": "毕业论文公共包——支持硕士/博士论文模板与像素级验收脚本",
        "install_mode": "texmfhome",
        "package_subdir": "packages/bensz-thesis",
    },
    "bensz-cv": {
        "installer_path": None,
        "description": "学术简历公共包——支持中英文简历模板与像素级验收脚本",
        "install_mode": "texmfhome",
        "package_subdir": "packages/bensz-cv",
    },
}


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _headers() -> dict[str, str]:
    headers = {"User-Agent": "ChineseResearchLaTeX-install.py"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        _die(f"下载失败：{exc.code} {url}")
    except urllib.error.URLError as exc:
        _die(f"无法访问远端：{url} — {exc.reason}")


def _fetch_bytes(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            dest.write_bytes(resp.read())
    except urllib.error.HTTPError as exc:
        _die(f"下载失败：{exc.code} {url}")
    except urllib.error.URLError as exc:
        _die(f"无法下载资源：{url} — {exc.reason}")


def _die(msg: str) -> None:
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)


def _texmfhome() -> Path:
    """获取 TEXMFHOME 目录。"""
    try:
        result = subprocess.run(
            ["kpsewhich", "--var-value=TEXMFHOME"],
            capture_output=True, text=True, check=True,
        )
        p = Path(result.stdout.strip())
        if p != Path(""):
            return p
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return Path.home() / "texmf"


# ---------------------------------------------------------------------------
# bensz-nsfc：委托给包级安装器
# ---------------------------------------------------------------------------

def _install_bensz_nsfc(ref: str, extra: list[str]) -> None:
    branch = "main"
    url = f"{RAW_BASE}/{branch}/packages/bensz-nsfc/scripts/install.py"
    print(f"  📥 下载 bensz-nsfc 安装器…")
    content = _fetch_text(url)

    with tempfile.NamedTemporaryFile(
        suffix=".py", delete=False, mode="w", encoding="utf-8", prefix="bensz-nsfc-installer-"
    ) as f:
        f.write(content)
        tmp = f.name

    try:
        cmd = [sys.executable, tmp, "install", "--ref", ref] + extra
        print(f"  ▶ {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        _die(f"bensz-nsfc 安装失败（退出码 {exc.returncode}）")
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# bensz-paper / bensz-thesis / bensz-cv：下载快照并安装到 TEXMFHOME
# ---------------------------------------------------------------------------

def _copy_package_tree(pkg_src: Path, dest: Path) -> int:
    copied = 0
    for path in pkg_src.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"__pycache__", ".DS_Store"} for part in path.parts) or path.suffix == ".pyc":
            continue
        target = dest / path.relative_to(pkg_src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    return copied


def _install_texmf_package(package_name: str, ref: str) -> None:
    print(f"  📥 下载仓库快照（{ref}）…")
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"{package_name}-install-"))
    archive = tmp_dir / "snapshot.zip"
    extract = tmp_dir / "extract"

    zip_url = f"{API_BASE}/zipball/{ref}"
    _fetch_bytes(zip_url, archive)

    print("  📦 解压中…")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract)

    roots = [p for p in extract.iterdir() if p.is_dir()]
    if not roots:
        _die("快照中未找到仓库根目录")
    repo_root = roots[0]

    pkg_src = repo_root / "packages" / package_name
    if not pkg_src.exists():
        _die(f"快照中缺少 packages/{package_name} 目录")

    texmfhome = _texmfhome()
    dest = texmfhome / "tex" / "latex" / package_name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    copied = _copy_package_tree(pkg_src, dest)

    print(f"  ✔ 已复制 {copied} 个文件到 {dest}")

    # 刷新 TeX 文件数据库
    try:
        subprocess.run(["mktexlsr"], check=True, capture_output=True)
        print("  ✔ mktexlsr 已刷新")
    except FileNotFoundError:
        print("  ℹ️  mktexlsr 未找到，请手动运行 `mktexlsr` 或 `texhash` 以刷新 TeX 文件数据库")
    except subprocess.CalledProcessError:
        print("  ⚠️  mktexlsr 执行失败，请手动刷新 TeX 文件数据库")

    shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 子命令：list
# ---------------------------------------------------------------------------

def cmd_list() -> None:
    print("支持的 LaTeX 包（来自 packages/ 目录）：\n")
    for name, info in SUPPORTED_PACKAGES.items():
        print(f"  {name}")
        print(f"    {info['description']}")
    print()
    print("安装示例：")
    print("  curl -fsSL https://raw.githubusercontent.com/huangwb8/ChineseResearchLaTeX/main/scripts/install.py \\")
    print("    | python3 - install --packages bensz-nsfc,bensz-paper,bensz-thesis,bensz-cv --ref v4.0.0")


# ---------------------------------------------------------------------------
# 子命令：install
# ---------------------------------------------------------------------------

def cmd_install(packages: list[str], ref: str, extra: list[str]) -> None:
    for pkg in packages:
        if pkg not in SUPPORTED_PACKAGES:
            _die(f"不支持的包名：{pkg}。可选：{', '.join(SUPPORTED_PACKAGES)}")

    for pkg in packages:
        info = SUPPORTED_PACKAGES[pkg]
        print(f"\n{'='*50}")
        print(f"📦 安装 {pkg}：{info['description']}")
        print(f"{'='*50}")

        if info["install_mode"] == "delegate":
            _install_bensz_nsfc(ref, extra)
        elif info["install_mode"] == "texmfhome":
            _install_texmf_package(pkg, ref)

    print(f"\n{'='*50}")
    print("✅ 所有包安装完成！")
    print(f"{'='*50}")


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="ChineseResearchLaTeX 统一 LaTeX 包安装器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command")

    # list 子命令
    sub.add_parser("list", help="列出所有支持安装的包")

    # install 子命令
    inst = sub.add_parser("install", help="安装一个或多个包")
    inst.add_argument(
        "--packages",
        default="bensz-nsfc",
        help="要安装的包，逗号分隔（默认：bensz-nsfc）。可选：bensz-nsfc,bensz-paper,bensz-thesis,bensz-cv",
    )
    inst.add_argument(
        "--ref",
        default="main",
        help="版本 tag 或分支，例如 v4.0.0（默认：main）",
    )
    inst.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="透传给子安装器的额外参数（仅 bensz-nsfc 有效）",
    )

    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "install":
        pkgs = [p.strip() for p in args.packages.split(",") if p.strip()]
        cmd_install(pkgs, args.ref, args.extra or [])
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
