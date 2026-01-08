"""transfer_old_latex_to_new core."""

# 新增工具模块（v1.3.0）
from .cache_manager import CacheManager
from .config_utils import (
    ConfigAccessor,
    ConfigDefaults,
    ThresholdDefaults,
    apply_profile,
    get_config_accessor,
)
from .json_utils import JsonParser, parse_json, parse_json_array, parse_batch_json
from .progress_utils import ProgressReporter, TaskGroup, iterate_with_progress, progress, task_group
from .prompt_templates import (
    MAPPING_JUDGE_TEMPLATE,
    OPTIMIZE_ANALYZE_TEMPLATE,
    OPTIMIZE_TYPE_PROMPTS,
    WORD_COUNT_COMPRESS_TEMPLATE,
    WORD_COUNT_EXPAND_TEMPLATE,
)

__all__ = [
    # 工具模块
    "CacheManager",
    "ConfigAccessor",
    "ConfigDefaults",
    "ThresholdDefaults",
    "JsonParser",
    "ProgressReporter",
    "TaskGroup",
    # 便捷函数
    "apply_profile",
    "get_config_accessor",
    "parse_json",
    "parse_json_array",
    "parse_batch_json",
    "iterate_with_progress",
    "progress",
    "task_group",
    # 提示词模板
    "MAPPING_JUDGE_TEMPLATE",
    "OPTIMIZE_ANALYZE_TEMPLATE",
    "OPTIMIZE_TYPE_PROMPTS",
    "WORD_COUNT_COMPRESS_TEMPLATE",
    "WORD_COUNT_EXPAND_TEMPLATE",
]


