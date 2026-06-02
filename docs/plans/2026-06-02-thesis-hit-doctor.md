# thesis-hit-doctor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use awesome-code planning and code-reviewer checks to implement this plan task-by-task.

**Goal:** Add a Harbin Institute of Technology doctoral dissertation template for issue #45.

**Architecture:** Register `thesis-hit-doctor` as an independent `bensz-thesis` template/profile/style, with a thin project under `projects/`. Keep HIT-specific cover pages and thesis structure in the new style and project files so existing thesis templates remain untouched.

**Tech Stack:** LaTeX/XeLaTeX, `bensz-thesis`, `ctexbook`, Python build wrappers, VS Code LaTeX Workshop templates.

**Minimal Change Scope:** Allowed paths are `packages/bensz-thesis/`, `projects/thesis-hit-doctor/`, `README.md`, `projects/README.md`, `CHANGELOG.md`, `docs/plans/`, and tests/issue scratch data. Avoid changing existing thesis style files except shared validation lists.

**Success Criteria:** `thesis-hit-doctor` has an independent profile/style/project identity, renders a complete HIT doctoral example PDF, is included in package validation and template indexes, and does not modify existing thesis style behavior.

**Verification Plan:** Run `python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-hit-doctor`, `python packages/bensz-thesis/scripts/validate_package.py --skip-compile`, `python scripts/sync_vscode_configs.py --check --project thesis-hit-doctor`, and a focused README/template-list test.

---

### Task 1: Source And Scope

**Files:**
- Read: issue #45 and HIT official page / Word example
- Create: `projects/thesis-hit-doctor/docs/official/README.md`

**Steps:**
1. Record the official HIT graduate school page and attachment URL.
2. Record the SHA256 hash of the public Word example.
3. State that the project does not redistribute the official Word source.

### Task 2: Package Registration

**Files:**
- Create: `packages/bensz-thesis/profiles/bthesis-profile-thesis-hit-doctor.def`
- Create: `packages/bensz-thesis/styles/bthesis-style-thesis-hit-doctor.tex`
- Modify: `packages/bensz-thesis/scripts/validate_package.py`

**Steps:**
1. Add a profile that points only to the new HIT style file.
2. Implement HIT fonts, margins, page styles, cover pages, front matter helpers, chapter formatting, TOC, captions, tables, and declaration helpers.
3. Register required files and compile validation entry.

### Task 3: Project Scaffold

**Files:**
- Create: `projects/thesis-hit-doctor/**`

**Steps:**
1. Add `template.json`, project README, AGENTS/CLAUDE, VS Code workspace/config, and build wrapper.
2. Add `main.tex`, metadata, abstracts, body chapters, conclusion, references, achievements, review/defense info, declaration, thanks, and resume.
3. Keep public demonstration content generic and privacy-safe.

### Task 4: Docs And Indexes

**Files:**
- Modify: `README.md`
- Modify: `projects/README.md`
- Modify: `CHANGELOG.md`

**Steps:**
1. Add `thesis-hit-doctor` to human-readable thesis project lists.
2. Record the package/project/template change in the root changelog.
3. Keep release download links absent until an actual release asset exists.

### Task 5: Verification And Review

**Files:**
- Generated: `projects/thesis-hit-doctor/main.pdf`

**Steps:**
1. Build the HIT project with the official thesis tool.
2. Run package structure validation without compiling all existing templates.
3. Check VS Code sync for the new project.
4. Review diff against issue requirements and the code-reviewer checklist.
