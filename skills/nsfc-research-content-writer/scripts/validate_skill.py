#!/usr/bin/env python3
"""检查独立安装包的配置、固定骨架、资源与本地链接。"""
from __future__ import annotations
import hashlib
import re
import sys
sys.dont_write_bytecode = True
if sys.version_info < (3, 11):
    raise SystemExit("需要 Python 3.11+")
from revision import SKILL_ROOT, load_config, yaml


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate() -> None:
    config = load_config()
    text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
    front, body = text.removeprefix("---\n").split("\n---\n", 1)
    meta = yaml.safe_load(front)
    require(meta["name"] == config["skill_info"]["name"], "Skill 名称不一致")
    require(meta.get("description") and meta.get("metadata", {}).get("author") == "Bensz Conan", "缺少触发描述或作者")
    require("version" not in meta and re.fullmatch(r"\d+\.\d+\.\d+", str(config["skill_info"]["version"])), "版本来源或格式错误")
    require(re.findall(r"^## (.+)$", body, re.M) == ["目标", "流程", "约束"], "二级章节顺序错误")
    require(re.findall(r"^### (.+)$", body.split("## 约束")[0], re.M) == ["输入", "执行步骤", "输出", "输出管理", "校验", "失败与恢复"], "流程子章节不完整")
    require(len(text.splitlines()) <= 500, "SKILL.md 超过 500 行")
    begin, end = "<!-- BEGIN COMMON CONSTRAINTS -->", "<!-- END COMMON CONSTRAINTS -->"
    common = text.split(begin + "\n", 1)[1].split(end, 1)[0]
    hash_line, template = common.split("\n", 1)
    require(hash_line == "<!-- Source-Hash: sha256:" + hashlib.sha256(template.encode()).hexdigest() + " -->", "公共约束摘要不匹配")
    require(config["parameters"]["output_mode"]["default"] in ("preview", "apply"), "默认输出模式错误")
    quality = config["quality_contract"]
    for lo, hi in (("subgoals_min", "subgoals_max"), ("innovation_min", "innovation_max"),
                   ("research_pages_min", "research_pages_max"), ("auxiliary_words_min", "auxiliary_words_max")):
        require(0 < quality[lo] <= quality[hi], "质量配置范围错误：" + lo)
    require(quality["plan_years"] > 0, "年度范围错误")
    for name in ("README.md", "README_EN.md", "CHANGELOG.md", "scripts/run.py", "scripts/revision.py",
                 "scripts/run_checks.py", "scripts/check_project_outputs.py", "scripts/create_test_session.py",
                 "templates/TEST_PLAN_TEMPLATE.md", "templates/TEST_REPORT_TEMPLATE.md"):
        require((SKILL_ROOT / name).is_file(), "缺少资源：" + name)
    for md in [SKILL_ROOT / "SKILL.md", *SKILL_ROOT.glob("README*.md"), *SKILL_ROOT.glob("references/*.md")]:
        for link in re.findall(r"\]\(([^)]+)\)", md.read_text(encoding="utf-8")):
            path = link.split("#", 1)[0]
            if path and not re.match(r"[a-z]+://|mailto:", path):
                require((md.parent / path).is_file(), f"失效链接 {md.name}: {path}")


def main() -> int:
    try:
        validate()
    except (AssertionError, KeyError, ValueError, OSError, TypeError) as exc:
        print("ERROR: Skill 配置或资源校验失败：" + str(exc), file=sys.stderr)
        return 1
    print("OK: Skill 配置、骨架、公共约束摘要和资源链接通过；科学质量需 AI 复核。")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
