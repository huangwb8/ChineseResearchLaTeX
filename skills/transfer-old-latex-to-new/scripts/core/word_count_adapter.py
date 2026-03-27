"""
字数自动适配器
自动适配旧版本内容到新版本字数要求
"""

import re
from pathlib import Path
from typing import Any, Dict, Optional

from .ai_integration import AIIntegration
from .config_utils import ConfigDefaults
from .prompt_templates import WORD_COUNT_COMPRESS_TEMPLATE, WORD_COUNT_EXPAND_TEMPLATE
from .reference_guardian import ReferenceGuardian


class WordCountAdapter:
    """字数自动适配器"""

    def __init__(self, config: dict, skill_root: str):
        self.config = config
        self.skill_root = Path(skill_root)
        wc_cfg = (config.get("word_count_adaptation", {}) or {}) if isinstance(config, dict) else {}
        self.tolerance = int(wc_cfg.get("target_tolerance", ConfigDefaults.WORD_COUNT_TOLERANCE))
        self.auto_expand = bool(wc_cfg.get("auto_expand", True))
        self.auto_compress = bool(wc_cfg.get("auto_compress", True))
        self.ref_guardian = ReferenceGuardian(config)
        self.version_requirements = self._load_version_requirements()

    def _load_version_requirements(self) -> dict:
        """加载版本字数要求"""
        return {
            "2025_to_2026": {
                "立项依据": {"old": (1500, 2000), "new": (2000, 2500)},
                "研究内容": {"old": (800, 1000), "new": (1000, 1200)},
                "研究目标": {"old": (500, 800), "new": (600, 900)},
                "关键科学问题": {"old": (400, 600), "new": (500, 700)},
                "研究方案": {"old": (1000, 1500), "new": (1200, 1500)},
                "可行性分析": {"old": (500, 800), "new": (800, 1000)},
                "研究风险应对": {"old": (0, 0), "new": (300, 500)},
                "特色与创新": {"old": (600, 800), "new": (700, 900)},
                "研究基础": {"old": (1000, 1500), "new": (1500, 2000)},
                "工作条件": {"old": (400, 600), "new": (500, 700)},
            },
            "2024_to_2025": {
                "立项依据": {"old": (1200, 1500), "new": (1500, 2000)},
                "研究内容": {"old": (600, 800), "new": (800, 1000)},
                "研究目标": {"old": (400, 600), "new": (500, 800)},
                "关键科学问题": {"old": (300, 500), "new": (400, 600)},
                "研究方案": {"old": (800, 1200), "new": (1000, 1500)},
                "可行性分析": {"old": (400, 600), "new": (500, 800)},
                "特色与创新": {"old": (500, 700), "new": (600, 800)},
                "研究基础": {"old": (800, 1200), "new": (1000, 1500)},
                "工作条件": {"old": (300, 500), "new": (400, 600)},
            }
        }

    async def adapt_content(
        self,
        content: str,
        section_title: str,
        target_word_count: int,
        ai_integration: Optional[AIIntegration] = None,
    ) -> dict:
        """适配内容到目标字数（以中文字符计，排除 LaTeX 命令）"""
        if target_word_count <= 0:
            return {
                "action": "invalid_target",
                "original_count": self._count_chinese_words(content),
                "target_count": target_word_count,
                "final_count": self._count_chinese_words(content),
                "adapted_content": content,
                "method": "none",
            }

        if ai_integration is None:
            ai_integration = AIIntegration(enable_ai=True, config=self.config)

        current_count = self._count_chinese_words(content)
        deficit = int(target_word_count) - int(current_count)

        if abs(deficit) <= self.tolerance:
            return {
                "action": "within_tolerance",
                "original_count": current_count,
                "target_count": int(target_word_count),
                "final_count": current_count,
                "adapted_content": content,
                "method": "none",
            }

        # 保护引用，避免在扩写/压缩中破坏 \ref/\cite
        protected_content, ref_map = self.ref_guardian.protect_references(content)

        if deficit > 0:
            if not self.auto_expand:
                return {
                    "action": "expand_skipped",
                    "original_count": current_count,
                    "target_count": int(target_word_count),
                    "final_count": current_count,
                    "adapted_content": content,
                    "method": "disabled",
                }

            expanded = await self._ai_expand_content(protected_content, section_title, deficit, ai_integration)
            restored = self.ref_guardian.restore_references(expanded, ref_map)
            final_count = self._count_chinese_words(restored)
            changed = restored != content
            return {
                "action": "expanded" if changed else "expand_no_change",
                "original_count": current_count,
                "target_count": int(target_word_count),
                "final_count": final_count,
                "delta": final_count - current_count,
                "adapted_content": restored,
                "method": "ai" if ai_integration.is_available() else "ai_unavailable",
            }

        # deficit < 0：需要精简
        if not self.auto_compress:
            return {
                "action": "compress_skipped",
                "original_count": current_count,
                "target_count": int(target_word_count),
                "final_count": current_count,
                "adapted_content": content,
                "method": "disabled",
            }

        compressed = await self._ai_compress_content(protected_content, section_title, -deficit, ai_integration)
        restored = self.ref_guardian.restore_references(compressed, ref_map)
        final_count = self._count_chinese_words(restored)
        changed = restored != content
        return {
            "action": "compressed" if changed else "compress_no_change",
            "original_count": current_count,
            "target_count": int(target_word_count),
            "final_count": final_count,
            "delta": final_count - current_count,
            "adapted_content": restored,
            "method": "ai" if ai_integration.is_available() else "ai_unavailable",
        }

    async def adapt_content_by_version_pair(
        self,
        content: str,
        section_title: str,
        version_pair: str,
        ai_integration: Optional[AIIntegration] = None,
    ) -> dict:
        """兼容旧接口：根据版本对的字数范围做适配（以新版本目标范围的中位数为目标）"""
        requirements = self.version_requirements.get(version_pair, {})
        section_req = requirements.get(section_title)
        if not section_req:
            return {"status": "skip", "reason": "无字数要求"}

        new_min, new_max = section_req["new"]
        current_count = self._count_chinese_words(content)
        if new_min <= current_count <= new_max:
            return {"status": "ok", "current_count": current_count}

        target = int((new_min + new_max) / 2)
        result = await self.adapt_content(content, section_title, target, ai_integration=ai_integration)
        return {
            "status": "adapted",
            "current_count": current_count,
            "target_range": (new_min, new_max),
            **result,
        }

    async def _expand_content(
        self,
        content: str,
        section_title: str,
        current: int,
        target_min: int,
        target_max: int,
        ai_integration: Optional[AIIntegration] = None,
    ) -> dict:
        """扩展内容到目标字数"""
        deficit = target_min - current
        if ai_integration is None:
            ai_integration = AIIntegration(enable_ai=True, config=self.config)

        # 策略1: 调用对应写作技能扩展
        skill_mapping = {
            "立项依据": "nsfc-rationale-writer",
            "研究内容": "nsfc-aims-writer",
            "研究方案": "nsfc-methods-feasibility-writer",
            "特色与创新": "nsfc-innovation-writer",
            "研究基础": "nsfc-foundation-conditions-writer",
        }

        skill_name = skill_mapping.get(section_title)
        if skill_name:
            # TODO: 集成写作技能调用
            # 目前使用 AI 直接扩展
            pass

        # 策略2: AI 直接扩展（使用当前 AI 环境）
        expanded = await self._ai_expand_content(content, section_title, deficit, ai_integration)
        new_count = self._count_chinese_words(expanded)

        return {
            "status": "expanded",
            "original_count": current,
            "new_count": new_count,
            "expansion": new_count - current,
            "content": expanded,
            "method": "ai_direct"
        }

    async def _compress_content(
        self,
        content: str,
        section_title: str,
        current: int,
        target_min: int,
        target_max: int,
        ai_integration: Optional[AIIntegration] = None,
    ) -> dict:
        """精简内容到目标字数"""
        excess = current - target_max
        if ai_integration is None:
            ai_integration = AIIntegration(enable_ai=True, config=self.config)

        # AI 精简内容（使用当前 AI 环境）
        compressed = await self._ai_compress_content(content, section_title, excess, ai_integration)
        new_count = self._count_chinese_words(compressed)

        return {
            "status": "compressed",
            "original_count": current,
            "new_count": new_count,
            "reduction": current - new_count,
            "content": compressed,
            "method": "ai_compression"
        }

    async def _ai_expand_content(
        self,
        content: str,
        section_title: str,
        deficit: int,
        ai_integration: AIIntegration,
    ) -> str:
        """AI 直接扩展内容（优雅降级）"""
        current_count = self._count_chinese_words(content)
        target_count = current_count + deficit

        # 使用提示词模板
        prompt = WORD_COUNT_EXPAND_TEMPLATE.format(
            section_title=section_title,
            deficit=deficit,
            current_count=current_count,
            target_count=target_count,
            content=content,
        )

        def fallback() -> str:
            return content

        result = await ai_integration.process_request(
            task="expand_content",
            prompt=prompt,
            fallback=fallback,
            output_format="text",
        )
        return str(result or content).strip() or content

    async def _ai_compress_content(
        self,
        content: str,
        section_title: str,
        excess: int,
        ai_integration: AIIntegration,
    ) -> str:
        """AI 精简内容（优雅降级）"""
        current_count = self._count_chinese_words(content)
        target_count = current_count - excess

        # 使用提示词模板
        prompt = WORD_COUNT_COMPRESS_TEMPLATE.format(
            section_title=section_title,
            excess=excess,
            current_count=current_count,
            target_count=target_count,
            content=content,
        )

        def fallback() -> str:
            return content

        result = await ai_integration.process_request(
            task="compress_content",
            prompt=prompt,
            fallback=fallback,
            output_format="text",
        )
        return str(result or content).strip() or content

    def _count_chinese_words(self, content: str) -> int:
        """统计中文字数（排除 LaTeX 命令）"""
        # 移除 LaTeX 命令
        clean_content = re.sub(r'\\[a-zA-Z]+(?:\[[^\]]*\])?\{[^\}]*\}', '', content)
        clean_content = re.sub(r'\$[^$]*\$', '', clean_content)
        clean_content = re.sub(r'%.*$', '', clean_content, flags=re.MULTILINE)

        # 统计中文字符
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', clean_content)
        return len(chinese_chars)

    def generate_word_count_report(self, content: str, section_title: str, version_pair: str) -> dict:
        """生成字数报告"""
        requirements = self.version_requirements.get(version_pair, {})
        section_req = requirements.get(section_title)

        if not section_req:
            return {"error": "无字数要求"}

        old_min, old_max = section_req["old"]
        new_min, new_max = section_req["new"]
        current_count = self._count_chinese_words(content)

        old_status = "符合" if old_min <= current_count <= old_max else "不符合"
        new_status = "符合" if new_min <= current_count <= new_max else "不符合"

        return {
            "section": section_title,
            "current_count": current_count,
            "old_requirement": f"{old_min}-{old_max}",
            "new_requirement": f"{new_min}-{new_max}",
            "old_status": old_status,
            "new_status": new_status,
            "needs_adaptation": new_status == "不符合"
        }
