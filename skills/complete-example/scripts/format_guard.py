"""
FormatGuard - 硬编码格式守护器
🔧 硬编码：严格保护格式设置不被修改
🔒 集成 SecurityManager 增强安全保护
"""

import hashlib
import re
import shutil
import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime


class FormatProtectionError(Exception):
    """格式保护异常"""
    pass


class CompilationError(Exception):
    """编译异常"""
    pass


# 导入安全管理器
try:
    from .security_manager import SecurityManager, SecurityError
    SECURITY_MANAGER_AVAILABLE = True
except ImportError:
    SECURITY_MANAGER_AVAILABLE = False


@dataclass
class ProtectedZone:
    """受保护的格式区域"""
    name: str           # 区域名称
    start: int          # 起始位置
    end: int            # 结束位置
    content: str        # 原始内容
    line_number: int    # 行号


class FormatGuard:
    """硬编码：严格的格式保护机制"""

    # 受保护的 LaTeX 命令（正则模式）
    PROTECTED_PATTERNS = [
        r'\\setlength\{[^}]+\}\{[^}]+\}',           # \setlength{\parindent}{2em}
        r'\\geometry\{[^}]+\}',                      # \geometry{left=3cm,...}
        r'\\definecolor\{[^}]+\}\{[^}]+\}\{[^}]+\}', # \definecolor{MsBlue}{RGB}{...}
        r'\\setCJKfamilyfont\{[^}]+\}(\[[^]]*\])?\{[^}]+\}',  # 字体设置
        r'\\setmainfont(\[[^]]*\])?\{[^}]+\}',       # 英文字体
        r'\\titleformat\{[^}]+\}\{[^}]*\}\{[^}]*\}\{[^}]*\}\{[^}]*\}\{[^}]*\}',  # 标题格式
        r'\\setlist\[[^]]+\]\{[^}]+\}',             # \setlist[enumerate]{...}
        r'\\newcommand\{[^}]+\}',                    # 自定义命令
        r'\\renewcommand\{[^}]+\}',                  # 重定义命令
    ]

    def __init__(
        self,
        project_path: Path,
        run_dir: Path = None,
        enable_security_manager: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Args:
            project_path: 项目根目录（被保护的项目，不写入任何文件）
            run_dir: 运行目录（备份和日志放在这里，隔离项目污染）
            enable_security_manager: 是否启用增强安全管理器
        """
        self.project_path = Path(project_path)
        self.run_dir = Path(run_dir) if run_dir else self.project_path
        self.config = config or {}

        fp_cfg = (self.config.get("format_protection") or {})
        self.protected_files = list(fp_cfg.get("protected_files") or ["extraTex/@config.tex", "main.tex"])
        self.compile_verify_cfg = (fp_cfg.get("compile_verify") or {})
        self.compile_verify_enabled = bool(self.compile_verify_cfg.get("enabled", True))
        self.compile_engine = str(self.compile_verify_cfg.get("engine", "xelatex"))
        self.compile_timeout_sec = int(self.compile_verify_cfg.get("timeout", 60))

        self.format_hashes = self._compute_format_hashes()

        # 🔒 集成安全管理器
        self.security_manager: Optional[SecurityManager] = None
        if enable_security_manager and SECURITY_MANAGER_AVAILABLE:
            self.security_manager = SecurityManager(
                project_path=self.project_path,
                hash_file=self.project_path / ".format_hashes.json",
                config=self.config,
            )
            # 初始化哈希（如果不存在）
            if not self.security_manager.hash_file.exists():
                self.security_manager.initialize_hashes()

    def _compute_format_hashes(self) -> Dict[str, str]:
        """计算关键格式文件的哈希值"""
        hashes = {}
        for file_path in self.protected_files:
            full_path = self.project_path / file_path
            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")
                # 提取格式定义行
                format_lines = self._extract_format_lines(content)
                hashes[file_path] = hashlib.sha256(
                    "".join(format_lines).encode()
                ).hexdigest()
        return hashes

    def _extract_format_lines(self, content: str) -> List[str]:
        """提取格式定义行"""
        lines = content.split("\n")
        format_lines = []

        for line in lines:
            # 检查是否包含受保护的命令
            for pattern in self.PROTECTED_PATTERNS:
                if re.search(pattern, line):
                    format_lines.append(line)
                    break

        return format_lines

    def extract_protected_zones(self, content: str) -> List[ProtectedZone]:
        """
        🔧 硬编码：使用正则提取保护区域

        Args:
            content: 文件内容

        Returns:
            List[ProtectedZone]: 保护区域列表
        """
        zones = []
        lines = content.split("\n")

        for line_no, line in enumerate(lines, 1):
            for pattern in self.PROTECTED_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    zones.append(ProtectedZone(
                        name="format_definition",
                        start=match.start(),
                        end=match.end(),
                        content=match.group(0),
                        line_number=line_no
                    ))

        return zones

    def validate_format_integrity(self) -> Dict[str, bool]:
        """
        🔧 硬编码：验证格式未被篡改

        Returns:
            Dict: {文件路径: 是否完整}
        """
        results = {}
        current_hashes = self._compute_format_hashes()

        for file_path, original_hash in self.format_hashes.items():
            current_hash = current_hashes.get(file_path)
            results[file_path] = (current_hash == original_hash)

        return results

    def safe_modify_file(
        self,
        file_path: Path,
        new_content: str,
        ai_explanation: str = None,
        auto_sanitize: bool = True,
        compile_verify: Optional[bool] = None,
    ) -> Optional[Path]:
        """
        🤝 协作点：AI 建议修改 + 硬编码安全检查
        🔒 集成安全管理器进行预检查

        Args:
            file_path: 要修改的文件路径
            new_content: 新内容
            ai_explanation: AI 对修改的解释
            auto_sanitize: 是否自动清理格式注入

        Returns:
            Optional[Path]: 备份文件路径；失败时抛异常

        Raises:
            FormatProtectionError: 格式保护失败
            CompilationError: 编译失败
            SecurityError: 安全检查失败（通过 SecurityManager）
        """
        file_path = Path(file_path)

        # 仅允许修改 project_path 内的文件，避免路径穿越/误写到仓库外。
        try:
            file_path.resolve().relative_to(self.project_path.resolve())
        except Exception:
            raise FormatProtectionError(f"拒绝修改项目目录之外的文件：{file_path}")

        # ========== 🔒 安全管理器预检查 ==========
        if self.security_manager:
            # 1. 系统文件黑名单 + 完整性校验
            self.security_manager.pre_edit_check(file_path)

            # 2. 格式注入检查 + 自动清理
            new_content = self.security_manager.pre_apply_check(
                file_path, new_content, auto_sanitize
            )

        # 检查是否为受保护文件（受 config.yaml 控制）
        try:
            relative_path = file_path.resolve().relative_to(self.project_path.resolve()).as_posix()
        except ValueError:
            relative_path = str(file_path)

        if relative_path in self.protected_files:
            raise FormatProtectionError(
                f"拒绝修改受保护文件：{relative_path}\n"
                f"AI 解释：{ai_explanation or '未提供'}"
            )

        # ========== 阶段 1：硬编码 - 备份 ==========
        # 🆕 备份到 .complete_example/<run_id>/backups/ 而非项目目录
        backup_dir = self.run_dir / "backups"
        backup_filename = f"{relative_path.replace('/', '_')}.backup"
        backup_path = backup_dir / backup_filename
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file_path, backup_path)

        # ========== 阶段 2：硬编码 - 检查格式区域 ==========
        old_content = file_path.read_text(encoding="utf-8")
        protected_zones = self.extract_protected_zones(old_content)

        for zone in protected_zones:
            if zone.content not in new_content:
                # 🧠 AI：尝试诊断
                diagnosis = self._ai_diagnose_format_loss(
                    zone, old_content, new_content
                )

                # 🧠 AI：尝试修复
                fixed_content = self._ai_attempt_fix(
                    new_content, zone, diagnosis
                )

                # 如果还是失败，回滚
                if zone.content not in fixed_content:
                    shutil.copy(backup_path, file_path)
                    raise FormatProtectionError(
                        f"格式保护失败，已回滚\n"
                        f"破坏区域：{zone.name} (第 {zone.line_number} 行)\n"
                        f"原内容：{zone.content}\n"
                        f"AI 诊断：{diagnosis}\n"
                        f"AI 解释：{ai_explanation or '未提供'}"
                    )
                else:
                    new_content = fixed_content

        # ========== 阶段 3：硬编码 - 应用修改 ==========
        file_path.write_text(new_content, encoding="utf-8")

        # ========== 阶段 4：硬编码 - 编译验证（可按批次外部统一执行） ==========
        do_compile = self.compile_verify_enabled if compile_verify is None else bool(compile_verify)
        if do_compile and not self.compile_verify_project():
            shutil.copy(backup_path, file_path)
            raise CompilationError(
                "编译失败，已回滚\n"
                f"修改的文件：{file_path}\n"
                f"AI 解释：{ai_explanation or '未提供'}"
            )

        # ========== 阶段 5：成功，记录 ==========
        self._log_modification(
            file_path, backup_path, ai_explanation
        )

        return backup_path

    def _ai_diagnose_format_loss(
        self,
        zone: ProtectedZone,
        old_content: str,
        new_content: str
    ) -> str:
        """🧠 AI：诊断格式丢失的原因"""
        # 简化版本：返回硬编码的诊断
        return f"格式定义 '{zone.content[:30]}...' 在新内容中未找到"

    def _ai_attempt_fix(
        self,
        new_content: str,
        zone: ProtectedZone,
        diagnosis: str
    ) -> str:
        """🧠 AI：尝试修复格式丢失"""
        # 简化版本：直接插入原格式
        # 实际版本可以让 AI 分析上下文并智能插入
        return new_content  # 不做修改，让外部处理

    def compile_verify_project(self) -> bool:
        """
        硬编码：项目级编译验证（尽量避免污染项目根目录）。

        说明：
        - 使用 `-output-directory` 将 aux/pdf 等产物写入本次 run_dir 的构建目录；
          项目根目录仍作为 cwd，保证相对路径（extraTex/、figures/、references/）可解析。
        - 按仓库约定执行 4 步：xelatex → bibtex → xelatex → xelatex（如检测到 bibtex 需求）。
        """
        if not self.compile_verify_enabled:
            return True

        project_root = self.project_path
        main_tex = project_root / "main.tex"
        if not main_tex.exists():
            return False

        build_dir = self.run_dir / "_latex_build"
        build_dir.mkdir(parents=True, exist_ok=True)

        log_file = self.run_dir / "logs" / "compile.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        def _append_log(title: str, result: subprocess.CompletedProcess[str]):
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n\n===== {title} =====\n")
                f.write(result.stdout or "")
                f.write("\n\n=== STDERR ===\n")
                f.write(result.stderr or "")

        def _run(cmd: List[str], title: str) -> bool:
            try:
                result = subprocess.run(
                    cmd,
                    cwd=project_root,
                    capture_output=True,
                    timeout=self.compile_timeout_sec,
                    text=True,
                )
                _append_log(title, result)
                return result.returncode == 0
            except subprocess.TimeoutExpired:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n\n===== {title} =====\n编译超时（{self.compile_timeout_sec}秒）\n")
                return False
            except Exception as e:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n\n===== {title} =====\n编译异常：{e}\n")
                return False

        # 清空旧日志，避免混淆
        log_file.write_text("", encoding="utf-8")

        engine = self.compile_engine
        # 1) xelatex
        if not _run([engine, "-interaction=nonstopmode", f"-output-directory={build_dir}", "main.tex"], f"{engine} #1"):
            return False

        # 2) bibtex（仅在 aux 声明了 bibdata 时运行）
        aux_file = build_dir / "main.aux"
        need_bibtex = False
        if aux_file.exists():
            try:
                aux_text = aux_file.read_text(encoding="utf-8", errors="ignore")
                need_bibtex = "\\bibdata" in aux_text
            except Exception:
                need_bibtex = False

        if need_bibtex:
            # bibtex 需要从项目根目录解析 references/*.bib 的相对路径：
            # 优先使用“相对路径”参数，避免 TeX 安全策略（openout_any）阻止写入绝对路径 *.blg/*.bbl。
            try:
                bibtex_target = (build_dir / "main").resolve().relative_to(project_root.resolve()).as_posix()
            except Exception:
                bibtex_target = None

            if bibtex_target:
                if not _run(["bibtex", bibtex_target], "bibtex"):
                    return False
            else:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write("\n\n===== bibtex =====\n跳过：build_dir 不在项目目录内，无法安全运行 bibtex。\n")

        # 3) xelatex
        if not _run([engine, "-interaction=nonstopmode", f"-output-directory={build_dir}", "main.tex"], f"{engine} #2"):
            return False

        # 4) xelatex
        if not _run([engine, "-interaction=nonstopmode", f"-output-directory={build_dir}", "main.tex"], f"{engine} #3"):
            return False

        return True

    def _log_modification(
        self,
        file_path: Path,
        backup_path: Path,
        ai_explanation: str
    ):
        """🆕 记录修改日志到 .complete_example/<run_id>/logs/"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "file": str(file_path),
            "backup": str(backup_path),
            "ai_explanation": ai_explanation or "未提供"
        }
        # 🆕 写入 .complete_example/<run_id>/logs/execution.log 而非项目目录
        log_file = self.run_dir / "logs" / "execution.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
