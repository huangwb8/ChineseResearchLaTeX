"""
SecurityManager - 安全管理器
🔒 增强的安全保护：系统文件完整性校验 + 内容安全扫描 + 访问控制
"""

import hashlib
import re
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum


class SecurityLevel(Enum):
    """安全级别"""
    SAFE = "safe"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SecurityViolation:
    """安全违规记录"""
    level: SecurityLevel
    type: str  # "system_file", "format_injection", "integrity_check"
    file: str
    message: str
    line_number: Optional[int] = None
    context: Optional[str] = None


class SecurityError(Exception):
    """安全异常"""
    pass


class SystemFileModificationError(SecurityError):
    """系统文件修改异常"""
    pass


class FormatInjectionError(SecurityError):
    """格式注入异常"""
    pass


class IntegrityCheckError(SecurityError):
    """完整性校验异常"""
    pass


class SecurityManager:
    """
    🔒 安全管理器：统一的安全检查和访问控制

    核心功能：
    1. 系统文件黑名单保护
    2. 文件完整性哈希校验
    3. 格式注入检测
    4. 自动清理危险内容
    """

    # ========== 默认配置（可被 config.yaml 覆盖） ==========
    DEFAULT_SYSTEM_FILE_BLACKLIST = [
        "main.tex",
        "extraTex/@config.tex",
        "@config.tex",
    ]
    DEFAULT_FORMAT_KEYWORDS = [
        r"\\geometry\{",
        r"\\setlength\{",
        r"\\setlength\{\\tabcolsep\}",
        r"\\definecolor\{",
        r"\\setCJKfamilyfont",
        r"\\setmainfont",
        r"\\setCJKmainfont",
        r"\\renewcommand\{\\baselinestretch\}",
        r"\\renewcommand\{\\arraystretch\}",
        r"\\titleformat\{",
        r"\\titlespacing",
        r"\\setlist",
        r"\\newcommand",
        r"\\renewcommand",
        r"\\newcolumntype",
        r"\\DeclareMathOperator",
        r"\\usepackage\{",
        r"\\documentclass",
    ]
    DEFAULT_EDITABLE_PATTERNS = [
        r"^extraTex/\d+\.\d+.*\.tex$",
        r"^references/reference\.tex$",
    ]

    def __init__(
        self,
        project_path: Path,
        hash_file: Optional[Path] = None,
        enabled_checks: Optional[Dict[str, bool]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            project_path: 项目根目录
            hash_file: 哈希存储文件（默认：.format_hashes.json）
            enabled_checks: 启用的检查项
                {
                    "system_file": True,      # 系统文件黑名单检查
                    "integrity": True,        # 完整性校验
                    "format_injection": True, # 格式注入检查
                    "section_hierarchy": True # 章节层级规范检查（input tex）
                }
        """
        self.project_path = Path(project_path)
        self.hash_file = Path(hash_file) if hash_file else self.project_path / ".format_hashes.json"

        cfg = config or {}
        security_cfg = cfg.get("security", {}) if isinstance(cfg, dict) else {}
        enabled_from_cfg = security_cfg.get("enabled_checks", {}) if isinstance(security_cfg, dict) else {}
        self.enabled_checks = enabled_checks or enabled_from_cfg or {
            "system_file": True,
            "integrity": True,
            "format_injection": True,
            "section_hierarchy": True,
        }

        sys_cfg = security_cfg.get("system_files", {}) if isinstance(security_cfg, dict) else {}
        self.system_file_blacklist = list(sys_cfg.get("blacklist") or self.DEFAULT_SYSTEM_FILE_BLACKLIST)
        self.editable_patterns = list(sys_cfg.get("editable_patterns") or self.DEFAULT_EDITABLE_PATTERNS)
        self.format_keywords = list(security_cfg.get("format_keywords_blacklist") or self.DEFAULT_FORMAT_KEYWORDS)

        # 加载已知哈希
        self.known_hashes = self._load_hashes()

        # 安全违规记录
        self.violations: List[SecurityViolation] = []

    # ========== 哈希管理 ==========

    def _load_hashes(self) -> Dict[str, str]:
        """加载已知哈希值"""
        if not self.hash_file.exists():
            return {}

        try:
            with open(self.hash_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_hashes(self):
        """保存哈希值"""
        with open(self.hash_file, 'w', encoding='utf-8') as f:
            json.dump(self.known_hashes, f, indent=2, ensure_ascii=False)

    def _compute_hash(self, file_path: Path) -> str:
        """计算文件的 SHA256 哈希值"""
        content = file_path.read_text(encoding="utf-8")
        return hashlib.sha256(content.encode()).hexdigest()

    def initialize_hashes(self, force: bool = False) -> Dict[str, str]:
        """
        初始化系统文件哈希值

        Args:
            force: 是否强制重新计算（覆盖已有哈希）

        Returns:
            计算的哈希值字典
        """
        computed_hashes = {}

        for sys_file in self.system_file_blacklist:
            file_path = self.project_path / sys_file
            if file_path.exists():
                computed_hashes[sys_file] = self._compute_hash(file_path)

                # 只在新文件或强制模式下保存
                if force or sys_file not in self.known_hashes:
                    self.known_hashes[sys_file] = computed_hashes[sys_file]

        self._save_hashes()
        return computed_hashes

    # ========== 安全检查 ==========

    def check_system_file_access(self, file_path: Path) -> bool:
        """
        检查文件是否为系统文件（黑名单）

        Args:
            file_path: 文件路径

        Returns:
            True 如果是系统文件（禁止访问）

        Raises:
            SystemFileModificationError: 如果尝试访问系统文件
        """
        if not self.enabled_checks.get("system_file", True):
            return False

        try:
            # 统一使用 posix 风格路径，避免 Windows 分隔符导致白名单/黑名单失效
            relative_path = file_path.resolve().relative_to(self.project_path.resolve()).as_posix()
        except ValueError:
            violation = SecurityViolation(
                level=SecurityLevel.CRITICAL,
                type="system_file",
                file=str(file_path),
                message=f"🚨 拒绝访问项目目录之外的文件：{file_path}"
            )
            self.violations.append(violation)
            raise SecurityError(violation.message)

        # 检查黑名单
        if relative_path in self.system_file_blacklist:
            violation = SecurityViolation(
                level=SecurityLevel.CRITICAL,
                type="system_file",
                file=relative_path,
                message=f"🚨 禁止访问系统文件：{relative_path}"
            )
            self.violations.append(violation)
            raise SystemFileModificationError(violation.message)

        # 检查白名单模式
        is_editable = any(
            re.match(pattern, relative_path)
            for pattern in self.editable_patterns
        )

        if not is_editable:
            violation = SecurityViolation(
                level=SecurityLevel.WARNING,
                type="system_file",
                file=relative_path,
                message=f"⚠️ 文件不在可编辑白名单中：{relative_path}"
            )
            self.violations.append(violation)

        return False

    def check_integrity(self, file_path: Optional[Path] = None) -> Dict[str, bool]:
        """
        检查系统文件完整性

        Args:
            file_path: 指定检查的文件（None 表示检查所有系统文件）

        Returns:
            {文件路径: 是否完整}

        Raises:
            IntegrityCheckError: 如果完整性校验失败
        """
        if not self.enabled_checks.get("integrity", True):
            return {}

        if not self.known_hashes:
            # 哈希为空，自动初始化
            self.initialize_hashes()
            return {}

        results: Dict[str, bool] = {}

        if file_path is None:
            sys_files = list(self.system_file_blacklist)
        else:
            try:
                sys_files = [file_path.resolve().relative_to(self.project_path.resolve()).as_posix()]
            except ValueError:
                # 外部文件在 check_system_file_access 已拦截；这里作为不通过处理
                raise IntegrityCheckError(f"🚨 完整性校验拒绝检查项目外文件：{file_path}")

        for sys_file in sys_files:
            file_full_path = self.project_path / sys_file

            if not file_full_path.exists():
                continue

            current_hash = self._compute_hash(file_full_path)
            known_hash = self.known_hashes.get(sys_file)

            if known_hash is None:
                # 未知文件，自动添加
                self.known_hashes[sys_file] = current_hash
                self._save_hashes()
                results[sys_file] = True
            else:
                is_valid = current_hash == known_hash
                results[sys_file] = is_valid

                if not is_valid:
                    violation = SecurityViolation(
                        level=SecurityLevel.CRITICAL,
                        type="integrity_check",
                        file=sys_file,
                        message=(
                            f"🚨 系统文件完整性校验失败：{sys_file}\n"
                            f"已知哈希：{known_hash[:16]}...\n"
                            f"当前哈希：{current_hash[:16]}...\n"
                            f"为确保模板样式安全，操作已中止。"
                        )
                    )
                    self.violations.append(violation)
                    raise IntegrityCheckError(violation.message)

        return results

    def check_format_injection(
        self,
        content: str,
        file_path: Optional[Path] = None
    ) -> Tuple[bool, List[SecurityViolation]]:
        """
        检查内容中的格式注入

        Args:
            content: 文件内容
            file_path: 文件路径（可选，用于日志）

        Returns:
            (是否安全, 违规列表)
        """
        if not self.enabled_checks.get("format_injection", True):
            return True, []

        violations = []
        lines = content.split("\n")

        for line_no, line in enumerate(lines, 1):
            # 注释行不参与格式注入判定，避免误报（例如注释中提到 \\geometry）
            if line.lstrip().startswith("%"):
                continue
            for keyword in self.format_keywords:
                if re.search(keyword, line):
                    violations.append(SecurityViolation(
                        level=SecurityLevel.WARNING,
                        type="format_injection",
                        file=str(file_path) if file_path else "unknown",
                        message=f"检测到格式注入尝试：{keyword.strip()}",
                        line_number=line_no,
                        context=line.strip()
                    ))

        is_safe = len(violations) == 0
        if not is_safe:
            self.violations.extend(violations)

        return is_safe, violations

    def sanitize_content(self, content: str) -> str:
        """
        清理内容中的格式注入

        Args:
            content: 原始内容

        Returns:
            清理后的内容
        """
        lines = content.split("\n")
        sanitized_lines = []

        for line_no, line in enumerate(lines, 1):
            if line.lstrip().startswith("%"):
                sanitized_lines.append(line)
                continue
            is_dangerous = any(
                re.search(keyword, line)
                for keyword in self.format_keywords
            )

            if is_dangerous:
                # 注释行里不能保留原始危险命令，否则二次扫描仍会命中关键词。
                # 这里仅保留去掉反斜杠后的“可读提示”，避免误伤 LaTeX 关键词匹配。
                sanitized_preview = line.replace("\\", "")
                sanitized_lines.append(f"% 🚨 已自动移除格式注入：{sanitized_preview}")
            else:
                sanitized_lines.append(line)

        return "\n".join(sanitized_lines)

    # ========== 统一检查接口 ==========

    def pre_edit_check(self, file_path: Path) -> bool:
        """
        编辑前的统一检查

        Args:
            file_path: 要编辑的文件

        Returns:
            是否通过检查

        Raises:
            SecurityError: 如果检查失败
        """
        # 1. 系统文件黑名单检查
        self.check_system_file_access(file_path)

        # 2. 完整性校验
        self.check_integrity()

        return True

    def pre_apply_check(
        self,
        file_path: Path,
        new_content: str,
        auto_sanitize: bool = True
    ) -> str:
        """
        应用前的检查和清理

        Args:
            file_path: 目标文件
            new_content: 新内容
            auto_sanitize: 是否自动清理

        Returns:
            检查/清理后的内容

        Raises:
            SecurityError: 如果检查失败且未启用自动清理
        """
        # 再次检查系统文件
        self.check_system_file_access(file_path)

        # 章节层级规范检查（extraTex/input 类 tex）
        if self.enabled_checks.get("section_hierarchy", True):
            self.check_section_hierarchy(file_path, new_content)

        # 检查格式注入
        is_safe, violations = self.check_format_injection(new_content, file_path)

        if not is_safe:
            if auto_sanitize:
                # 自动清理（避免直接 print 污染输出；违规信息可通过 get_violations_report 获取）
                new_content = self.sanitize_content(new_content)

                # 二次验证
                is_safe, _ = self.check_format_injection(new_content, file_path)
                if not is_safe:
                    raise FormatInjectionError(
                        "🚨 生成内容包含不安全的格式指令，且自动清理失败"
                    )
            else:
                raise FormatInjectionError(
                    f"🚨 生成内容包含 {len(violations)} 处格式注入尝试\n"
                    f"请检查内容并移除格式相关指令"
                )

        return new_content

    def check_section_hierarchy(self, file_path: Path, content: str) -> bool:
        """
        检查 input 类 tex 的章节层级是否符合约束：
        - 禁止使用 \\section / \\subsection
        - 必须同时包含 \\subsubsection 与 \\subsubsubsection（至少各 1 次）
        """
        try:
            relative_path = file_path.resolve().relative_to(self.project_path.resolve()).as_posix()
        except ValueError:
            relative_path = str(file_path)

        # 仅对 extraTex/*.tex（且非 @config.tex）启用
        if not (relative_path.startswith("extraTex/") and relative_path.endswith(".tex")):
            return True
        if relative_path.endswith("extraTex/@config.tex") or relative_path.endswith("@config.tex"):
            return True

        forbidden = []
        if re.search(r"\\section\{", content):
            forbidden.append("\\section")
        if re.search(r"\\subsection\{", content):
            forbidden.append("\\subsection")
        if forbidden:
            msg = f"🚨 input 类 tex 禁止使用：{', '.join(forbidden)}（文件：{relative_path}）"
            self.violations.append(SecurityViolation(
                level=SecurityLevel.CRITICAL,
                type="section_hierarchy",
                file=relative_path,
                message=msg,
            ))
            raise SecurityError(msg)

        if not re.search(r"\\subsubsection\{", content) or not re.search(r"\\subsubsubsection\{", content):
            msg = f"🚨 input 类 tex 必须同时包含 \\subsubsection 与 \\subsubsubsection（文件：{relative_path}）"
            self.violations.append(SecurityViolation(
                level=SecurityLevel.CRITICAL,
                type="section_hierarchy",
                file=relative_path,
                message=msg,
            ))
            raise SecurityError(msg)

        return True

    # ========== 违规报告 ==========

    def get_violations_report(self) -> str:
        """生成违规报告"""
        if not self.violations:
            return "✅ 未检测到安全违规"

        report_lines = ["🚨 安全违规报告：", ""]

        for violation in self.violations:
            level_icon = {
                SecurityLevel.SAFE: "✅",
                SecurityLevel.WARNING: "⚠️",
                SecurityLevel.CRITICAL: "🚨",
            }[violation.level]

            report_lines.append(f"{level_icon} [{violation.type.upper()}] {violation.message}")
            if violation.line_number:
                report_lines.append(f"   位置：第 {violation.line_number} 行")
            if violation.context:
                report_lines.append(f"   上下文：{violation.context}")
            report_lines.append("")

        return "\n".join(report_lines)

    def clear_violations(self):
        """清除违规记录"""
        self.violations.clear()
