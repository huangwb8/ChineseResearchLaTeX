<div align="center">
  <h1>Research Idea</h1>
  <p><strong>Turn research materials and auditable literature evidence into scientific questions, falsifiable hypotheses, and bounded research directions.</strong></p>
  <p><a href="README.md">中文</a> · <a href="#quick-start">Quick Start</a> · <a href="SKILL.md">Execution Contract</a> · <a href="references/runtime-guide.md">Runtime Guide</a></p>
</div>

<!-- README README_EN -->

`research-idea` builds a literature landscape, paper-level interpretations, and a research map before it generates, checks, and independently reviews candidates. It reports scientific value, confidence, and near-term investment separately, and distinguishes a recommendation, no qualified candidate in the evaluated scope, and insufficient evidence.

## Quick Start

Give a host that supports Agent Skills your research materials and explicitly invoke this Skill:

```text
Use the research-idea skill to derive key scientific questions and falsifiable hypotheses from ./notes and ./draft.md.
Investigate the literature before comparing recent work, and save the final report under ./docs/ideas/.
```

The expected result is a Markdown research-idea report named `Research-Idea_{repo}_{pr}_{timestamp}.md` by default. Intermediate evidence, novelty records, and review receipts remain in one `.bensz-api/task-*` workspace.

## What It Does

1. Uses `research-topic-extractor` to turn the input into searchable topics.
2. Uses `research-literature-search` and `research-literature-radar` to build a canonical candidate pool and complete landscape.
3. Uses `research-literature-interpretation` in paper-isolated tasks and builds a research map with stable O/R anchors.
4. Uses `parallel-vibe` to generate candidates and run multi-round independent reviews.
5. Runs multi-query novelty checks for retained candidates against direct neighbors, equivalent hypotheses, contrary evidence, and scope boundaries.
6. Produces a recommendation, no-qualified-candidate result, or insufficient-evidence result, while BSK State, Verifier, Gate, and completion checks preserve auditable evidence.

## Inputs and Outputs

| Type | Content |
| --- | --- |
| Minimum input | At least one research background, experimental observation, manuscript, file/directory, URL, repository, or PR clue |
| Optional constraints | Research objective, time/resource limits, output location, review rounds, and reviewer count |
| Formal output | `./docs/ideas/Research-Idea_{repo}_{pr}_{timestamp}.md`, or a user-specified Markdown path |
| Intermediates | `.bensz-api/task-{yyyymmdd-hhmm}-{description}/{skill-name}/input\|output\|log/` |

The report covers evidence depth, the research map, candidate or zero-candidate rationale, value/confidence/investment judgments, recent work and novelty checks, falsification paths, risks, and the smallest next step. It does not expose hidden workspace paths, test paths, or internal agent instructions.

## Research Narrative and Citations

The working map retains the full research-line index, Search record IDs, evidence depth, and stable O/R identifiers. The formal summary introduces the real question and essential terms, then explains existing answers, relationships among lines, the strongest neighbor, and the important unknown behind each O opportunity. Tables and timelines are optional. Review nearby evidence, contrary findings, source claims versus synthesis, and the strength of abstract-only evidence after drafting.

New reports use `research-idea-report-v3`. The default GB/T 7714—2025 numeric style links in-text citations such as `[1](#ref-1)` to the final `## References` section; `reference_map` maps working R identifiers to bibliography numbers. A requested journal or degree style may declare `citation_style: custom` and its source, with the mapping and style checked by the host AI. Earlier v2 R-anchor reports remain readable but cannot certify a new run.

## Usage Examples

### Derive candidates from an observation

```text
Use the research-idea skill.
Input: treatment A increases cell migration without changing proliferation; RNA-seq shows pathway B is upregulated.
Constraint: retain only directions that can produce decisive evidence within six months; high feasibility must not compensate for low scientific value.
Output: a research-idea report under the default docs/ideas directory.
```

### Find novelty in project materials

```text
Use the research-idea skill to analyze ./project-background/ and ./grant-draft.md.
Build the literature landscape and research map before proposing candidates; check direct neighbors, equivalent hypotheses, and contrary evidence for every proposed recommendation.
Run 5 independent review rounds and report scientific value, confidence, and near-term investment separately.
```

## Scope

Use this Skill for literature-grounded scientific-question discovery, falsifiable-hypothesis development, novelty assessment, and research-direction comparison.

Use an adjacent Skill for these tasks:

- The question is fixed and only an experimental or analysis plan is needed: `research-plan`.
- A systematic review, related work, or full review manuscript is needed: `research-literature-review`.
- Only an auditable candidate-paper pool is needed: `research-literature-search`.
- Literature evidence is unnecessary and the task is ordinary ideation: use a general brainstorming workflow.

## Configuration and Scripts

`config.yaml` is the source of truth for the version, default rounds, dependencies, output, and BSK runtime declaration. The main entries are:

| Entry | Purpose |
| --- | --- |
| `scripts/start_workflow.py` | Atomically initializes the workspace and BSK run/visit/attempt identity |
| `scripts/phase_entry.py` | Handles phase authorization, Verifier handoff, Gate, transition, and retry |
| `scripts/validate_report.py` | Checks report structure, fields, naming, and path leakage |
| `scripts/check_completion.py` | Checks dependency evidence, receipts, Gate/transition binding, and completed state |
| `scripts/edge_rules.py` | Shared domain rules for the phase entry, completion checker, and deterministic Verifier |

See the [runtime guide](references/runtime-guide.md) for commands and recovery paths. See the [report template](references/report-template.md) for the output contract and the [research synthesis guide](references/research-synthesis.md) for map construction and value screening.

## Completion Semantics and Limitations

The existence of a report does not prove completion. `artifact_ready`, `execution_recorded`, `evidence_sufficient`, and `claim_eligible` are verified separately; formal `completed` status also requires all required Verifiers, the BSK Gate, the bound transition, and `check_completion.py` to pass.

`bounded_recommendation`, `degraded`, and `insufficient` are valid, honest interim deliveries, but they must not be presented as completed results. Legacy completion v2–v5 runs or runs without evidence binding remain read-only and are not backfilled as new completion records.

## FAQ and Further Documentation

**Why is there no recommended direction?** The evidence may be sufficient to reject the current candidates, or it may be insufficient to judge them. The report distinguishes `no_qualified` from `insufficient` and provides restart conditions or a recovery point.

**Why does it not immediately write an experimental plan?** This Skill first tests whether the question and hypothesis are worth pursuing. Once a direction is selected, use `research-plan` for the detailed design.

**Is an abstract enough?** Abstracts can support relevance checks and obvious non-equivalence exclusions. Full text is normally required for neighbors that determine mechanism, results, or novelty; otherwise the claim must be narrowed.

- [Skill execution contract](SKILL.md)
- [Runtime guide](references/runtime-guide.md)
- [Novelty assessment guide](references/novelty-check.md)
- [Independent review reference](references/agent-review-prompt.md)
- [Changelog](CHANGELOG.md)
