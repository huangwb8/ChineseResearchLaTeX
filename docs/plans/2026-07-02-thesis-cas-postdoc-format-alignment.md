# Thesis CAS Postdoc Format Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Tighten `thesis-cas-postdoc` against the font, paragraph, page-numbering, figure/table, bibliography, and appendix rules extracted from `projects/thesis-cas-postdoc/assets/1-2.doc`.

**Architecture:** Keep the independent `thesis-cas-postdoc` profile/style inside the existing `bensz-thesis` product line. Put reusable formatting behavior in `packages/bensz-thesis/styles/bthesis-style-thesis-cas-postdoc.tex`, and keep report content/order fixes in `projects/thesis-cas-postdoc/main.tex` and `projects/thesis-cas-postdoc/extraTex/`.

**Tech Stack:** XeLaTeX, `ctexbook`, `bensz-thesis`, `biblatex`, `caption`, `fancyhdr`, official `thesis_project_tool.py` build entry.

**Minimal Change Scope:** Allowed paths are `packages/bensz-thesis/styles/bthesis-style-thesis-cas-postdoc.tex`, `projects/thesis-cas-postdoc/main.tex`, `projects/thesis-cas-postdoc/extraTex/`, `projects/thesis-cas-postdoc/README.md`, `packages/bensz-thesis/README.md`, and `CHANGELOG.md`. Avoid changing other thesis templates, shared fonts, and unrelated package scripts.

**Success Criteria:** The template still builds through the official thesis tool; generated PDF remains A4 with 30/35/25/20 mm margins; body text uses size-4 Songti; Chinese cover/title/chapter text uses Heiti or the configured CJK sans family; body page 1 starts at the first chapter; page numbers are placed at bottom-right where required; figure captions are below figures and table captions are above tables; appendix counters use A/B/C prefixes; bibliography style choices are documented and closer to the source rule.

**Verification Plan:** Run `python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-cas-postdoc`, `pdfinfo projects/thesis-cas-postdoc/main.pdf`, `pdffonts projects/thesis-cas-postdoc/main.pdf`, and inspect `projects/thesis-cas-postdoc/.latex-cache/main.log` for new warnings.

---

### Task 1: Document The Source Rule Mapping

**Files:**
- Modify: `projects/thesis-cas-postdoc/README.md`

**Steps:**
- Add a short "format source mapping" section that maps `1-2.doc` rules to template behavior: A4, margins, body font, cover/title font, front matter order, lists of figures/tables, page numbering, and appendix numbering.
- Mark which rules are strict implementation targets and which are content-authoring guidance.
- Keep the section concise; do not paste the full Word source.

### Task 2: Fix Page Number Placement And Start Point

**Files:**
- Modify: `packages/bensz-thesis/styles/bthesis-style-thesis-cas-postdoc.tex`
- Modify: `projects/thesis-cas-postdoc/main.tex`

**Steps:**
- Change the main report page style from centered footer page numbers to bottom-right footer page numbers for Arabic-numbered body pages.
- Keep front matter page numbers separate; decide whether Roman front matter remains centered or also moves right, then document the choice.
- Ensure `\pagenumbering{arabic}` and `\setcounter{page}{1}` remain immediately before the first chapter input.
- Rebuild and confirm the first body chapter is page 1.

### Task 3: Make Chapter And Section Break Behavior Explicit

**Files:**
- Modify: `packages/bensz-thesis/styles/bthesis-style-thesis-cas-postdoc.tex`
- Modify: `projects/thesis-cas-postdoc/main.tex`

**Steps:**
- Add a dedicated `\casdocMainChapter` or equivalent helper only if it reduces repeated manual `\clearpage` calls.
- Ensure each body chapter starts on a fresh page, matching the "每一篇（或部分）必须另页起" rule.
- Keep `openany` unless right-page enforcement becomes a confirmed requirement for printed duplex output.
- Rebuild and inspect the body chapter boundaries.

### Task 4: Align Figure, Table, And Appendix Counters

**Files:**
- Modify: `packages/bensz-thesis/styles/bthesis-style-thesis-cas-postdoc.tex`
- Modify: `projects/thesis-cas-postdoc/extraTex/body/*.tex`
- Modify: `projects/thesis-cas-postdoc/extraTex/back/appendix.tex`

**Steps:**
- Split caption setup by type so figure captions render below figures and table captions render above tables by default.
- Keep table captions centered and above tables, with table notes below tables when present.
- After `\appendix`, redefine appendix figure/table/equation counters to use `A1`, `B2`, `B3` style prefixes rather than chapter-number prefixes.
- Replace any sample manual figure/table labels with semantic captions and labels.

### Task 5: Revisit Bibliography Defaults

**Files:**
- Modify: `packages/bensz-thesis/styles/bthesis-style-thesis-cas-postdoc.tex`
- Modify: `projects/thesis-cas-postdoc/README.md`

**Steps:**
- Decide whether bibliography should inherit body size-4/1.5 spacing or keep a compact thesis-style default.
- If compact defaults are kept, document them as a pragmatic template choice, not a direct rule from `1-2.doc`.
- Keep `gb7714-2015` unless the project explicitly needs a historical GB7714-87 emulation mode.

### Task 6: Verify And Review

**Commands:**
- `python packages/bensz-thesis/scripts/thesis_project_tool.py build --project-dir projects/thesis-cas-postdoc`
- `pdfinfo projects/thesis-cas-postdoc/main.pdf`
- `pdffonts projects/thesis-cas-postdoc/main.pdf`
- `rg -n "Warning|Overfull|Underfull|undefined|Citation|Reference" projects/thesis-cas-postdoc/.latex-cache/main.log`

**Review Checklist:**
- A4 and margins still match the source rule.
- Font fallback remains portable across macOS, Linux, and Windows.
- No existing non-CAS thesis template behavior changed.
- New warnings are either eliminated or explicitly explained.
- Public demo content remains anonymized and follows repository thesis demo conventions.
