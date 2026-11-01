# nsfc-research-content-writer

[中文](README.md) · [English](README_EN.md) · [Execution guide](SKILL.md) · [Configuration](config.yaml)

Draft, restructure, review, or polish the research content, innovation, and annual plan sections of an NSFC proposal. The host reads project materials and edits the authorized sections, checking related sections without extending permission.

## Quick start

Point your Agent Skill host to this directory and specify the task:

```text
使用 nsfc-research-content-writer。
project_root: projects/NSFC_Young
只润色特色与创新，保留研究设计和其他章节。
output_mode: preview
从现有正文、立项依据和研究基础提取信息，缺口按影响处理。
```

For a complete draft or restructuring, authorize all three sections and provide available research materials. Review tasks only produce findings. No fixed intake form is required. `nsfc-justification-writer` handles the rationale and `nsfc-research-foundation-writer` handles the research foundation; both are read-only context here.

## Inputs and outputs

`project_root` is required. `output_mode` defaults to `apply`; `preview` shows draft text and a diff when available. These modes retain their existing meaning. Defaults are maintained in [config.yaml](config.yaml):

| Role | Target |
| --- | --- |
| `research_content_tex` | `extraTex/2.1.研究内容.tex` |
| `innovation_tex` | `extraTex/2.2.特色与创新.tex` |
| `yearly_plan_tex` | `extraTex/2.3.年度研究计划.tex` |

The defaults remain **3–4 subgoals, a three-year plan, and 12–15 research-content pages including figures**; use 1–3 innovation points. The previous 12000–15000 text-unit recommendation is auxiliary, not a page conversion. Without compilation, the output states that actual page count is unverified. Internal planning identifiers stay out of the final prose.

Deliver the requested sections and concise notes on research design and structure, academic expression, scientific ambiguity and evidence gaps, and author decisions. Applied revisions also include the actual diff, backup, and recovery instructions. A technical roadmap may be placed near the beginning of research content; this Skill does not generate figures.

## Safe application and preview

Scripts require **Python 3.11+ and PyYAML**. Replace `python3.11` with another compatible interpreter if needed. The host AI first prepares complete proposed files within the previously declared `.bensz-api/task-*` directory. Required target files must already exist in the template.

Save this JSON as `nsfc-research-content-writer/input/proposals.json` under the task root. Proposal paths are also relative to that root. Include only authorized roles:

```json
{"proposals": {"innovation_tex": "nsfc-research-content-writer/input/innovation.tex"}}
```

Call an installed copy or the repository script from any directory. Replace `/path/to/skill` with its location; the manifest and proposals must remain inside the task directory:

```bash
python3.11 /path/to/skill/scripts/run.py revise \
  --project-root /path/to/project --task-root /path/to/.bensz-api/task-YYYYMMDD-HHMM-topic \
  --proposal-manifest nsfc-research-content-writer/input/proposals.json \
  --role innovation_tex --output-mode preview
```

`preview` changes no target and creates no backup. Use `--output-mode apply` once writing is authorized; omitting the option uses the configured default. A complete revision requires three `--role` arguments and an identical manifest role set. Existing headings, hierarchy, labels, and resource commands are protected by default. Use `--allow-structure-change` only with explicit structural-edit authorization; it does not broaden the target allowlist. `main.tex`, `extraTex/@config.tex`, and all `.cls/.sty` files are forbidden targets.

All targets are checked before any replacement. One failure prevents the entire set from being written. All changed originals are backed up before checking for concurrent edits and replacing each file. Identical proposals do not replace files. Caught failures trigger recovery of replaced files. Process interruption may leave a partial update: this is not a filesystem-wide atomic transaction, and an external race after the final check cannot be fully eliminated.

## Diff and recovery

The application result returns `backup_dir`, containing before/after copies and `record.json` without absolute host paths. Replace `<id>` with that result:

```bash
python3.11 /path/to/skill/scripts/run.py diff --project-root /path/to/project \
  --task-root /path/to/.bensz-api/task-YYYYMMDD-HHMM-topic \
  --backup-dir nsfc-research-content-writer/output/revision-<id>
python3.11 /path/to/skill/scripts/run.py restore --project-root /path/to/project \
  --task-root /path/to/.bensz-api/task-YYYYMMDD-HHMM-topic \
  --backup-dir nsfc-research-content-writer/output/revision-<id>
```

Recovery first protects the current versions. If any current file matches neither its original nor its proposal, or a backup is corrupt or mismatched, the entire recovery refuses to overwrite. Resolve the conflict first. A mixed set of originals and proposals after interruption is recoverable. The new recovery revision can also undo the recovery.

## Checks and compatibility

```bash
python3.11 /path/to/skill/scripts/validate_skill.py
python3.11 /path/to/skill/scripts/check_project_outputs.py --project-root /path/to/project
python3.11 /path/to/skill/scripts/run_checks.py --project-root /path/to/project --fail-on-risk-phrases
python3.11 /path/to/skill/scripts/create_test_session.py \
  --task-root /path/to/.bensz-api/task-YYYYMMDD-HHMM-topic --kind a --id v202611011300 --create-plan
```

The old check entry points retain `--no-content-check`, `--no-risk-scan`, and `--fail-on-risk-phrases`. They no longer require S identifiers; `checks.subgoal_markers_min` is deprecated with a notice. Phrase matches are advisory unless strict scanning is explicitly selected, and are not evidence of a false claim. Existing citation keys do not prove bibliographic authenticity or claim support. Scripts do not judge scientific consistency across sections.

`create_test_session.py` now requires the declared `--task-root`. Old plan flags produce a compatibility notice; plans/reports stay in that task. Formal maintenance plans belong in the repository's `docs/plans/`. It no longer creates Skill-local `plans/` or `tests/` directories. Runtime artifacts stay outside source directories. No State, Verifier, or Kernel dependency was added.

## Common questions

**Does missing information block everything?** Nonblocking gaps are recorded while supported edits continue. Passages depending on feasibility or project commitments remain pending. Do not invent sample sizes, cohorts, ethics dates, or effects.

**Why do missing bibkeys block writing?** Proposals must not introduce unresolved citations. Preserve necessary citations and pending-verification notes; correct the bibliography before resubmitting instead of removing claims to pass a check.

**Does every preview need fresh approval?** Preview is available for review; existing writing authorization permits application without repeated permission requests. Single-section permission does not authorize three-section editing.

## Further reading

[Research design and section writing](references/section_writing.md) · [Quality control](references/quality_control.md) · [Regression cases](references/regression_examples.md) · [Page planning](references/page_budget.md) · [Changes](CHANGELOG.md)
