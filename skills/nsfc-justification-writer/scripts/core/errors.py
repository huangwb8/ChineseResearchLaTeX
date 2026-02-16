#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations


class SkillError(Exception):
    """
    统一的 Skill 异常基类：携带可读的修复建议（供 CLI 友好输出）。
    """

    def __init__(self, message: str, *, fix_suggestion: str = "") -> None:
        super().__init__(message)
        self.fix_suggestion = str(fix_suggestion or "").strip()


class TargetFileNotFoundError(SkillError):
    def __init__(self, *, target_relpath: str, project_root: str) -> None:
        super().__init__(
            f"目标文件不存在：{target_relpath}",
            fix_suggestion=(
                "请确认：\n"
                f"1) 项目根目录是否正确：{project_root}\n"
                "2) 标书模板是否已初始化（是否存在 extraTex/ 与 references/）\n"
                f"3) 目标文件路径是否应为：{target_relpath}\n"
            ),
        )


class MissingCitationKeysError(SkillError):
    def __init__(self, missing_keys: list[str]) -> None:
        self.missing_keys = [str(x) for x in (missing_keys or []) if str(x).strip()]
        super().__init__(
            f"检测到 {len(self.missing_keys)} 个缺失引用 bibkey（为避免幻觉引用，已拒绝写入）",
            fix_suggestion=(
                "建议：\n"
                "- 优先：提供 DOI/链接（或可核验题录信息），补齐并核验 references/*.bib 后重试\n"
                "- 或：删除未核验引用/改写为无引用的可核验描述\n"
                "- 如确需忽略该检查：在命令中加入 `--allow-missing-citations`\n"
            ),
        )


class BackupNotFoundError(SkillError):
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(
            f"未找到 run_id={run_id} 的备份文件",
            fix_suggestion=(
                "建议：先运行 `list-runs` 查看可用 run_id；\n"
                "或确认 `config.yaml:workspace.runs_dir` 是否指向正确目录（默认 `tests/_artifacts/runs/`）。"
            ),
        )


class SectionNotFoundError(SkillError):
    def __init__(self, *, title: str, suggestions: list[str]) -> None:
        sug = "\n".join([f"- {t}" for t in suggestions[:10]]) if suggestions else "（无）"
        super().__init__(
            f"未找到匹配的小标题：{title}",
            fix_suggestion=("可用的小标题候选：\n" + sug + "\n\n提示：可加 `--suggest-alias` 输出更多候选。"),
        )


class QualityGateError(SkillError):
    def __init__(self, *, forbidden_phrases: list[str], avoid_commands: list[str]) -> None:
        self.forbidden_phrases = [str(x) for x in (forbidden_phrases or []) if str(x).strip()]
        self.avoid_commands = [str(x) for x in (avoid_commands or []) if str(x).strip()]
        parts = []
        if self.forbidden_phrases:
            parts.append("不可核验表述：" + "、".join(self.forbidden_phrases[:10]))
        if self.avoid_commands:
            parts.append("可能破坏模板的命令：" + "、".join(self.avoid_commands[:10]))
        detail = "；".join(parts) if parts else "命中质量闸门"
        super().__init__(
            f"新正文命中质量闸门，已拒绝写入（{detail}）",
            fix_suggestion=(
                "建议：\n"
                "- 删除/替换上述绝对化表述，改为“可核验的证据链”表述\n"
                "- 避免在正文中直接使用 \\section/\\subsection/\\input/\\include 等结构命令\n"
                "- 修订后重试；如确需跳过该闸门：不要使用 `--strict-quality`\n"
            ),
        )
