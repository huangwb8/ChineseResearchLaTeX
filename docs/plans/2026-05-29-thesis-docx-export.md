# Thesis DOCX Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reusable `bensz-thesis` DOCX export path so thesis projects can produce an editable Word draft from the same LaTeX source.

**Architecture:** Keep PDF building unchanged, and add DOCX export as an explicit `docx` command in the thesis tool. Reuse the proven paper pipeline idea, `LaTeX -> Markdown -> HTML5+MathML -> DOCX`, but wrap it with thesis-specific source normalization, reference-doc discovery, degradation rules for complex objects, and a quality report.

**Tech Stack:** Python 3, Pandoc, optional `python-docx`, optional LibreOffice, LaTeX source parsing, DOCX XML inspection.

**Minimal Change Scope:** Modify only `packages/bensz-thesis/scripts/`, `packages/bensz-thesis/README.md`, selected `projects/thesis-*/README.md`, project wrappers under `projects/thesis-*/scripts/`, `tests/`, and root docs/changelog if the feature lands. Do not alter thesis PDF layout styles while implementing DOCX export.

**Success Criteria:** `python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir <project>` generates `main.docx`, keeps intermediate files under `.latex-cache/docx/` by default, emits a quality report, preserves headings/paragraphs/images/basic math, and marks unsupported complex objects clearly instead of failing silently.

**Verification Plan:** Run focused unit tests under `tests/`, then run DOCX export on at least `projects/thesis-smu-master`, `projects/thesis-nju-master`, `projects/thesis-smu-postdoc`, and `projects/thesis-ucas-doctor` with an explicit reference doc where required.

---

## Feasibility

This is feasible, and the repo already contains two strong proofs:

