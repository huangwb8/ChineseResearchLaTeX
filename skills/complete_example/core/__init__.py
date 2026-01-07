"""
complete_example skill - 核心模块
AI 增强版 LaTeX 示例智能生成器
"""

__version__ = "1.0.0"

from .resource_scanner import ResourceScanner, ResourceInfo, ResourceReport
from .format_guard import FormatGuard, ProtectedZone, FormatProtectionError
from .semantic_analyzer import SemanticAnalyzer, SectionTheme, ResourceRelevance
from .ai_content_generator import AIContentGenerator
from .skill_controller import CompleteExampleSkill

__all__ = [
    "ResourceScanner",
    "ResourceInfo",
    "ResourceReport",
    "FormatGuard",
    "ProtectedZone",
    "FormatProtectionError",
    "SemanticAnalyzer",
    "SectionTheme",
    "ResourceRelevance",
    "AIContentGenerator",
    "CompleteExampleSkill",
]
