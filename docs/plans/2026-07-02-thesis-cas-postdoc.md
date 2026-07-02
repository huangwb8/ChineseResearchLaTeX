# Thesis CAS Postdoc Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a stable `thesis-cas-postdoc` template for Chinese Academy of Sciences postdoctoral research reports requested by issue #50.

**Architecture:** Reuse the existing `bensz-thesis` product line and project wrapper pattern. Add an independent profile/style pair for `thesis-cas-postdoc`, keep all CAS-specific report text in `projects/thesis-cas-postdoc/extraTex/`, and register the project in validation and documentation.

**Tech Stack:** XeLaTeX, `ctexbook`, `bensz-thesis`, `biblatex`, project-level Python build wrapper.

**Minimal Change Scope:** Allowed paths are `packages/bensz-thesis/`, `projects/thesis-cas-postdoc/`, `scripts/test_install_architecture.py`, `README.md`, `projects/README.md`, `CHANGELOG.md`, and this plan. Avoid changing existing thesis templates or shared fonts.

**Success Criteria:** `thesis-cas-postdoc` has its own `template.json`, profile, style, wrapper, front matter, body, references, and README; package validation recognizes it; official thesis build produces `projects/thesis-cas-postdoc/main.pdf`; existing thesis templates are not edited for style behavior.

**Verification Plan:** Run `python packages/bensz-thesis/scripts/validate_package.py --skip-compile`, `python scripts/sync_vscode_configs.py --check`, and `python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-cas-postdoc`.

---

### Task 1: Extract Requirements

**Files:**
- Read: `.bensz-api/skills/awesome-code/2026-07-02-21-00/output/converted/issue-50-research-report-format.txt`

**Steps:**
- Confirm required structure: cover, title page, Chinese and English abstracts, keywords, table of contents, lists of figures/tables when needed, symbols/abbreviations, body, references, appendices, resume, achievements, permanent contact address.
- Confirm page requirements: A4 paper, top 30 mm, left 35 mm, bottom 25 mm, right 20 mm, Chinese body in size 4 Songti, cover/title page in Heiti.

### Task 2: Add Template Implementation

**Files:**
- Create: `packages/bensz-thesis/profiles/bthesis-profile-thesis-cas-postdoc.def`
- Create: `packages/bensz-thesis/styles/bthesis-style-thesis-cas-postdoc.tex`
- Modify: `packages/bensz-thesis/scripts/validate_package.py`
- Modify: `packages/bensz-thesis/package.json`

**Steps:**
- Add profile mapping for `thesis-cas-postdoc`.
- Add CAS postdoc style macros with official margins, front matter helpers, headers, captions, lists, and link behavior.
- Register required files and compile target in validation.
- Bump `bensz-thesis` package version.

### Task 3: Add Project

**Files:**
- Create: `projects/thesis-cas-postdoc/**`

**Steps:**
- Start from the proven postdoc project wrapper structure.
- Replace SMU-specific metadata and assets with Chinese Academy of Sciences public demo data.
- Keep the repository thesis demo convention: author is `冯宝宝`, and sample research content is around `佐佐木希`.
- Include CAS report structure: cover, title page, abstract, contents, figure/table lists, abbreviations, body, references, appendix, resume, doctoral/postdoctoral achievements, permanent address, acknowledgements.

### Task 4: Sync Docs And Tests

**Files:**
- Modify: `README.md`
- Modify: `projects/README.md`
- Modify: `packages/bensz-thesis/README.md`
- Modify: `scripts/test_install_architecture.py`
- Modify: `CHANGELOG.md`

**Steps:**
- Add `thesis-cas-postdoc` to template lists and descriptions.
- Add release/runtime package assertions for the independent profile and style.
- Document the new issue #50 template in the changelog.

### Task 5: Verify And Review

**Commands:**
- `python packages/bensz-thesis/scripts/validate_package.py --skip-compile`
- `python scripts/sync_vscode_configs.py --check`
- `python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-cas-postdoc`
- `git diff --stat`

**Review Checklist:**
- No existing template style files were modified unless strictly necessary.
- No private or sensitive data was introduced.
- The generated PDF is built through the official thesis tool.
