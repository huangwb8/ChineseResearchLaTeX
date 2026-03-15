#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parents[1] / "packages" / "bensz-nsfc"


def parse_provides_package(style_file: Path) -> tuple[str, str]:
    content = style_file.read_text(encoding="utf-8")
    match = re.search(
        r"\\ProvidesPackage\{bensz-nsfc-common\}\[(\d{4}/\d{2}/\d{2})\s+([^\s]+)",
        content,
    )
    if not match:
        raise ValueError(f"无法解析 {style_file} 中的 ProvidesPackage")
    return match.group(1), match.group(2)


def validate_required_files() -> list[str]:
    required = [
        "bensz-nsfc-common.sty",
        "bensz-nsfc-core.sty",
        "bensz-nsfc-layout.sty",
        "bensz-nsfc-typography.sty",
        "bensz-nsfc-headings.sty",
        "bensz-nsfc-bibliography.sty",
        "profiles/bensz-nsfc-profile-general.def",
        "profiles/bensz-nsfc-profile-local.def",
        "profiles/bensz-nsfc-profile-young.def",
        "package.json",
        "README.md",
        "examples/basic-usage.tex",
    ]
    missing = [entry for entry in required if not (PACKAGE_DIR / entry).exists()]
    return missing


def compile_example() -> dict[str, str | int]:
    example_dir = PACKAGE_DIR / "examples"
    command = ["xelatex", "-interaction=nonstopmode", "-halt-on-error", "basic-usage.tex"]
    env = dict(**os.environ)
    texinputs = str(PACKAGE_DIR) + "//" + os.pathsep
    if env.get("TEXINPUTS"):
        texinputs = texinputs + env["TEXINPUTS"]
    env["TEXINPUTS"] = texinputs
    result = subprocess.run(
        command,
        cwd=example_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
        env=env,
    )
    return {"returncode": result.returncode, "stdout": result.stdout[-4000:]}


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 bensz-nsfc 公共包")
    parser.add_argument("--skip-compile", action="store_true")
    args = parser.parse_args()

    missing = validate_required_files()
    if missing:
        print(json.dumps({"status": "error", "missing_files": missing}, ensure_ascii=False, indent=2))
        return 1

    package_json = json.loads((PACKAGE_DIR / "package.json").read_text(encoding="utf-8"))
    _, style_version = parse_provides_package(PACKAGE_DIR / "bensz-nsfc-common.sty")
    status = {
        "status": "ok",
        "package_version": package_json["version"],
        "style_version": style_version,
        "templates": package_json.get("templates", {}),
    }
    if package_json["version"] != style_version:
        status["status"] = "error"
        status["reason"] = "package.json.version 与 ProvidesPackage 版本不一致"
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 1

    if not args.skip_compile:
        compile_result = compile_example()
        status["example_compile"] = compile_result
        if compile_result["returncode"] != 0:
            status["status"] = "error"
            print(json.dumps(status, ensure_ascii=False, indent=2))
            return 1

    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
