"""兼容旧查询模块入口；新消费者应从 rls_contract 导入。"""
from rls_contract import (
    CONTRACT_VERSION,
    QueryInputError,
    QueryPlan,
    legacy_output_stems,
    load_query_plan,
    normalize_output_stem,
    normalize_query_payload,
    sha256_file,
)

__all__ = [
    "CONTRACT_VERSION", "QueryInputError", "QueryPlan", "legacy_output_stems",
    "load_query_plan", "normalize_output_stem", "normalize_query_payload", "sha256_file",
]
