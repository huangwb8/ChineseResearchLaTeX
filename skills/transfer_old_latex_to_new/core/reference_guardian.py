"""
引用强制守护者
保护 LaTeX 引用不被 AI 破坏
"""

import re
import uuid
from typing import Dict, List, Tuple, Set


class ReferenceGuardian:
    """引用强制守护者"""

    # 所有需要保护的引用模式
    PATTERNS = {
        "ref": r'\\ref\{([^}]+)\}',
        "cite": r'\\cite\{([^}]+)\}',
        "citep": r'\\citep\{([^}]+)\}',
        "citet": r'\\citet\{([^}]+)\}',
        "eqref": r'\\eqref\{([^}]+)\}',
        "label": r'\\label\{([^}]+)\}',
        "includegraphics": r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}',
        "lstinputlisting": r'\\lstinputlisting(?:\[[^\]]*\])?\{([^}]+)\}',
    }

    def __init__(self, config: dict):
        self.config = config
        self.enabled = config.get("reference_protection", {}).get("enabled", True)

    def protect_references(self, content: str) -> Tuple[str, Dict[str, str]]:
        """保护所有引用，返回 (保护后内容, 引用映射表)"""
        if not self.enabled:
            return content, {}

        protected_content = content
        ref_map = {}

        for ref_type, pattern in self.PATTERNS.items():
            matches = list(re.finditer(pattern, protected_content))

            for match in matches:
                original = match.group(0)
                ref_key = match.group(1)

                # 生成唯一占位符
                placeholder = f"__REF_{ref_type.upper()}_{uuid.uuid4().hex[:8]}__"

                # 记录映射关系
                ref_map[placeholder] = original

                # 替换为占位符
                protected_content = protected_content.replace(original, placeholder, 1)

        return protected_content, ref_map

    def restore_references(self, protected_content: str, ref_map: Dict[str, str]) -> str:
        """恢复所有引用"""
        if not self.enabled or not ref_map:
            return protected_content

        restored_content = protected_content

        # 按占位符长度降序恢复（避免部分替换）
        for placeholder in sorted(ref_map.keys(), key=len, reverse=True):
            restored_content = restored_content.replace(placeholder, ref_map[placeholder])

        return restored_content

    def validate_references(self, content: str, original_refs: Set[str]) -> dict:
        """验证引用完整性"""
        current_refs = self._extract_all_references(content)

        missing = original_refs - current_refs
        added = current_refs - original_refs

        return {
            "valid": len(missing) == 0,
            "total_original": len(original_refs),
            "total_current": len(current_refs),
            "missing": list(missing),
            "added": list(added),
            "missing_count": len(missing),
        }

    def _extract_all_references(self, content: str) -> Set[str]:
        """提取所有引用"""
        refs = set()

        for pattern in self.PATTERNS.values():
            matches = re.findall(pattern, content)
            refs.update(matches)

        return refs

    def generate_reference_report(self, content: str) -> dict:
        """生成引用报告"""
        report = {}

        for ref_type, pattern in self.PATTERNS.items():
            matches = re.findall(pattern, content)
            report[ref_type] = {
                "count": len(matches),
                "items": matches
            }

        report["total"] = sum(r["count"] for r in report.values())

        return report

    def repair_references(self, content: str, ref_map: Dict[str, str]) -> str:
        """尝试修复被破坏的引用"""
        if not self.enabled or not ref_map:
            return content

        repaired_content = content

        # 查找被部分破坏的引用（如 __REF_CITE_1234__ → __REF_CITE）
        for placeholder, original in ref_map.items():
            if placeholder not in repaired_content:
                # 尝试模糊匹配
                partial = placeholder[:20]  # 取前20个字符
                if partial in repaired_content:
                    repaired_content = repaired_content.replace(partial, placeholder)

        # 恢复引用
        return self.restore_references(repaired_content, ref_map)
