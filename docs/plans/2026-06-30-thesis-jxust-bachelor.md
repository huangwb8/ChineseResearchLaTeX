# thesis-jxust-bachelor Implementation Plan

**Goal:** Add a Jiangxi University of Science and Technology undergraduate thesis/design template for issue #49.

**Architecture:** Keep the existing `bensz-thesis` layering: a thin `projects/thesis-jxust-bachelor/` example project, plus a dedicated package profile and style under `packages/bensz-thesis/`. Use `jxust` as the project and macro prefix to avoid colliding with the existing Jiangsu University of Science and Technology `thesis-just-bachelor` template.

**Tech Stack:** XeLaTeX, `ctexbook`, `bensz-thesis`, `fancyhdr`, `titlesec`, `titletoc`, project-level Python build wrapper.

**Minimal Change Scope:** Add JXUST thesis files, register them in `bensz-thesis` validation, update package metadata and local documentation. Avoid changing existing thesis template styles.

**Success Criteria:** `projects/thesis-jxust-bachelor` builds to `main.pdf`; `main.tex` exposes a `\jxustSetWorkType{thesis|design}` switch; package validation recognizes the new profile/style; README and changelog mention the new template.

**Verification Plan:** Run `python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-jxust-bachelor`, `python packages/bensz-thesis/scripts/validate_package.py --skip-compile`, `python scripts/sync_vscode_configs.py --check --project thesis-jxust-bachelor`, and targeted text checks for `thesis-jxust-bachelor`.

---

1. Extract issue #49 and official Word format facts.
2. Add JXUST profile/style and project scaffold.
3. Sync VS Code wrapper configuration.
4. Build and run package checks.
5. Review the diff for scope, correctness, and regressions.
