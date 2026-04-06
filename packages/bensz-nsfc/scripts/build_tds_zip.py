#!/usr/bin/env python3
"""打包 bensz-nsfc 为 TDS（TeX Directory Structure）兼容 ZIP。

将 ``packages/bensz-nsfc/`` 和 ``packages/bensz-fonts/`` 中的运行时文件
按 TDS 目录布局打包为可分发的 zip 文件，主要用于 CTAN 发布或供用户手动安装到 TEXMFHOME。

TDS 目录映射规则：
- ``examples/`` 下的文件 → ``doc/latex/bensz-nsfc/``
- ``README.md`` 和 ``package.json`` → ``doc/latex/bensz-nsfc/``
- 其余文件（.sty、.def、.bst、字体等） → ``tex/latex/bensz-nsfc/``
- bensz-fonts 包同理映射到 ``tex/latex/bensz-fonts/``（文档类文件到 ``doc/latex/bensz-fonts/``）

典型用法::

    python build_tds_zip.py            # 输出到 dist/bensz-nsfc-{version}-tds.zip
    python build_tds_zip.py --out /tmp/bensz-nsfc.zip
"""
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

# bensz-nsfc 公共包根目录（packages/bensz-nsfc）
PACKAGE_DIR = Path(__file__).resolve().parents[1]
# 仓库根目录
REPO_ROOT = PACKAGE_DIR.parents[1]
# bensz-fonts 共享字体包根目录（packages/bensz-fonts）
FONTS_PACKAGE_DIR = REPO_ROOT / "packages" / "bensz-fonts"


def main() -> int:
    """CLI 入口：读取 package.json 版本号，遍历 bensz-nsfc 和 bensz-fonts 包文件，按 TDS 布局写入 zip。默认输出到 ``dist/bensz-nsfc-{version}-tds.zip``。"""
    parser = argparse.ArgumentParser(description="打包 bensz-nsfc TDS zip")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    package_json = json.loads((PACKAGE_DIR / "package.json").read_text(encoding="utf-8"))
    version = package_json["version"]
    output = args.out or (REPO_ROOT / "dist" / f"bensz-nsfc-{version}-tds.zip")
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for file_path in PACKAGE_DIR.rglob("*"):
            if file_path.is_dir():
                continue
            relative = file_path.relative_to(PACKAGE_DIR)
            if relative.parts[0] == "examples":
                archive_name = Path("doc") / "latex" / "bensz-nsfc" / relative
            elif relative.name in {"README.md", "package.json"}:
                archive_name = Path("doc") / "latex" / "bensz-nsfc" / relative
            else:
                archive_name = Path("tex") / "latex" / "bensz-nsfc" / relative
            bundle.write(file_path, archive_name.as_posix())
        if FONTS_PACKAGE_DIR.exists():
            for file_path in FONTS_PACKAGE_DIR.rglob("*"):
                if file_path.is_dir():
                    continue
                relative = file_path.relative_to(FONTS_PACKAGE_DIR)
                if relative.name in {"README.md", "package.json"}:
                    archive_name = Path("doc") / "latex" / "bensz-fonts" / relative
                else:
                    archive_name = Path("tex") / "latex" / "bensz-fonts" / relative
                bundle.write(file_path, archive_name.as_posix())

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
