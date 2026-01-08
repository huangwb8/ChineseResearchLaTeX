"""
引用强制守护者
保护 LaTeX 引用不被 AI 破坏
"""

import hashlib
import re
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

    # 占位符前缀（使用特殊字符避免与正文冲突）
    PLACEHOLDER_PREFIX = "___REF_"
    PLACEHOLDER_SUFFIX = "___"

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

                # 生成唯一占位符（使用 SHA256 哈希确保唯一性）
                hash_input = f"{ref_type}:{ref_key}:{id(original)}".encode('utf-8')
                hash_hex = hashlib.sha256(hash_input).hexdigest()[:12]
                placeholder = f"{self.PLACEHOLDER_PREFIX}{ref_type.upper()}_{hash_hex}{self.PLACEHOLDER_SUFFIX}"

                # 记录映射关系
                ref_map[placeholder] = original

                # 替换为占位符（只替换第一个匹配，避免重复替换）
                protected_content = protected_content.replace(original, placeholder, 1)

        return protected_content, ref_map

    def restore_references(self, protected_content: str, ref_map: Dict[str, str]) -> str:
        """
        恢复所有引用

        使用正则表达式确保精确匹配占位符，避免部分替换问题
        """
        if not self.enabled or not ref_map:
            return protected_content

        restored_content = protected_content

        # 按占位符长度降序恢复（避免部分替换）
        for placeholder in sorted(ref_map.keys(), key=len, reverse=True):
            # 使用正则表达式精确替换（word boundary）
            pattern = re.escape(placeholder)
            # 注意：replacement 字符串若包含反斜杠（如 \cite/\ref），直接传给 re.sub 会触发转义解析；
            # 用函数替换可避免 "bad escape"。
            replacement = ref_map[placeholder]
            restored_content = re.sub(pattern, lambda _m, r=replacement: r, restored_content)

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
        """
        尝试修复被破坏的引用

        使用模糊匹配来恢复被部分修改的占位符
        """
        if not self.enabled or not ref_map:
            return content

        repaired_content = content

        # 查找被部分破坏的引用
        for placeholder, original in ref_map.items():
            if placeholder not in repaired_content:
                # 尝试模糊匹配（占位符可能被 AI 修改）
                # 检查是否包含类型标识
                ref_type = placeholder.split("_")[2] if "_" in placeholder else ""
                type_pattern = f"{self.PLACEHOLDER_PREFIX}{ref_type}"

                # 查找可能的损坏占位符
                for match in re.finditer(re.escape(type_pattern) + r"_[A-Fa-f0-9]+", repaired_content):
                    damaged = match.group(0)
                    # 尝试修复（检查哈希长度是否正确）
                    hash_part = damaged.split("_")[-1].replace(self.PLACEHOLDER_SUFFIX, "")
                    if len(hash_part) < 12:  # 哈希被截断
                        # 查找最接近的占位符
                        for ref_placeholder in ref_map.keys():
                            if ref_placeholder.startswith(type_pattern):
                                repaired_content = repaired_content.replace(damaged, ref_placeholder)
                                break

        # 恢复引用
        return self.restore_references(repaired_content, ref_map)
