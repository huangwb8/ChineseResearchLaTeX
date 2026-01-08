#!/usr/bin/env python3
"""
config_loader.py - 统一配置加载器

P0-1: 统一配置管理 - 消除硬编码阈值，实现配置与代码分离

功能：
  - 加载 config.yaml 配置文件
  - 提供 API 配置、LaTeX 配置、Word 配置等
  - 支持环境变量覆盖

使用示例：
    from scripts.config_loader import load_config

    # 加载完整配置
    config = load_config()

    # 获取API配置
    api_timeout = config['api']['semantic_scholar']['timeout']
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


# 配置文件路径（相对于技能根目录）
_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
_cached_config: Optional[Dict] = None


def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    加载配置文件（带缓存）

    Args:
        force_reload: 强制重新加载，忽略缓存

    Returns:
        配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: 配置文件格式错误
    """
    global _cached_config

    if _cached_config is not None and not force_reload:
        return _cached_config

    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"配置文件不存在: {_CONFIG_PATH}\n"
            f"请确保 systematic-literature-review/config.yaml 存在"
        )

    with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 应用环境变量覆盖（可选）
    config = _apply_env_overrides(config)

    _cached_config = config
    return config


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    应用环境变量覆盖配置

    支持的环境变量：
      - SLR_API_TIMEOUT: API 超时时间（秒）
      - SLR_RATE_LIMIT: API 速率限制（每分钟请求数）
    """
    if 'SLR_API_TIMEOUT' in os.environ:
        timeout = int(os.environ['SLR_API_TIMEOUT'])
        api_cfg = config.setdefault('api', {})
        ss_cfg = api_cfg.setdefault('semantic_scholar', {})
        oa_cfg = api_cfg.setdefault('openalex', {})
        ss_cfg['timeout'] = timeout
        oa_cfg['timeout'] = timeout

    if 'SLR_RATE_LIMIT' in os.environ:
        rate_limit = int(os.environ['SLR_RATE_LIMIT'])
        api_cfg = config.setdefault('api', {})
        ss_cfg = api_cfg.setdefault('semantic_scholar', {})
        ss_cfg['rate_limit'] = rate_limit

    return config


def get_api_config(service: str, config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    获取特定 API 服务的配置

    Args:
        service: 服务名称（semantic_scholar/openalex）
        config: 配置字典（可选）

    Returns:
        API 配置字典
    """
    if config is None:
        config = load_config()
    return config.get('api', {}).get(service, {})


def get_latex_config(config: Optional[Dict] = None) -> Dict[str, Any]:
    """获取 LaTeX/PDF 生成配置"""
    if config is None:
        config = load_config()
    return config.get('latex', {})


def get_word_config(config: Optional[Dict] = None) -> Dict[str, Any]:
    """获取 Word 导出配置"""
    if config is None:
        config = load_config()
    return config.get('word', {})


def get_output_template(name: str, config: Optional[Dict] = None) -> str:
    """
    获取输出文件命名模板

    Args:
        name: 模板名称（review_markdown/review_pdf/review_word等）
        config: 配置字典（可选）

    Returns:
        文件命名模板字符串
    """
    if config is None:
        config = load_config()
    return config.get('output', {}).get(name, '')


def get_script_path(script_name: str, config: Optional[Dict] = None) -> Path:
    """
    获取脚本路径

    Args:
        script_name: 脚本名称（quality_assessment/keyword_expansion等）
        config: 配置字典（可选）

    Returns:
        脚本文件的完整路径
    """
    if config is None:
        config = load_config()

    script_rel_path = config.get('scripts', {}).get(script_name, '')
    return Path(__file__).parent.parent / script_rel_path


def get_predatory_journals(config: Optional[Dict] = None) -> list:
    """获取预警期刊黑名单"""
    if config is None:
        config = load_config()
    return config.get('predatory_journals', [])


def reload_config():
    """清除配置缓存，下次调用 load_config 时重新加载"""
    global _cached_config
    _cached_config = None


# ============================================================================
# 命令行接口（用于调试）
# ============================================================================

if __name__ == '__main__':
    import argparse
    import json

    parser = argparse.ArgumentParser(description='配置文件加载器')
    parser.add_argument('--all', '-a', action='store_true',
                        help='显示完整配置（JSON格式）')
    parser.add_argument('--reload', '-r', action='store_true',
                        help='强制重新加载配置')

    args = parser.parse_args()

    if args.reload:
        reload_config()
        print("✓ 配置已重新加载")

    if args.all:
        config = load_config(force_reload=args.reload)
        print(json.dumps(config, ensure_ascii=False, indent=2))
