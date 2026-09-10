#!/usr/bin/env python3
"""Pack 内 JSON-stdio 入口，调用 Skill 共用 helper。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'scripts'))
from phase_evidence import check


def main():
    try:
        data = sys.stdin.buffer.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise ValueError('请求超出体积限制')
        request = json.loads(data)
        if not isinstance(request, dict):
            raise ValueError('请求必须是 JSON 对象')
        result = check(request)
    except (ValueError, TypeError, UnicodeError):
        result = {'verdict': 'error', 'facts': {}, 'findings': [{'code': 'invalid-json'}], 'evidence_refs': []}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
