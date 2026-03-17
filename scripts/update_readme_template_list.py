#!/usr/bin/env python3
"""根据最新正式 GitHub Release 自动更新 README 的模板列表区块。"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"
PROJECTS_DIR = REPO_ROOT / "projects"
DEFAULT_REPO = "huangwb8/ChineseResearchLaTeX"
START_MARKER = "<!-- TEMPLATE-LIST:START -->"
END_MARKER = "<!-- TEMPLATE-LIST:END -->"
SHANGHAI_TZ = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class TemplateSpec:
    category: str
    display_name: str
    local_path: str
    asset_prefix: str | None
    school: str | None = None
    degree: str | None = None


CATEGORY_TITLES = {
    "nsfc": "NSFC 模板",
    "paper": "SCI 论文模板",
    "thesis": "毕业论文模板",
    "cv": "简历模板",
}

CATEGORY_DESCRIPTIONS = {
    "nsfc": "当前主线，优先面向正式申报与 Overleaf 打包分发。",
    "paper": "公共包 + 示例项目已落地，支持 PDF / DOCX 双输出。",
    "thesis": "公共包 + 示例项目已落地，支持 PDF 输出与像素级验收。",
    "cv": "公共包 + 示例项目已落地，支持中英文 PDF 输出与像素级验收。",
    "thesis-placeholder": "当前仅保留包级扩展位点；当仓库接入公开 thesis 示例项目后，这里会自动展示对应 Release 资产。",
}
THESIS_TEMPLATE_METADATA_NAME = "template.json"
THESIS_TEMPLATE_REQUIRED_FIELDS = ("project_name", "school", "degree")
THESIS_DEGREE_LABELS = {
    "bachelor": "学士",
    "master": "硕士",
    "doctor": "博士",
}
ISSUE_FORM_FILENAMES = {
    "paper-customization": "paper-template-customization.yml",
    "thesis-customization": "thesis-template-customization.yml",
    "docx-support": "docx-template-support.yml",
}

BASE_TEMPLATE_SPECS = (
    TemplateSpec(
        category="nsfc",
        display_name="青年 C",
        local_path="projects/NSFC_Young/",
        asset_prefix="NSFC_Young",
    ),
    TemplateSpec(
        category="nsfc",
        display_name="面上",
        local_path="projects/NSFC_General/",
        asset_prefix="NSFC_General",
    ),
    TemplateSpec(
        category="nsfc",
        display_name="地区",
        local_path="projects/NSFC_Local/",
        asset_prefix="NSFC_Local",
    ),
    TemplateSpec(
        category="paper",
        display_name="paper-sci-01",
        local_path="projects/paper-sci-01/",
        asset_prefix="paper-sci-01",
    ),
)


def discover_cv_template_specs() -> tuple[TemplateSpec, ...]:
    if not PROJECTS_DIR.exists():
        return ()

    cv_projects = sorted(
        project_dir.name
        for project_dir in PROJECTS_DIR.iterdir()
        if project_dir.is_dir() and project_dir.name.startswith("cv-")
    )
    return tuple(
        TemplateSpec(
            category="cv",
            display_name=project_name,
            local_path=f"projects/{project_name}/",
            asset_prefix=project_name,
        )
        for project_name in cv_projects
    )


def load_thesis_template_metadata(project_dir: Path) -> dict[str, str]:
    metadata_path = project_dir / THESIS_TEMPLATE_METADATA_NAME
    if not metadata_path.exists():
        raise RuntimeError(f"毕业论文项目缺少元数据文件：{metadata_path}")

    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"毕业论文项目元数据不是合法 JSON：{metadata_path}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(f"毕业论文项目元数据必须是 JSON 对象：{metadata_path}")

    normalized: dict[str, str] = {}
    for field_name in THESIS_TEMPLATE_REQUIRED_FIELDS:
        value = data.get(field_name)
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(f"毕业论文项目元数据缺少必填字段 `{field_name}`：{metadata_path}")
        normalized[field_name] = value.strip()

    if normalized["project_name"] != project_dir.name:
        raise RuntimeError(
            "毕业论文项目元数据中的 `project_name` 与目录名不一致："
            f"{metadata_path} -> {normalized['project_name']} != {project_dir.name}"
        )

    return normalized


def discover_thesis_template_specs() -> tuple[TemplateSpec, ...]:
    if not PROJECTS_DIR.exists():
        return ()

    thesis_projects = sorted(
        project_dir.name
        for project_dir in PROJECTS_DIR.iterdir()
        if project_dir.is_dir() and project_dir.name.startswith("thesis-")
    )
    if not thesis_projects:
        return (
            TemplateSpec(
                category="thesis",
                display_name="bensz-thesis",
                local_path="packages/bensz-thesis/",
                asset_prefix=None,
            ),
        )

    specs = []
    for project_name in thesis_projects:
        metadata = load_thesis_template_metadata(PROJECTS_DIR / project_name)
        specs.append(
            TemplateSpec(
                category="thesis",
                display_name=project_name,
                local_path=f"projects/{project_name}/",
                asset_prefix=project_name,
                school=metadata["school"],
                degree=metadata["degree"],
            )
        )
    return tuple(specs)


def get_template_specs() -> tuple[TemplateSpec, ...]:
    return BASE_TEMPLATE_SPECS + discover_thesis_template_specs() + discover_cv_template_specs()


def get_category_description(category: str, specs: tuple[TemplateSpec, ...]) -> str:
    if category != "thesis":
        return CATEGORY_DESCRIPTIONS[category]
    if any(spec.asset_prefix for spec in specs):
        return CATEGORY_DESCRIPTIONS["thesis"]
    return CATEGORY_DESCRIPTIONS["thesis-placeholder"]


def build_issue_form_url(repo: str, issue_form_filename: str) -> str:
    return f"https://github.com/{repo}/issues/new?template={issue_form_filename}"


def get_category_support_notes(category: str, repo: str) -> tuple[str, ...]:
    if category == "paper":
        paper_issue_url = build_issue_form_url(
            repo, ISSUE_FORM_FILENAMES["paper-customization"]
        )
        docx_issue_url = build_issue_form_url(repo, ISSUE_FORM_FILENAMES["docx-support"])
        return (
            "> SCI 模板通常需要按期刊规范或既有 Word 稿件做个性化定制；"
            f"如有这类需求，建议提交 [SCI 论文模板定制需求]({paper_issue_url})。",
            "> 如果最关键的是 `reference.docx`、目标 Word 模板或 PDF / DOCX 对齐问题，"
            f"请优先提交 [DOCX 模板问题/需求]({docx_issue_url})。",
        )
    if category == "thesis":
        thesis_issue_url = build_issue_form_url(
            repo, ISSUE_FORM_FILENAMES["thesis-customization"]
        )
        return (
            "> 毕业论文模板通常需要按学校、学院或学位规范做个性化定制；"
            f"如有这类需求，建议提交 [毕业论文模板定制需求]({thesis_issue_url})。",
        )
    return ()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="用最新正式 Release 更新 README 模板列表。")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub 仓库，格式 owner/name")
    parser.add_argument("--readme", default=str(README_PATH), help="README 文件路径")
    return parser.parse_args()


def get_api_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ChineseResearchLaTeX-template-list-updater",
    }
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_latest_release(repo: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    request = Request(url, headers=get_api_headers())
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"获取最新 Release 失败：HTTP {exc.code} {exc.reason}") from exc
    except URLError as exc:
        raise RuntimeError(f"获取最新 Release 失败：{exc.reason}") from exc


def format_release_time(iso_timestamp: str) -> str:
    dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
    local_dt = dt.astimezone(SHANGHAI_TZ)
    return local_dt.strftime("%Y-%m-%d %H:%M（UTC+8）")


def format_asset_size(size_bytes: int) -> str:
    size_mb = size_bytes / (1024 * 1024)
    if size_mb >= 10:
        return f"{size_mb:.1f} MB"
    return f"{size_mb:.2f} MB"


def build_asset_lookup(release: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {asset["name"]: asset for asset in release.get("assets", [])}


def render_asset_link(asset: dict[str, Any] | None) -> str:
    if not asset:
        return "暂未发布"
    size = format_asset_size(int(asset.get("size", 0)))
    return f"[下载]({asset['browser_download_url']})（{size}）"


def resolve_assets(
    spec: TemplateSpec,
    tag_name: str,
    assets_by_name: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not spec.asset_prefix:
        return None, None
    standard_name = f"{spec.asset_prefix}-{tag_name}.zip"
    overleaf_name = f"{spec.asset_prefix}-Overleaf-{tag_name}.zip"
    return assets_by_name.get(standard_name), assets_by_name.get(overleaf_name)


def build_status(
    spec: TemplateSpec,
    standard_asset: dict[str, Any] | None,
    overleaf_asset: dict[str, Any] | None,
) -> str:
    if not spec.asset_prefix:
        return "🚧 预留位点"
    if standard_asset and overleaf_asset:
        return "✅ 已发布"
    if standard_asset:
        return "🟡 仅标准包"
    if overleaf_asset:
        return "🟡 仅 Overleaf 包"
    return "🛠️ 等待发布"


def format_thesis_degree(degree: str) -> str:
    return THESIS_DEGREE_LABELS.get(degree.strip().lower(), degree.strip())


def build_detail_value(
    spec: TemplateSpec,
    standard_asset: dict[str, Any] | None,
    overleaf_asset: dict[str, Any] | None,
) -> str:
    return build_status(spec, standard_asset, overleaf_asset)


def build_row_values(
    category: str,
    spec: TemplateSpec,
    standard_asset: dict[str, Any] | None,
    overleaf_asset: dict[str, Any] | None,
) -> list[str]:
    template_link = f"[{spec.display_name}]({spec.local_path})"
    if category == "thesis" and spec.asset_prefix:
        if not spec.school:
            raise RuntimeError(f"毕业论文模板缺少院校元数据：{spec.local_path}")
        if not spec.degree:
            raise RuntimeError(f"毕业论文模板缺少学位元数据：{spec.local_path}")
        return [
            template_link,
            spec.school,
            format_thesis_degree(spec.degree),
            render_asset_link(standard_asset),
            render_asset_link(overleaf_asset),
        ]
    return [
        template_link,
        build_detail_value(spec, standard_asset, overleaf_asset),
        render_asset_link(standard_asset),
        render_asset_link(overleaf_asset),
    ]


def render_category_table(
    category: str,
    specs: tuple[TemplateSpec, ...],
    repo: str,
    tag_name: str,
    assets_by_name: dict[str, dict[str, Any]],
) -> str:
    if category == "thesis" and any(spec.asset_prefix for spec in specs):
        header = "| 模板 | 院校 | 学位 | 标准包 | Overleaf 包 |"
        separator = "|------|------|------|--------|-------------|"
    else:
        header = "| 模板 | 状态 | 标准包 | Overleaf 包 |"
        separator = "|------|------|--------|-------------|"
    lines = [
        f"### {CATEGORY_TITLES[category]}",
        "",
        f"> {get_category_description(category, specs)}",
        *get_category_support_notes(category, repo),
        "",
        header,
        separator,
    ]

    for spec in specs:
        standard_asset, overleaf_asset = resolve_assets(spec, tag_name, assets_by_name)
        lines.append(
            "| "
            + " | ".join(
                build_row_values(category, spec, standard_asset, overleaf_asset)
            )
            + " |"
        )

    lines.append("")
    return "\n".join(lines)


def render_template_section(repo: str, release: dict[str, Any]) -> str:
    assets_by_name = build_asset_lookup(release)
    tag_name = release["tag_name"]
    published_label = format_release_time(release["published_at"])
    template_specs = get_template_specs()
    sections = [
        "<!-- 由 scripts/update_readme_template_list.py 自动生成，请勿手动编辑。 -->",
        (
            "> ⚠️ **建议优先使用下表中的最新正式 zip 下载包。** "
            f"该列表由 GitHub Actions 每小时自动检查一次，也支持手动触发同步。"
        ),
        (
            f"> 当前同步源：`{repo}@{tag_name}`，发布时间：{published_label}。"
        ),
        "",
    ]

    for category in ("nsfc", "paper", "thesis", "cv"):
        category_specs = tuple(spec for spec in template_specs if spec.category == category)
        if not category_specs:
            continue
        sections.append(
            render_category_table(
                category=category,
                specs=category_specs,
                repo=repo,
                tag_name=tag_name,
                assets_by_name=assets_by_name,
            )
        )

    return "\n".join(sections).rstrip()


def replace_marked_block(content: str, replacement: str) -> str:
    if START_MARKER not in content or END_MARKER not in content:
        raise RuntimeError(f"README 缺少标记：{START_MARKER} / {END_MARKER}")
    start_index = content.index(START_MARKER) + len(START_MARKER)
    end_index = content.index(END_MARKER)
    return content[:start_index] + "\n" + replacement + "\n" + content[end_index:]


def main() -> int:
    args = parse_args()
    readme_path = Path(args.readme).resolve()
    if not readme_path.exists():
        raise RuntimeError(f"README 不存在：{readme_path}")

    release = fetch_latest_release(args.repo)
    rendered_section = render_template_section(args.repo, release)
    original_content = readme_path.read_text(encoding="utf-8")
    updated_content = replace_marked_block(original_content, rendered_section)

    if updated_content == original_content:
        print(f"README 已是最新模板列表：{release['tag_name']}")
        return 0

    readme_path.write_text(updated_content, encoding="utf-8")
    print(f"已更新 README 模板列表：{release['tag_name']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
