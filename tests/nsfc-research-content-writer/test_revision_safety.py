#!/usr/bin/env python3
"""验证正文修订公开 CLI 与可注入的失败路径；所有夹具留在任务工作区。"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/nsfc-research-content-writer"
sys.path.insert(0, str(SKILL / "scripts"))
import revision as rev

TASK: Path
WORK: Path
RESULTS: list[dict] = []


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.case = Path(tempfile.mkdtemp(prefix=self._testMethodName + "-", dir=WORK))
        self.project = self.case / "project"
        self.project.mkdir()
        self.config = rev.load_config()
        self.originals = {}
        self.proposals = {}
        for role, rel in self.config["targets"].items():
            target = self.project / rel
            target.parent.mkdir(exist_ok=True)
            original = "\\subsection[短标题]{保留{嵌套}标题} 原有正文\\cite{known}。\n"
            target.write_text(original, encoding="utf-8")
            self.originals[role] = original.encode()
            proposal = self.case / (role + ".tex")
            proposal.write_text(original.replace("原有正文", "澄清后的正文"), encoding="utf-8")
            self.proposals[role] = proposal
        (self.project / "references").mkdir()
        (self.project / "references/test.bib").write_text("@article{known, title={Example}}\n", encoding="utf-8")
        (self.project / "main.tex").write_text("不得修改", encoding="utf-8")
        self.manifest = self.case / "proposals.json"
        self.write_manifest(list(rev.ROLES))

    def tearDown(self):
        RESULTS.append({"check": self._testMethodName})

    def write_manifest(self, roles):
        self.manifest.write_text(json.dumps({"proposals": {r: str(self.proposals[r].relative_to(TASK))
                                                          for r in roles}}), encoding="utf-8")

    def entries(self, roles=None, **kwargs):
        roles = roles or list(rev.ROLES)
        return rev.prepare(self.project, TASK, self.manifest, roles, self.config, **kwargs)[0]

    def assert_originals(self):
        for role, rel in self.config["targets"].items():
            self.assertEqual((self.project / rel).read_bytes(), self.originals[role])
        self.assertEqual((self.project / "main.tex").read_text(), "不得修改")

    def cli(self, *args, expected=0, script="run.py", skill=SKILL):
        result = subprocess.run([sys.executable, str(skill / "scripts" / script), *map(str, args)],
                                cwd=self.case, text=True, capture_output=True, timeout=30,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        log = result.stdout + result.stderr
        (self.case / f"command-{len(list(self.case.glob('command-*')))}.txt").write_text(
            log.replace(str(ROOT), "<repo>"), encoding="utf-8")
        self.assertEqual(result.returncode, expected, log)
        return log

    def revise_cli(self, mode="preview", roles=rev.ROLES, expected=0):
        argv = ["revise", "--project-root", self.project, "--task-root", TASK,
                "--proposal-manifest", self.manifest, "--output-mode", mode]
        for role in roles:
            argv.extend(["--role", role])
        return self.cli(*argv, expected=expected)

    def test_preview_readonly_and_same_line_body(self):
        before = set(TASK.rglob("record.json"))
        out = self.revise_cli()
        self.assertIn("澄清后的正文", out)
        self.assertIn('"status": "preview"', out)
        self.assertEqual(set(TASK.rglob("record.json")), before)
        self.assert_originals()

    def test_apply_diff_restore_and_undo_restore(self):
        out = self.revise_cli("apply")
        self.assertIn('"status": "applied"', out)
        result = json.loads(out[out.index('{\n  "status":'):])
        backup = TASK / result["backup_dir"]
        for role, rel in self.config["targets"].items():
            self.assertEqual((self.project / rel).read_bytes(), self.proposals[role].read_bytes())
        self.assertIn("澄清后的正文", self.cli("diff", "--project-root", self.project, "--task-root", TASK, "--backup-dir", backup))
        restored = json.loads(self.cli("restore", "--project-root", self.project,
                                      "--task-root", TASK, "--backup-dir", backup))
        self.assert_originals()
        self.assertEqual(restored["status"], "applied")
        rev.restore(self.project, TASK, restored["backup_dir"], self.config)
        for role, rel in self.config["targets"].items():
            self.assertEqual((self.project / rel).read_bytes(), self.proposals[role].read_bytes())

    def test_noop_does_not_replace_or_backup(self):
        for role in rev.ROLES:
            self.proposals[role].write_bytes(self.originals[role])
        entries = self.entries()
        snapshots = [rev.fingerprint(e["path"]) for e in entries]
        with patch.object(rev, "atomic_write", side_effect=AssertionError("不得替换")):
            self.assertEqual(rev.apply_entries(self.project, TASK, entries)["status"], "unchanged")
        self.assertEqual(snapshots, [rev.fingerprint(e["path"]) for e in entries])

    def test_single_role_other_targets_missing(self):
        self.write_manifest(["innovation_tex"])
        for role in ("research_content_tex", "yearly_plan_tex"):
            (self.project / self.config["targets"][role]).unlink()
        self.revise_cli("apply", roles=["innovation_tex"])
        for role in ("research_content_tex", "yearly_plan_tex"):
            self.assertFalse((self.project / self.config["targets"][role]).exists())

    def test_missing_required_target_does_not_create(self):
        path = self.project / self.config["targets"]["innovation_tex"]
        path.unlink()
        self.revise_cli("apply", expected=2)
        self.assertFalse(path.exists())
        for role in ("research_content_tex", "yearly_plan_tex"):
            self.assertEqual((self.project / self.config["targets"][role]).read_bytes(), self.originals[role])

    def test_one_bad_citation_rejects_whole_set(self):
        p = self.proposals["yearly_plan_tex"]
        p.write_text(p.read_text().replace("known", "missing"), encoding="utf-8")
        self.revise_cli("apply", expected=2)
        self.assert_originals()

    def test_heading_change_rejected_and_explicit_override(self):
        p = self.proposals["innovation_tex"]
        p.write_text(p.read_text().replace("保留", "变更"), encoding="utf-8")
        self.revise_cli("apply", expected=2)
        self.assert_originals()
        self.assertEqual(len(self.entries(allow_structure=True)), 3)

    def test_structure_optional_star_environment_and_label(self):
        original = "\\subsection*[短]{长{嵌套}题} 同行正文\n\\begin{quote}内容\\label{a}\\end{quote}"
        self.assertEqual(rev.structure(original), rev.structure(original.replace("同行正文", "修改正文")))
        self.assertEqual(rev.structure(r"\subsection{标题}{原有正文}"),
                         rev.structure(r"\subsection{标题}{修改后的正文}"))
        for updated in (original.replace("短", "另"), original.replace("label{a}", "label{b}"),
                        original.replace("begin{quote}", "begin{center}"), original.replace("subsection*", "section*")):
            self.assertNotEqual(rev.structure(original), rev.structure(updated))
        with self.assertRaises(rev.RevisionError):
            rev.structure("\\subsection{未闭合")

    def test_comments_and_escaped_percent(self):
        report = rev.content_report("实际正文 % \\cite{missing}\n", {"known"}, self.config)
        self.assertFalse(report["errors"])
        self.assertNotIn("missing", rev.citations("% \\cite{missing}"))
        self.assertEqual(rev.citations(r"20\%\parencite[见][第2页]{known}"), {"known"})

    def test_multicites_and_unbraced_macros(self):
        self.assertEqual(rev.citations(r"\parencites[见]{known}[第2页]{missing}"), {"known", "missing"})
        for before, after in ((r"\def\foo#1{before}", r"\def\foo#1{after}"),
                              (r"\newcommand\foo{before}", r"\newcommand\bar{before}")):
            self.assertNotEqual(rev.structure(before), rev.structure(after))

    def test_empty_proposal_rejected(self):
        self.proposals["innovation_tex"].write_text("% 只有注释\n", encoding="utf-8")
        self.revise_cli("apply", expected=2)
        self.assert_originals()

    def test_unauthorized_extra_manifest_role(self):
        self.revise_cli("apply", roles=["innovation_tex"], expected=2)
        self.assert_originals()

    def test_unknown_role_and_forbidden_targets(self):
        for rel in ("main.tex", "extraTex/@config.tex", "theme.sty", "nested/a.cls", "../outside.tex"):
            cfg = copy.deepcopy(self.config)
            cfg["targets"]["innovation_tex"] = rel
            cfg["guardrails"]["allowed_write_files"].append(rel)
            with self.assertRaises(rev.RevisionError):
                rev.target_path(self.project, "innovation_tex", cfg)
        with self.assertRaises(rev.RevisionError):
            rev.target_path(self.project, "main", self.config)

    def test_proposal_escape_and_traversal(self):
        for value in (str(ROOT / "CHANGELOG.md"), "../CHANGELOG.md"):
            self.manifest.write_text(json.dumps({"proposals": {"innovation_tex": value}}), encoding="utf-8")
            self.revise_cli("apply", roles=["innovation_tex"], expected=2)
            self.assert_originals()

    def test_symlink_target_and_proposal(self):
        path = self.project / self.config["targets"]["innovation_tex"]
        path.unlink()
        path.symlink_to(self.project / "main.tex")
        self.revise_cli("apply", expected=2)
        self.assertEqual((self.project / "main.tex").read_text(), "不得修改")
        path.unlink()
        path.write_bytes(self.originals["innovation_tex"])
        p = self.proposals["innovation_tex"]
        p.unlink()
        p.symlink_to(self.project / "main.tex")
        self.revise_cli("apply", expected=2)

    def test_symlink_parent_escape(self):
        folder = self.case / "outside"
        (self.project / "extraTex").rename(folder)
        (self.project / "extraTex").symlink_to(folder, target_is_directory=True)
        self.revise_cli("apply", expected=2)
        self.assertEqual((folder / "2.1.研究内容.tex").read_bytes(), self.originals["research_content_tex"])

    def test_backup_failure_does_not_write(self):
        entries = self.entries()
        real = Path.open
        def fail(path, *args, **kwargs):
            if path.parent.name == "before":
                raise OSError("注入备份失败")
            return real(path, *args, **kwargs)
        with patch.object(Path, "open", fail), self.assertRaises(OSError):
            rev.apply_entries(self.project, TASK, entries)
        self.assert_originals()

    def test_second_replacement_failure_restores_first(self):
        entries = self.entries()
        real = rev.atomic_write
        def fail(path, data, mode):
            if path == entries[1]["path"] and data == entries[1]["after"]:
                raise OSError("注入第二文件替换失败")
            return real(path, data, mode)
        with patch.object(rev, "atomic_write", fail), self.assertRaisesRegex(rev.RevisionError, "已恢复"):
            rev.apply_entries(self.project, TASK, entries)
        self.assert_originals()

    def test_precheck_drift_preserves_external_edit(self):
        entries = self.entries()
        entries[0]["path"].write_bytes(b"external change")
        with self.assertRaises(rev.RevisionError):
            rev.apply_entries(self.project, TASK, entries)
        self.assertEqual(entries[0]["path"].read_bytes(), b"external change")
        self.assertEqual(entries[1]["path"].read_bytes(), entries[1]["before"])

    def test_drift_after_backup_before_replacement(self):
        entries = self.entries()
        real = rev.save_record
        def drift(directory, record):
            real(directory, record)
            if record["status"] == "prepared":
                entries[0]["path"].write_bytes(b"external change")
        with patch.object(rev, "save_record", drift), self.assertRaises(rev.RevisionError):
            rev.apply_entries(self.project, TASK, entries)
        self.assertEqual(entries[0]["path"].read_bytes(), b"external change")

    def test_rollback_conflict_preserves_new_external_version(self):
        entries = self.entries()
        real = rev.atomic_write
        def fail(path, data, mode):
            if path == entries[1]["path"] and data == entries[1]["after"]:
                entries[0]["path"].write_bytes(b"external change")
                raise OSError("写入中途外部变化")
            return real(path, data, mode)
        with patch.object(rev, "atomic_write", fail), self.assertRaisesRegex(rev.RevisionError, "恢复受阻"):
            rev.apply_entries(self.project, TASK, entries)
        self.assertEqual(entries[0]["path"].read_bytes(), b"external change")

    def test_restore_conflict_rejects_entire_set(self):
        entries = self.entries()
        backup = rev.apply_entries(self.project, TASK, entries)["backup_dir"]
        entries[-1]["path"].write_bytes(b"external change")
        with self.assertRaisesRegex(rev.RevisionError, "恢复冲突"):
            rev.restore(self.project, TASK, backup, self.config)
        self.assertEqual(entries[0]["path"].read_bytes(), entries[0]["after"])

    def test_restore_mixed_interrupted_set(self):
        entries = self.entries()
        backup = rev.apply_entries(self.project, TASK, entries)["backup_dir"]
        entries[-1]["path"].write_bytes(entries[-1]["before"])
        rev.restore(self.project, TASK, backup, self.config)
        self.assert_originals()

    def test_corrupt_backup_and_forged_target_rejected(self):
        entries = self.entries()
        backup = TASK / rev.apply_entries(self.project, TASK, entries)["backup_dir"]
        path = backup / "before/research_content_tex.tex"
        saved = path.read_bytes()
        path.write_bytes(b"corrupt")
        with self.assertRaisesRegex(rev.RevisionError, "损坏"):
            rev.restore(self.project, TASK, backup, self.config)
        path.write_bytes(saved)
        rec = json.loads((backup / "record.json").read_text())
        rec["files"][0]["target"] = "main.tex"
        (backup / "record.json").write_text(json.dumps(rec), encoding="utf-8")
        with self.assertRaises(rev.RevisionError):
            rev.restore(self.project, TASK, backup, self.config)

    def test_restore_wrong_project_or_directory(self):
        entries = self.entries()
        backup = rev.apply_entries(self.project, TASK, entries)["backup_dir"]
        other = self.case / "other"
        shutil.copytree(self.project, other)
        with self.assertRaisesRegex(rev.RevisionError, "project_root"):
            rev.restore(other, TASK, backup, self.config)
        with self.assertRaises(rev.RevisionError):
            rev.restore(self.project, TASK, ROOT, self.config)

    def test_legacy_commands_no_s_identifiers(self):
        out = self.cli("--project-root", self.project, script="check_project_outputs.py")
        self.assertIn("已停用", out)
        self.cli("--project-root", self.project, "--no-content-check", "--no-risk-scan", script="run_checks.py")
        self.cli(script="validate_skill.py")

    def test_risk_scan_advisory_and_explicit_strict(self):
        path = self.project / self.config["targets"]["innovation_tex"]
        path.write_text(path.read_text() + "首次出现定义。", encoding="utf-8")
        self.cli("--project-root", self.project, script="check_project_outputs.py")
        self.cli("--project-root", self.project, "--fail-on-risk-phrases", script="check_project_outputs.py", expected=2)
        self.cli("--project-root", self.project, "--fail-on-risk-phrases", "--no-risk-scan", script="check_project_outputs.py")

    def test_test_session_explicit_workspace(self):
        test_id = "v202611" + str(uuid.uuid4().int % 1000000).zfill(6)
        self.cli("--task-root", TASK, "--id", test_id, "--kind", "a", "--create-plan", script="create_test_session.py")
        self.cli("--task-root", TASK, "--id", test_id, "--kind", "a", script="create_test_session.py", expected=2)
        self.cli("--id", "v202611011301", script="create_test_session.py", expected=2)
        self.assertFalse((SKILL / "plans").exists())
        self.assertFalse((SKILL / "tests").exists())

    def test_standalone_copy_and_arbitrary_cwd(self):
        installed = self.case / "installed-skill"
        shutil.copytree(SKILL, installed)
        self.cli(script="validate_skill.py", skill=installed)
        self.cli("--project-root", self.project, script="check_project_outputs.py", skill=installed)
        self.cli("revise", "--project-root", self.project, "--task-root", TASK,
                 "--proposal-manifest", self.manifest, "--role", "research_content_tex", "--role", "innovation_tex",
                 "--role", "yearly_plan_tex", "--output-mode", "preview", skill=installed)
        self.assertFalse(any(installed.rglob("__pycache__")))


def main():
    global TASK, WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-root", required=True, type=Path)
    args = parser.parse_args()
    TASK = rev.task_path(args.task_root)
    TASK.relative_to(ROOT / ".bensz-api")
    parent = TASK / "skill-creator/output"
    parent.mkdir(parents=True, exist_ok=True)
    WORK = Path(tempfile.mkdtemp(prefix="revision-safety-", dir=parent))
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SafetyTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {"run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
               "checks": RESULTS, "workspace": str(WORK.relative_to(ROOT))}
    (WORK / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
