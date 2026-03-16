# bensz-fonts Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `packages/bensz-fonts/` as the shared font foundation for the bensz LaTeX package family, with mandatory installation dependency handling and GitHub/Gitee mirror-aware downloads.

**Architecture:** Centralize bundled font assets and path-resolution helpers in a dedicated `bensz-fonts` package, then migrate package-level font lookups to consume that base layer instead of duplicating assets. Keep the root installer as the single public entry for multi-package installs, but teach it dependency expansion and mirror selection so existing workflows keep working while adding Gitee support.

**Tech Stack:** Python CLI installers, LaTeX package/runtime files, ZIP-based release packaging, pytest

---

### Task 1: Lock the desired install protocol with tests

**Files:**
- Create: `tests/test_install_architecture.py`
- Modify: `scripts/install.py`
- Modify: `scripts/pack_release.py`

**Step 1: Write failing tests for package dependency expansion**

Cover these expectations:
- requesting `bensz-paper` auto-adds `bensz-fonts`
- requesting multiple packages deduplicates `bensz-fonts`
- install order keeps `bensz-fonts` ahead of dependent packages

**Step 2: Write failing tests for remote mirror resolution**

Cover these expectations:
- `github` mirror keeps current raw/archive endpoints
- `gitee` mirror returns Gitee raw/archive endpoints
- parser accepts `--mirror`

**Step 3: Write failing tests for Overleaf runtime bundling**

Cover these expectations:
- NSFC runtime zip includes `bensz-fonts.sty`
- Paper runtime zip includes `bensz-fonts.sty`
- CV runtime zip includes bundled font assets from `bensz-fonts`

**Step 4: Run the tests and confirm they fail**

Run:

```bash
pytest -q tests/test_install_architecture.py
```

Expected:
- failures for missing helper functions / missing `bensz-fonts` runtime content

### Task 2: Add the new shared fonts package

**Files:**
- Create: `packages/bensz-fonts/README.md`
- Create: `packages/bensz-fonts/package.json`
- Create: `packages/bensz-fonts/bensz-fonts.sty`
- Create: `packages/bensz-fonts/fonts/...`

**Step 1: Move or copy shared bundled fonts into `packages/bensz-fonts/fonts/`**

Include:
- NSFC bundled fonts
- CV bundled fonts
- shared FontAwesome font files used by `bensz-cv`

**Step 2: Expose a stable font API in `bensz-fonts.sty`**

Add helpers for:
- package root / font root resolution
- collection-specific subdirectories
- NSFC bundled font setup
- CV bundled font setup helpers

**Step 3: Add package metadata**

Describe:
- package name
- repository
- dependency role as the shared font base

### Task 3: Teach installers about dependencies and mirrors

**Files:**
- Modify: `scripts/install.py`
- Modify: `packages/bensz-nsfc/scripts/install.py`

**Step 1: Add `bensz-fonts` to the supported package registry**

Include description, install mode, and dependency metadata.

**Step 2: Add mirror-aware remote endpoint resolution**

Support:
- `--mirror github`
- `--mirror gitee`
- `--mirror auto`

**Step 3: Expand requested packages to include required dependencies**

Ensure:
- `bensz-fonts` installs automatically for any other `bensz-*` package
- duplicate requests stay deduplicated
- delegated NSFC install receives the selected mirror

**Step 4: Keep current workflows intact**

Preserve:
- current `--ref` semantics
- TEXMFHOME installation behavior
- existing GitHub-default install commands

### Task 4: Migrate consumers and runtime bundles

**Files:**
- Modify: `packages/bensz-nsfc/bensz-nsfc-typography.sty`
- Modify: `packages/bensz-cv/resume.cls`
- Modify: `packages/bensz-cv/fontawesome.sty`
- Modify: `packages/bensz-cv/NotoSansSC_external.sty`
- Modify: `packages/bensz-cv/NotoSerifCJKsc_external.sty`
- Modify: `packages/bensz-cv/zh_CN-Adobefonts_external.sty`
- Modify: `scripts/pack_release.py`
- Modify: `packages/bensz-nsfc/scripts/validate_package.py`
- Modify: `packages/*/scripts/package/build_tds_zip.py`

**Step 1: Switch bundled-font consumers to `bensz-fonts`**

Keep package-specific typography decisions, but stop relying on local font asset directories.

**Step 2: Bundle `bensz-fonts` into Overleaf/runtime distributions**

Ensure all package families can resolve the shared base package from a standalone zip.

**Step 3: Update validation/TDS packaging**

Make the new base package visible to:
- validation checks
- TDS zip exports
- future local installs

### Task 5: Verify and document

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `packages/bensz-cv/README.md`
- Modify: `packages/bensz-nsfc/README.md`
- Create or modify: `packages/bensz-fonts/README.md`

**Step 1: Run automated tests**

Run:

```bash
pytest -q tests/test_install_architecture.py tests/test_update_readme_template_list.py
```

**Step 2: Run targeted packaging/build verification**

Run:

```bash
python packages/bensz-nsfc/scripts/validate_package.py --skip-compile
python packages/bensz-cv/scripts/cv_project_tool.py build --project-dir projects/cv-01 --variant all
python packages/bensz-nsfc/scripts/nsfc_project_tool.py build --project-dir projects/NSFC_General
```

**Step 3: Sync docs**

Document:
- new `bensz-fonts` package
- mandatory dependency behavior
- `--mirror gitee` install path
- any compatibility notes for Overleaf/release bundles
