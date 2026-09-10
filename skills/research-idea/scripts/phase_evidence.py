"""阶段快照的机械边界；科学充分性由 Pack 的 Agent 组件判断。"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from init_workspace import load_config
from validate_report import validate_report

SKILL_ROOT = Path(__file__).resolve().parent.parent


def digest(data: bytes) -> str:
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def safe_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('path 必须是非空 POSIX 相对路径')
    path = Path(value)
    if path.is_absolute() or any(p in {'.', '..'} for p in value.split('/')):
        raise ValueError('拒绝绝对路径和路径穿越')
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('拒绝符号链接路径')
    current.resolve().relative_to(root.resolve())
    return current


def read_bytes(path: Path, limit: int) -> bytes:
    if not path.is_file():
        raise ValueError('证据文件不存在或不是普通文件')
    with path.open('rb') as handle:
        data = handle.read(limit + 1)
    if not data.strip() or len(data) > limit:
        raise ValueError('证据文件为空或超出体积限制')
    return data


def snapshot(root: Path, items: list) -> list[dict]:
    limits = load_config()['control']['limits']
    if not isinstance(items, list) or not 1 <= len(items) <= limits['max_evidence']:
        raise ValueError('证据必须是非空且限量的列表')
    output, refs = [], set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('证据条目必须是对象')
        ref = item.get('ref')
        if not isinstance(ref, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', ref) or ref in refs:
            raise ValueError('证据 ref 必须唯一且仅包含字母、数字、下划线、连字符')
        refs.add(ref)
        for key in ('role', 'source_type', 'summary'):
            if not isinstance(item.get(key), str) or not item[key].strip() or len(item[key]) > 1000:
                raise ValueError('证据 role/source_type/summary 必须是有限非空文本')
        path = safe_path(root, item.get('path'))
        actual_hash = digest(read_bytes(path, limits['max_file_bytes']))
        if item.get('content_hash') and item['content_hash'] != actual_hash:
            raise ValueError('证据内容已变化，必须创建新 attempt')
        row = {k: item[k] for k in ('ref', 'role', 'path', 'source_type', 'summary')}
        row['content_hash'] = actual_hash
        for key in ('round', 'reviewer'):
            if key in item:
                if key == 'round' and (type(item[key]) is not int or item[key] < 1):
                    raise ValueError('审查 round 必须是正整数')
                if key == 'reviewer' and (not isinstance(item[key], str) or not item[key].strip() or len(item[key]) > 100):
                    raise ValueError('reviewer 必须是有限非空标识')
                row[key] = item[key]
        output.append(row)
    return output


def check(request: dict) -> dict:
    """只检查可机械验证的事实；任何错误都不能冒充 pass。"""
    try:
        subject, context = request['subject'], request['context']
        root = Path(context['project_root']).resolve()
        evidence = snapshot(root, request['evidence'])
        config = load_config()
        target = subject['target']
        roles = config['control']['required_roles'].get(target)
        if roles is None:
            raise ValueError('未知验证目标阶段')
        if not set(roles).issubset({e['role'] for e in evidence}):
            raise ValueError('缺少当前阶段必需的证据角色')
        if target.endswith('.reporting'):
            rounds, agents = context['rounds'], context['agents']
            for number in range(1, rounds + 1):
                reviews = [e for e in evidence if e['role'] == 'review' and e.get('round') == number]
                reviewers = {e.get('reviewer') for e in reviews}
                if None in reviewers or any(not isinstance(r, str) or not r for r in reviewers):
                    raise ValueError('独立审查必须标明 reviewer')
                if len(reviewers) < agents or len({e['content_hash'] for e in reviews}) < agents:
                    raise ValueError('独立审查轮次或不同结果数量不足')
        if target.endswith('.completed'):
            reports = [e for e in evidence if e['role'] == 'report']
            if len(reports) != 1:
                raise ValueError('完成阶段必须且只能验证一个最终报告')
            result = validate_report(safe_path(root, reports[0]['path']), allow_custom_name=context['allow_custom_name'], project_root=root)
            if not result['passed']:
                return {'verdict': 'fail', 'findings': [{'code': 'report-structure', 'message': e} for e in result['errors']], 'facts': {}, 'evidence_refs': [e['ref'] for e in evidence]}
        return {'verdict': 'pass', 'facts': {'evidence_count': len(evidence), 'target': target}, 'evidence_refs': [e['ref'] for e in evidence]}
    except (KeyError, ValueError, TypeError, OSError, SystemExit) as exc:
        return {'verdict': 'fail', 'findings': [{'code': 'invalid-evidence', 'message': str(exc)}], 'facts': {}, 'evidence_refs': []}