- `bensz-paper` already ships a stable DOCX chain: `LaTeX -> Markdown -> HTML5+MathML -> DOCX`, with Word math handled through MathML/OMML conversion. See [manuscript_tool.py](../../packages/bensz-paper/scripts/manuscript_tool.py#L10) and [manuscript_tool.py](../../packages/bensz-paper/scripts/manuscript_tool.py#L811).
- `thesis-ucas-doctor` already has a project-level prototype that converts thesis LaTeX source to DOCX, applies a reference Word template, and writes a quality report. See [export_docx.py](../../projects/thesis-ucas-doctor/scripts/export_docx.py#L1), [export_docx.py](../../projects/thesis-ucas-doctor/scripts/export_docx.py#L557), and [export_docx.py](../../projects/thesis-ucas-doctor/scripts/export_docx.py#L1213).

The hard part is not "can a DOCX be produced"; it can. The hard part is setting the right product promise. Thesis DOCX should be an editable Word draft with strong structure and reasonable style fidelity, not a pixel-perfect clone of the PDF. Complex tables, algorithm environments, code listings, bespoke cover pages, and school-specific front matter need explicit fallback rules and a report.

Current thesis tooling only exposes PDF build, clean, and PDF compare in the public package command. See [thesis_project_tool.py](../../packages/bensz-thesis/scripts/thesis_project_tool.py#L1) and [thesis_project_tool.py](../../packages/bensz-thesis/scripts/thesis_project_tool.py#L555). That makes the safest implementation path an additive `docx` subcommand.

## Product Promise

Phase 1 promise:

- Generate `main.docx` from the same `main.tex` / `extraTex/**/*.tex` source.
- Preserve document order, headings, body paragraphs, lists, basic figures, basic tables, inline math, display math, citations where bibliography data is discoverable, and common front/back matter headings.
- Support `--reference-doc` for school Word templates.
- Produce `main.docx.md` or `main_docx_quality_report.md` explaining generated files, unsupported objects, missing assets, style mapping, and required manual Word actions such as updating TOC fields.

Non-goals for Phase 1:

- Pixel-perfect PDF-to-Word layout equivalence.
- Perfect cover/title page reproduction for every school.
- Fully editable reconstruction of arbitrary `tabular`, `longtable`, TikZ, algorithm, minted/listings, custom macro-heavy environments.
- Automatic redistribution of official school Word templates when license is unclear.

## Recommended CLI

Add this command:

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx \
  --project-dir projects/thesis-smu-master
```

Useful options:

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx \
  --project-dir projects/thesis-ucas-doctor \
  --reference-doc <path-to-reference.docx> \
  --output main.docx \
  --keep-markdown
```

Do not change the existing `build` behavior in Phase 1. Thesis PDF users should not suddenly pay a DOCX dependency cost.

## Implementation Tasks

### Task 1: Add DOCX Export Contract Tests

**Files:**

- Create: `tests/bensz-thesis/test_thesis_docx_tool.py`
- Read: `projects/thesis-smu-master/main.tex`
- Read: `projects/thesis-ucas-doctor/scripts/export_docx.py`

**Step 1: Write parser and degradation tests**

Test small in-memory LaTeX snippets for:

- Direct `\input{extraTex/body/chapter-01.tex}` collection.
- Comment stripping without removing escaped `\%`.
- Heading conversion for `\chapter`, `\section`, `\subsection`, and starred headings.
- Figure conversion with `\includegraphics`.
- Table/algorithm/listing fallback text that records manual cleanup.
- Citation conversion to Pandoc citation syntax where possible.

**Step 2: Write CLI smoke test**

Run:

```bash
pytest tests/bensz-thesis/test_thesis_docx_tool.py -q
```

Expected before implementation: FAIL because `packages.bensz-thesis.scripts.thesis_docx_tool` does not exist.

### Task 2: Create a Package-Level DOCX Module

**Files:**

- Create: `packages/bensz-thesis/scripts/thesis_docx_tool.py`
- Modify: `packages/bensz-thesis/scripts/thesis_project_tool.py`

**Step 1: Move reusable ideas from the UCAS prototype**

Port the generic pieces from [export_docx.py](../../projects/thesis-ucas-doctor/scripts/export_docx.py#L1):

- TeX comment stripping.
- Braced argument parsing.
- `\texorpdfstring` flattening.
- Graphics path discovery and image resolution.
- Markdown rendering.
- Pandoc execution.
- DOCX style analysis and report writing.

Keep UCAS-specific checks out of the common module unless they are guarded by a profile hook.

**Step 2: Reuse the paper DOCX conversion shape**

Follow the paper chain documented at [manuscript_tool.py](../../packages/bensz-paper/scripts/manuscript_tool.py#L777):

```text
LaTeX fragments -> normalized Markdown -> HTML5+MathML -> DOCX
```

For thesis, keep a fallback direct Markdown-to-DOCX mode only if the MathML route fails, and record that fallback in the quality report.

**Step 3: Add public function**

Expose:

```python
def export_docx_project(
    project_dir: Path,
    tex_file: str = "main.tex",
    output: Path | None = None,
    reference_doc: Path | None = None,
    keep_markdown: bool = False,
    skip_style_normalization: bool = False,
) -> Path:
    ...
```

Expected output:

- `project_dir / "main.docx"` by default.
- `.latex-cache/docx/main.md` unless `--keep-markdown` also copies it to project root.
- `.latex-cache/docx/main_docx_quality_report.md`, with optional project-root copy if desired.

### Task 3: Add `docx` Subcommand

**Files:**

- Modify: `packages/bensz-thesis/scripts/thesis_project_tool.py`

**Step 1: Extend CLI parser**

Add:

```bash
docx --project-dir <path> --tex-file main.tex --reference-doc <path> --output <path> --keep-markdown --skip-style-normalization
```

**Step 2: Keep command behavior additive**

Existing commands remain:

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-smu-master
python packages/bensz-thesis/scripts/thesis_project_tool.py clean --project-dir projects/thesis-smu-master
python packages/bensz-thesis/scripts/thesis_project_tool.py compare --project-dir projects/thesis-smu-master --baseline-pdf tests/baseline.pdf
```

New command:

```bash
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-smu-master
```

### Task 4: Reference Word Template Discovery

**Files:**

- Modify: `packages/bensz-thesis/scripts/thesis_docx_tool.py`
- Optionally modify: `projects/thesis-ucas-doctor/docs/official/README.md`

**Discovery order:**

1. `--reference-doc`.
2. `project_dir/artifacts/reference.docx`.
3. `project_dir/docs/official/*.docx`.
4. `project_dir/docs/*.docx`.
5. No reference doc: allow Pandoc default DOCX, but warn in the quality report.

**Reasoning:** UCAS cannot ship official Word templates directly because of redistribution uncertainty, and that pattern should remain. See [README.md](../../projects/thesis-ucas-doctor/README.md#L47).

### Task 5: Source Collection for Thesis Projects

**Files:**

- Modify: `packages/bensz-thesis/scripts/thesis_docx_tool.py`
- Test: `tests/bensz-thesis/test_thesis_docx_tool.py`

**Rules:**

- Parse `main.tex` in order.
- Follow `\input{...}` and `\include{...}` recursively.
- Skip known setup files: `config-pre.tex`, `@config.tex`, package setup, and pure metadata files unless a profile adapter knows how to render them.
- Include front/body/back content in source order.
- Detect bibliography commands from `\addbibresource{...}` and `\bibliography{...}`.

**Expected behavior:** Missing included files should be reported as warnings in the quality report unless they are required for a fatal conversion path.

### Task 6: Object Conversion Policy

**Files:**

- Modify: `packages/bensz-thesis/scripts/thesis_docx_tool.py`
- Test: `tests/bensz-thesis/test_thesis_docx_tool.py`

**Automatic conversion:**

- Headings to Markdown headings.
- Paragraphs and simple inline formatting.
- `itemize` / `enumerate` to Markdown lists.
- `equation`, `align`, display math to TeX math blocks for Pandoc MathML conversion.
- `figure` with one `\includegraphics` to Markdown image plus caption.
- Basic `tabular` only if Pandoc handles it cleanly.

**Controlled degradation:**

- Complex tables become a captioned placeholder with original environment saved in `.latex-cache/docx/unsupported/`.
- Algorithms become captioned placeholders.
- Code listings become fenced code or placeholders, depending on source readability.
- TikZ and raw PDF-only constructs become placeholders.
- TOC/list-of-figures/list-of-tables become Word field-update instructions.

### Task 7: Style Normalization and Quality Report

**Files:**

- Modify: `packages/bensz-thesis/scripts/thesis_docx_tool.py`

**Quality report contents:**

- Generated DOCX path.
- Reference doc path or "Pandoc default".
- Pandoc version.
- Number of included source files.
- Missing assets.
- Unsupported object counts by environment.
- Style IDs used before/after normalization.
- Heading level counts.
- Manual actions: update TOC, inspect placeholders, refresh references if needed.

**Style normalization scope:**

- Remap Pandoc default paragraph styles to reference-doc Normal/Heading/Caption styles.
- Keep school-specific checks optional. UCAS resource-environment checks should remain a profile-specific extension, not the default global thesis report.

### Task 8: Migrate UCAS Prototype to the Common Command

**Files:**

- Modify: `projects/thesis-ucas-doctor/scripts/export_docx.py`
- Modify: `projects/thesis-ucas-doctor/README.md`

**Approach:**

- Turn `export_docx.py` into a thin compatibility wrapper that delegates to `packages/bensz-thesis/scripts/thesis_project_tool.py docx`.
- Preserve the old command for one release cycle.
- Keep UCAS-specific quality checks either in a small adapter or in the wrapper if they are not ready for generalization.

### Task 9: Update Project Wrappers and Docs

**Files:**

- Modify: `scripts/vscode/` only if VS Code command integration is desired in this phase.
- Modify: `packages/bensz-thesis/README.md`
- Modify: `projects/thesis-smu-master/README.md`
- Modify: `projects/thesis-nju-master/README.md`
- Modify: `projects/thesis-smu-postdoc/README.md`
- Modify: `projects/thesis-ucas-doctor/README.md`
- Modify: `CHANGELOG.md`

**Doc wording:**

- Call the output "editable Word draft".
- State clearly that complex objects may require manual review.
- Recommend `--reference-doc` for school-specific Word compliance.
- Keep PDF build docs unchanged.

### Task 10: End-to-End Verification

**Files:**

- Output only under project roots and `.latex-cache/`; no root test artifacts.
- Test artifacts under `tests/bensz-thesis/docx-export/` if persistent reports are needed.

**Commands:**

```bash
pytest tests/bensz-thesis/test_thesis_docx_tool.py -q
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-smu-master
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-nju-master
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-smu-postdoc
python packages/bensz-thesis/scripts/thesis_project_tool.py docx --project-dir projects/thesis-ucas-doctor --reference-doc <local-ucas-reference.docx>
```

Optional manual check:

```bash
soffice --headless --convert-to pdf --outdir tests/bensz-thesis/docx-export projects/thesis-smu-master/main.docx
```

## Rollout Strategy

1. Ship as experimental but public: `thesis_project_tool.py docx`.
2. Validate against the four mature thesis projects.
3. Promote UCAS wrapper to the common command.
4. Add per-school profile refinements only after the generic pipeline is stable.
5. Later consider `build --with-docx`, but only after dependency and runtime cost are acceptable.

## Key Risks

- Pandoc cannot fully understand arbitrary LaTeX macros. Mitigation: normalize common macros and report unsupported objects.
- Official Word templates may not be redistributable. Mitigation: user-supplied `--reference-doc` plus default Pandoc fallback.
- Tables are the biggest fidelity risk. Mitigation: support simple tables, degrade complex tables loudly.
- Thesis front matter differs heavily by school. Mitigation: keep project/profile adapters small and optional.
- Users may expect PDF-equivalent Word layout. Mitigation: docs must say "editable Word draft" and quality report must list manual checks.

## Recommendation

Do it, but do it in two tiers:

- Tier 1: generic, stable, honest DOCX export for all thesis projects.
- Tier 2: school/profile-specific polish for high-value templates such as UCAS, SMU, NJU, SYSU, and postdoc reports.

This makes the feature landable without overpromising, while still opening the door to a genuinely strong "LaTeX source, PDF plus Word" thesis workflow.
