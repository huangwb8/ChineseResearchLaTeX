#!/usr/bin/env python3
"""根据 skills/*/config.yaml 自动更新 README 的技能列表区块。

本脚本从以下数据源读取信息并渲染为 Markdown 表格：
1. ``skills/*/config.yaml`` 的 ``skill_info.version``：版本号唯一真相来源
2. 静态登记表 ``SKILL_SPECS``：技能的阶段归属、功能摘要与展示顺序
3. 版本号语义规则：v1.0.0 及以上视为 ✅ 稳定，v0.x.x 视为 🚧 开发中

渲染后的内容替换 README.md 中 ``<!-- SKILL-LIST:START -->`` 和
``<!-- SKILL-LIST:END -->`` 之间的区块。通常由 GitHub Actions 自动定时执行，
也可手动运行。

登记表与磁盘的双向校验规则：
- 目录存在 ``config.yaml`` 但未登记：报错，提示补登记（防止新 skill 漏更新）
- 已登记但目录或 ``config.yaml`` 缺失：报错（防止登记表腐化）
- 目录无 ``config.yaml``：警告并跳过（视为残留或草稿目录，不进入列表）

典型用法::

    python scripts/update_readme_skill_list.py
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - 仅在缺 PyYAML 的环境触发
    print("错误：本脚本依赖 PyYAML，请先执行 `pip install pyyaml`。", file=sys.stderr)
    raise SystemExit(1)


# 仓库根目录
REPO_ROOT = Path(__file__).resolve().parent.parent
# 目标 README 文件路径
README_PATH = REPO_ROOT / "README.md"
# 技能目录
SKILLS_DIR = REPO_ROOT / "skills"
# README 中技能列表区块的起止标记
START_MARKER = "<!-- SKILL-LIST:START -->"
END_MARKER = "<!-- SKILL-LIST:END -->"
# 合法版本号格式：x.y.z 三段
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class SkillSpec:
    """技能登记条目，对应 README 技能列表表格中的一行。

    Attributes:
        name: 技能目录名，须与 ``skills/<name>/`` 一致
        stage: 阶段展示文字（含 emoji 前缀）
        summary: 面向用户的功能摘要（一句话）
    """

    name: str
    stage: str
    summary: str


# 技能登记表：决定展示顺序与功能摘要；版本号与状态始终从 config.yaml 推导
SKILL_SPECS: tuple[SkillSpec, ...] = (
    SkillSpec(
        name="make-latex-model",
        stage="🔧 模板开发",
        summary="面向 ChineseResearchLaTeX 全仓库的模板落地与高保真对齐",
    ),
    SkillSpec(
        name="complete-example",
        stage="🔧 模板开发",
        summary="智能示例生成和补全",
    ),
    SkillSpec(
        name="transfer-old-latex-to-new",
        stage="🔧 模板开发",
        summary="模板迁移与重构编排，支持任意输入并由 AI 自主决定输出",
    ),
    SkillSpec(
        name="research-literature-search",
        stage="📚 文献调研",
        summary="独立多源文献检索、规范化、canonical 去重与 manifest 审计包",
    ),
    SkillSpec(
        name="research-literature-review",
        stage="📚 文献调研",
        summary="消费 search manifest 的显式多查询、可审计专家级综述",
    ),
    SkillSpec(
        name="research-citation-check",
        stage="📚 文献调研",
        summary="综述引用语义一致性检查",
    ),
    SkillSpec(
        name="research-topic-extractor",
        stage="📚 文献调研",
        summary="结构化综述主题提取",
    ),
    SkillSpec(
        name="research-guide-updater",
        stage="📚 文献调研",
        summary="项目指南优化与写作规范沉淀",
    ),
    SkillSpec(
        name="research-plan",
        stage="📚 文献调研",
        summary="文献驱动的科研分析策略规划",
    ),
    SkillSpec(
        name="research-literature-radar",
        stage="📚 文献调研",
        summary="分层发现、筛选并长期归档重要研究文献",
    ),
    SkillSpec(
        name="research-literature-interpretation",
        stage="📚 文献调研",
        summary="导师式解读单篇研究文献，重建机制、证据边界与可迁移启发",
    ),
    SkillSpec(
        name="research-idea",
        stage="📚 文献调研",
        summary="基于证据地图、价值筛选与假设价值认证评估科研方向，区分推荐与证据不足",
    ),
    SkillSpec(
        name="nsfc-code",
        stage="✍️ 标书写作",
        summary="NSFC 申请代码推荐（5 组 code1/code2 + 理由，只读）",
    ),
    SkillSpec(
        name="nsfc-abstract",
        stage="✍️ 标书写作",
        summary="标题建议 + NSFC 中英文摘要生成（中文≤400字；英文≤4000字符）",
    ),
    SkillSpec(
        name="nsfc-budget",
        stage="✍️ 标书写作",
        summary="NSFC 预算说明书生成（LaTeX 项目 + `budget.pdf`）",
    ),
    SkillSpec(
        name="nsfc-justification-writer",
        stage="✍️ 标书写作",
        summary="全自动立项依据语义写作、专业可读性复核与可逆写入",
    ),
    SkillSpec(
        name="nsfc-research-content-writer",
        stage="✍️ 标书写作",
        summary="NSFC 研究内容编排写作",
    ),
    SkillSpec(
        name="nsfc-research-foundation-writer",
        stage="✍️ 标书写作",
        summary="NSFC 研究基础编排写作",
    ),
    SkillSpec(
        name="nsfc-qc",
        stage="✍️ 标书写作",
        summary="NSFC 标书只读质量控制（多线程检查文风/引用/篇幅/逻辑 + 全文级缩写注册表 QC）",
    ),
    SkillSpec(
        name="nsfc-ref-alignment",
        stage="✍️ 标书写作",
        summary="NSFC 参考文献与正文引用一致性核查（只读）",
    ),
    SkillSpec(
        name="nsfc-reviewers",
        stage="✍️ 标书写作",
        summary="NSFC 标书多专家多维度评审模拟（默认 3 组、最多 5 组，含函评/会评给不过判断与资助约束识别）",
    ),
    SkillSpec(
        name="nsfc-length-aligner",
        stage="✍️ 标书写作",
        summary="NSFC 标书篇幅对齐（检查差距 → 扩写/压缩到达标）",
    ),
    SkillSpec(
        name="nsfc-humanization",
        stage="✍️ 标书写作",
        summary="分词语/句法/段落/章节四层去 AI 机器味，识别工程协议腔、术语漂移并审计安全不变量",
    ),
    SkillSpec(
        name="paper-write-sci",
        stage="📝 SCI 论文",
        summary="SCI 期刊论文写作与修订（风格化写作、数字审查、逻辑审查、写作节奏护栏、PDF/Word 渲染闭环）",
    ),
    SkillSpec(
        name="paper-explain-figures",
        stage="📝 SCI 论文",
        summary="解读论文 Figure 含义，生成高可读性 Markdown 报告（视觉理解 + 源代码检索 + 人工解读）",
    ),
    SkillSpec(
        name="paper-select-journal",
        stage="📝 SCI 论文",
        summary="SCI 投稿期刊筛选（稿件画像 + 期刊核验 + 近 3 个月相似论文证据）",
    ),
    SkillSpec(
        name="paper-know-journal",
        stage="📝 SCI 论文",
        summary="期刊投稿指南调研（官方作者指南、投稿形式要求、费用政策与社区评价）",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="用 skills/*/config.yaml 更新 README 技能列表。")
    parser.add_argument("--readme", default=str(README_PATH), help="README 文件路径")
    parser.add_argument("--skills-dir", default=str(SKILLS_DIR), help="skills 目录路径")
    return parser.parse_args()


def load_skill_version(skill_dir: Path) -> str:
    """读取单个技能目录 ``config.yaml`` 中的 ``skill_info.version``。

    Args:
        skill_dir: 技能目录路径

    Returns:
        形如 ``x.y.z`` 的版本号字符串

    Raises:
        RuntimeError: config.yaml 缺失、格式错误或版本号不合规
    """
    config_path = skill_dir / "config.yaml"
    if not config_path.exists():
        raise RuntimeError(f"技能缺少配置文件：{config_path}")

    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise RuntimeError(f"技能配置不是合法 YAML：{config_path}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("skill_info"), dict):
        raise RuntimeError(f"技能配置缺少 `skill_info` 节点：{config_path}")

    version = data["skill_info"].get("version")
    # YAML 会把不带引号的两段版本（如 1.0）解析为 float，此处统一拒绝，
    # 强制使用三段字符串写法，避免 1.10 被解析成 1.1 的精度歧义
    version_str = str(version)
    if not VERSION_PATTERN.match(version_str):
        raise RuntimeError(
            f"技能版本号必须是 `x.y.z` 三段字符串（实际为 {version!r}）：{config_path}"
        )
    return version_str


def derive_status(version: str) -> str:
    """按语义化版本规则推导状态标记：v1.0.0 及以上为稳定，否则为开发中。"""
    major = int(version.split(".")[0])
    return "✅ 稳定" if major >= 1 else "🚧 开发中"


def scan_skill_dirs(skills_dir: Path) -> tuple[set[str], list[str]]:
    """扫描 skills 目录，返回 (含 config.yaml 的技能名集合, 无 config.yaml 的目录名列表)。"""
    configured: set[str] = set()
    unconfigured: list[str] = []
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        if (entry / "config.yaml").exists():
            configured.add(entry.name)
        else:
            unconfigured.append(entry.name)
    return configured, unconfigured


def validate_registry(skills_dir: Path, registered: set[str]) -> dict[str, str]:
    """校验登记表与磁盘状态的一致性，返回技能名到版本号的映射。

    Raises:
        RuntimeError: 存在未登记的正式技能，或登记条目在磁盘上缺失
    """
    configured, unconfigured = scan_skill_dirs(skills_dir)

    errors: list[str] = []
    missing = sorted(configured - registered)
    if missing:
        errors.append(
            "以下技能目录含 config.yaml 但未在 SKILL_SPECS 登记，请补登记后再同步：\n"
            + "\n".join(f"  - {name}" for name in missing)
        )
    stale = sorted(registered - configured)
    if stale:
        errors.append(
            "以下登记条目在 skills/ 下不存在或缺少 config.yaml，请清理登记表：\n"
            + "\n".join(f"  - {name}" for name in stale)
        )
    if errors:
        raise RuntimeError("\n".join(errors))

    for name in unconfigured:
        print(f"警告：目录无 config.yaml，已跳过：{skills_dir / name}")

    return {name: load_skill_version(skills_dir / name) for name in registered}


def render_skill_table(versions: dict[str, str]) -> str:
    """根据登记表与版本号映射渲染完整的技能列表 Markdown 表格。"""
    lines = [
        "<!-- 由 scripts/update_readme_skill_list.py 自动生成，请勿手动编辑。 -->",
        "| 技能 | 阶段 | 版本 | 功能 | 状态 |",
        "|------|------|------|------|------|",
    ]
    for spec in SKILL_SPECS:
        cells = [
            f"[{spec.name}](skills/{spec.name}/)",
            spec.stage,
            f"v{versions[spec.name]}",
            spec.summary,
            derive_status(versions[spec.name]),
        ]
        if any("|" in cell for cell in cells):
            raise RuntimeError(f"技能条目含管道符 `|`，会破坏表格：{spec.name}")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def replace_marked_block(content: str, replacement: str) -> str:
    """替换 README 中由 ``SKILL-LIST:START`` 和 ``SKILL-LIST:END`` 标记包围的区块。"""
    if START_MARKER not in content or END_MARKER not in content:
        raise RuntimeError(f"README 缺少标记：{START_MARKER} / {END_MARKER}")
    start_index = content.index(START_MARKER) + len(START_MARKER)
    end_index = content.index(END_MARKER)
    return content[:start_index] + "\n" + replacement + "\n" + content[end_index:]


def update_readme(readme_path: Path, skills_dir: Path) -> bool:
    """执行同步：校验登记表 -> 渲染表格 -> 写回 README。

    Returns:
        True 表示 README 发生变更并已写入
    """
    if not readme_path.exists():
        raise RuntimeError(f"README 不存在：{readme_path}")
    if not skills_dir.is_dir():
        raise RuntimeError(f"skills 目录不存在：{skills_dir}")

    versions = validate_registry(skills_dir, {spec.name for spec in SKILL_SPECS})
    rendered_table = render_skill_table(versions)
    original_content = readme_path.read_text(encoding="utf-8")
    updated_content = replace_marked_block(original_content, rendered_table)

    if updated_content == original_content:
        print(f"README 已是最新技能列表（共 {len(SKILL_SPECS)} 项）")
        return False

    readme_path.write_text(updated_content, encoding="utf-8")
    print(f"已更新 README 技能列表（共 {len(SKILL_SPECS)} 项）")
    return True


def main() -> int:
    """脚本主入口：校验登记表 -> 渲染技能列表 -> 写入 README。"""
    args = parse_args()
    update_readme(Path(args.readme).resolve(), Path(args.skills_dir).resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc
