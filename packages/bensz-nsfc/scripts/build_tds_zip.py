#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_DIR.parents[1]


def main() -> int:
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

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
