#!/usr/bin/env python3
"""research-idea 的本地 Kernel 宿主：快照、验证回传与领域阶段重放。"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import math
from pathlib import Path
import sys
import uuid

from init_workspace import load_config
from phase_evidence import digest, safe_path, read_bytes, snapshot

SKILL_ROOT = Path(__file__).resolve().parent.parent
VERIFIER = 'bensz.research.stage-readiness'
PREFIX = 'bensz.research-ideation.'


def kernel_api():
    try:
        from bensz_skill_kernel import __version__
        from bensz_skill_kernel.runtime import EventLog
        from bensz_skill_kernel.states import SkillStateDeclaration, StateMachine
        from bensz_skill_kernel.verifiers import FilesystemVerifierRegistry
    except ImportError as exc:
        raise ValueError('需要 Python 3.11+ 和 config.yaml 声明的 bensz-skill-kernel；当前环境不兼容') from exc
    expected = load_config()['runtime']['kernel']['version']
    if __version__ != expected:
        raise ValueError(f'Kernel 版本不匹配：需要 {expected}，当前 {__version__}；请在隔离环境安装匹配版本')
    return EventLog, SkillStateDeclaration, StateMachine, FilesystemVerifierRegistry


def save_new(path: Path, value: dict):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


class Runtime:
    def __init__(self, project: Path, task: str):
        self.project = project.resolve()
        self.task = safe_path(self.project, task)
        if len(Path(task).parts) != 2 or Path(task).parts[0] != '.bensz-api' or not self.task.name.startswith('task-'):
            raise ValueError('task-root 必须为项目内 .bensz-api/task-*，复用已声明任务目录')
        self.root = safe_path(self.project, f'{task}/research-idea')
        self.logdir = safe_path(self.project, f'{task}/research-idea/log')
        self.output = safe_path(self.project, f'{task}/research-idea/output')
        self.config = load_config()
        EventLog, Declaration, self.Machine, Registry = kernel_api()
        self.declaration = Declaration.from_skill_root(SKILL_ROOT)
        self.registry = self.declaration.registry()
        self.verifiers = Registry(SKILL_ROOT / 'references/verifiers')
        self.log = EventLog(safe_path(self.project, f'{task}/research-idea/log/events.ndjson'), contract={'project_root': str(self.project)})
        # 固定整个发布资产快照，源码/配置变化要求新 run，不重写历史。
        files = [SKILL_ROOT / 'config.yaml', *sorted((SKILL_ROOT / 'references/states').rglob('*')), *sorted((SKILL_ROOT / 'references/verifiers').rglob('*')), *sorted((SKILL_ROOT / 'scripts').glob('*.py'))]
        self.asset_hash = digest(json.dumps([(str(p.relative_to(SKILL_ROOT)), digest(p.read_bytes())) for p in files if p.is_file() and '__pycache__' not in p.parts], sort_keys=True).encode())

    @contextmanager
    def locked(self):
        # 单一执行主体跨进程串行化；OS 锁在异常退出时自动释放。
        import fcntl
        self.logdir.mkdir(parents=True, exist_ok=True)
        path = safe_path(self.project, str((self.logdir / 'runtime.lock').relative_to(self.project)))
        with path.open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def status(self):
        events = self.log.read()
        if not events or events[0].event_type != 'idea.initialized':
            raise ValueError('尚未初始化；先运行 init')
        initial = events[0].payload
        if initial['asset_hash'] != self.asset_hash:
            raise ValueError('Skill 资产已改变；不能以新契约续写旧运行，请建立新任务')
        machine = self.Machine(self.registry, self.declaration.initial_state)
        pending, cancelled, checkpoints = None, False, {}
        for event in events[1:]:
            if event.run_id != events[0].run_id:
                raise ValueError('事件 run_id 不匹配')
            if event.event_type == 'idea.attempt':
                if cancelled or machine.current.endswith('.completed'):
                    raise ValueError('终止后存在非法 attempt')
                pending = event.payload
            elif event.event_type == 'idea.moved':
                if cancelled or event.payload['source'] != machine.current:
                    raise ValueError('状态事件源不匹配')
                if event.payload['mode'] == 'advance':
                    gates = [e for e in events if e.seq < event.seq and e.event_type == 'verification.gate' and e.event_id == event.payload['gate_event_id'] and e.attempt_id == event.attempt_id]
                    if not pending or pending['attempt_id'] != event.attempt_id or pending['target'] != event.payload['target'] or not gates or gates[0].payload['decision'] != 'allow':
                        raise ValueError('转移缺少当前 attempt 的通过 Gate')
                    checkpoints[machine.current] = event.payload['evidence']
                elif event.payload['mode'] != 'rework':
                    raise ValueError('未知转移模式')
                else:
                    order = list(self.declaration.states)
                    if order.index(event.payload['target']) >= order.index(machine.current):
                        raise ValueError('回退事件不能前进')
                    checkpoints = {k: v for k, v in checkpoints.items() if order.index(k) < order.index(event.payload['target'])}
                machine.transition(event.payload['target'])
                pending = None
            elif event.event_type == 'idea.cancelled':
                cancelled, pending = True, None
        return {'run_id': events[0].run_id, 'state': machine.current, 'pending': pending, 'cancelled': cancelled, 'settings': initial['settings'], 'checkpoints': checkpoints, 'event_count': len(events)}

    def init(self, rounds=None, agents=None, allow_custom_name=False):
        if self.log.path.exists():
            raise ValueError('运行已存在；用 status 恢复，不重新初始化')
        for folder in ('input', 'output', 'log'):
            safe_path(self.project, str((self.root / folder).relative_to(self.project))).mkdir(parents=True, exist_ok=True)
        settings = {'rounds': rounds if rounds is not None else self.config['iteration']['default_rounds'], 'agents': agents if agents is not None else self.config['iteration']['default_independent_agents'], 'allow_custom_name': allow_custom_name}
        if any(type(settings[k]) is not int or not 1 <= settings[k] <= 100 for k in ('rounds', 'agents')):
            raise ValueError('rounds/agents 必须为 1..100 的整数')
        self.log.append('idea.initialized', payload={'asset_hash': self.asset_hash, 'settings': settings}, run_id=uuid.uuid4().hex)
        return self.status()

    def active(self):
        status = self.status()
        if status['cancelled'] or status['state'] == PREFIX + 'completed':
            raise ValueError('运行已终止，不能继续修改阶段')
        return status

    def canonical(self, value):
        result = self.registry.resolve(value if '.' in value else PREFIX + value).id
        if result not in self.declaration.states:
            raise ValueError('目标不属于本 Skill 状态集合')
        return result

    def evidence_file(self, value):
        data = read_bytes(safe_path(self.project, value), self.config['control']['limits']['max_request_bytes'])
        return json.loads(data)

    def request(self, status, target, evidence):
        return {'subject': {'source': status['state'], 'target': target}, 'context': {**status['settings'], 'checkpoints': status['checkpoints']}, 'evidence': snapshot(self.project, evidence)}

    def execute(self, request, status, attempt, submissions=()):
        # 内容每次重算，禁止旧哈希/旧回传用于修改后的证据。
        for rows in status['checkpoints'].values():
            snapshot(self.project, rows)
        snapshot(self.project, request['evidence'])
        context = {**request['context'], 'project_root': str(self.project)}
        execution = self.verifiers.run_contract(VERIFIER, {**request, 'context': context}, run_id=status['run_id'], attempt_id=attempt, submissions=submissions)
        _, gate = self.log.record_verification(execution.to_event_payload(), execution.gate.to_dict(), run_id=status['run_id'], attempt_id=attempt, requirements=self.declaration.verifier_requirements())
        return execution, gate

    @staticmethod
    def receipt(execution, gate):
        # handoff 仅返回绑定与必要事实，契约由宿主直接读发布文件，不复制到审计日志。
        handoffs = []
        for handoff in execution.report.handoffs:
            item = handoff.to_audit_dict()
            item['subject'] = dict(handoff.subject)
            item['context'] = {k: v for k, v in handoff.context.items() if k != 'project_root'}
            item['evidence'] = list(handoff.evidence)
            handoffs.append(item)
        return {'verdict': execution.aggregate.verdict, 'gate': gate.payload['decision'], 'handoffs': handoffs}

    def prepare(self, target, evidence):
        status = self.active()
        target = self.canonical(target)
        expected = self.config['control']['forward'].get(status['state'])
        if target != expected:
            raise ValueError('prepare 只允许下一前向阶段；回退使用 rework')
        machine = self.Machine(self.registry, status['state'])
        machine.transition(target)
        request = self.request(status, target, evidence)
        for rows in status['checkpoints'].values():
            snapshot(self.project, rows)
        attempt = uuid.uuid4().hex
        relative = str((self.output / f'attempt-{attempt}.json').relative_to(self.project))
        save_new(safe_path(self.project, relative), request)
        self.log.append('idea.attempt', payload={'attempt_id': attempt, 'target': target, 'request_path': relative, 'request_hash': digest(json.dumps(request, sort_keys=True).encode())}, run_id=status['run_id'], attempt_id=attempt)
        execution, gate = self.execute(request, status, attempt)
        return {'attempt_id': attempt, **self.receipt(execution, gate)}

    def submit(self, submission):
        status = self.active()
        pending = status['pending']
        if not pending:
            raise ValueError('没有待处理 attempt；先 prepare')
        if not isinstance(submission, dict):
            raise ValueError('回传必须是 JSON 对象')
        facts = submission.get('facts', {})
        if not isinstance(facts, dict) or not isinstance(facts.get('summary'), str) or not facts['summary'].strip() or not isinstance(facts.get('uncertainties'), list):
            raise ValueError('回传必须包含 facts.summary/confidence/uncertainties')
        confidence = facts.get('confidence')
        if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError('confidence 必须在 0..1 之间，但不作为 pass 阈值')
        if not submission.get('evidence_refs'):
            raise ValueError('语义回传必须引用实际证据')
        if submission.get('verdict') == 'pass' and facts['uncertainties']:
            raise ValueError('尚有未解决不确定性时不能回传 pass')
        request = self.evidence_file(pending['request_path'])
        if digest(json.dumps(request, sort_keys=True).encode()) != pending['request_hash']:
            raise ValueError('attempt 快照已改变')
        execution, gate = self.execute(request, status, pending['attempt_id'], (submission,))
        if gate.payload['decision'] == 'allow':
            self.log.append('idea.moved', payload={'source': status['state'], 'target': pending['target'], 'mode': 'advance', 'gate_event_id': gate.event_id, 'evidence': request['evidence']}, run_id=status['run_id'], attempt_id=pending['attempt_id'])
        return {**self.receipt(execution, gate), 'state': self.status()['state']}

    def rework(self, target, evidence):
        status = self.active()
        target = self.canonical(target)
        if target == self.config['control']['forward'].get(status['state']):
            raise ValueError('rework 不能绕过前向 Gate')
        self.Machine(self.registry, status['state']).transition(target)
        rows = snapshot(self.project, evidence)
        if not any(e['role'] == 'rework' for e in rows):
            raise ValueError('回退需要 role=rework 的原因与证据文件')
        self.log.append('idea.moved', payload={'source': status['state'], 'target': target, 'mode': 'rework', 'evidence': rows}, evidence_refs=[e['ref'] for e in rows], run_id=status['run_id'], attempt_id=uuid.uuid4().hex)
        return self.status()

    def cancel(self):
        status = self.active()
        self.log.append('idea.cancelled', payload={}, run_id=status['run_id'])
        return self.status()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path('.'))
    parser.add_argument('--task-root', required=True, help='项目内 .bensz-api/task-* 相对路径，必须复用本逻辑任务目录')
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init')
    init.add_argument('--rounds', type=int)
    init.add_argument('--agents', type=int)
    init.add_argument('--allow-custom-name', action='store_true')
    sub.add_parser('status')
    sub.add_parser('cancel')
    for name in ('prepare', 'rework'):
        command = sub.add_parser(name)
        command.add_argument('--target', required=True)
        command.add_argument('--evidence', required=True, help='项目内相对 JSON 路径，内容为证据列表')
    submit = sub.add_parser('submit')
    submit.add_argument('--result', required=True, help='绑定的 Agent 结果 JSON，相对项目路径')
    args = parser.parse_args()
    try:
        runtime = Runtime(args.project_root, args.task_root)
        with runtime.locked():
            if args.command == 'init':
                result = runtime.init(args.rounds, args.agents, args.allow_custom_name)
            elif args.command in ('status', 'cancel'):
                result = getattr(runtime, args.command)()
            elif args.command == 'submit':
                result = runtime.submit(runtime.evidence_file(args.result))
            else:
                result = getattr(runtime, args.command)(args.target, runtime.evidence_file(args.evidence))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get('gate', 'allow') == 'allow' else 2
    except Exception as exc:
        print(json.dumps({'status': 'error', 'summary': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(main())
