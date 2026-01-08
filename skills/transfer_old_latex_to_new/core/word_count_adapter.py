"""
字数自动适配器
自动适配旧版本内容到新版本字数要求
"""

import re
import json
from pathlib import Path
from typing import Dict, Tuple, Optional


class WordCountAdapter:
    """字数自动适配器"""

    def __init__(self, config: dict, skill_root: str):
        self.config = config
        self.skill_root = Path(skill_root)
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

    async def adapt_content(self, content: str, section_title: str, version_pair: str) -> dict:
        """适配内容到新版本字数要求"""
        requirements = self.version_requirements.get(version_pair, {})
        section_req = requirements.get(section_title)

        if not section_req:
            return {"status": "skip", "reason": "无字数要求"}

        old_min, old_max = section_req["old"]
        new_min, new_max = section_req["new"]
        current_count = self._count_chinese_words(content)

        # 判断是否需要适配
        if new_min <= current_count <= new_max:
            return {"status": "ok", "current_count": current_count}

        # 字数不足：扩展内容
        if current_count < new_min:
            return await self._expand_content(content, section_title, current_count, new_min, new_max)

        # 字数过多：精简内容
        if current_count > new_max:
            return await self._compress_content(content, section_title, current_count, new_min, new_max)

    async def _expand_content(self, content: str, section_title: str, current: int, target_min: int, target_max: int) -> dict:
        """扩展内容到目标字数"""
        deficit = target_min - current

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
        expanded = await self._ai_expand_content(content, section_title, deficit)
        new_count = self._count_chinese_words(expanded)

        return {
            "status": "expanded",
            "original_count": current,
            "new_count": new_count,
            "expansion": new_count - current,
            "content": expanded,
            "method": "ai_direct"
        }

    async def _compress_content(self, content: str, section_title: str, current: int, target_min: int, target_max: int) -> dict:
        """精简内容到目标字数"""
        excess = current - target_max

        # AI 精简内容（使用当前 AI 环境）
        compressed = await self._ai_compress_content(content, section_title, excess)
        new_count = self._count_chinese_words(compressed)

        return {
            "status": "compressed",
            "original_count": current,
            "new_count": new_count,
            "reduction": current - new_count,
            "content": compressed,
            "method": "ai_compression"
        }

    async def _ai_expand_content(self, content: str, section_title: str, deficit: int) -> str:
        """AI 直接扩展内容（使用当前 AI 环境）"""
        # 使用 Skill 工具调用当前 AI
        from skill_core import call_ai

        prompt = f"""你是 NSFC 标书写作专家。请扩展以下"{section_title}"的内容。

要求：
1. 扩展约 {deficit} 字（当前 {self._count_chinese_words(content)} 字，目标约 {self._count_chinese_words(content) + deficit} 字）
2. 保持原有逻辑和核心论点
3. 增加论据、案例、数据支撑
4. 深化分析层次
5. 保持学术严谨性

原文：
{content}

请直接输出扩展后的完整内容，不要解释。"""

        try:
            response = await call_ai(prompt, max_tokens=4000)
            return response.strip()
        except Exception as e:
            # AI 调用失败时返回原内容
            print(f"[WordCountAdapter] AI 扩展失败: {e}")
            return content

    async def _ai_compress_content(self, content: str, section_title: str, excess: int) -> str:
        """AI 精简内容（使用当前 AI 环境）"""
        # 使用 Skill 工具调用当前 AI
        from skill_core import call_ai

        prompt = f"""你是 NSFC 标书写作专家。请精简以下"{section_title}"的内容。

要求：
1. 精简约 {excess} 字（当前 {self._count_chinese_words(content)} 字，目标约 {self._count_chinese_words(content) - excess} 字）
2. 保留所有核心论点和关键信息
3. 删除冗余表述和重复内容
4. 保持逻辑连贯性
5. 保持学术严谨性

原文：
{content}

请直接输出精简后的完整内容，不要解释。"""

        try:
            response = await call_ai(prompt, max_tokens=4000)
            return response.strip()
        except Exception as e:
            # AI 调用失败时返回原内容
            print(f"[WordCountAdapter] AI 精简失败: {e}")
            return content

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
