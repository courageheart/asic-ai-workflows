# Skill Validation And Testing Plan

## Goal

Move this repository from static smoke-asset validation to live, measurable
skill validation that answers the questions that matter for AI engineering
artifacts:

- does the skill improve first-attempt correctness
- does the skill help the agent understand the task faster and stay focused
- does the skill reduce unsupported assumptions and repair-loop churn
- does the skill improve downstream artifact quality for later skills and flows

The plan below stays aligned with the current repository model:

- `skills/` define narrow engineering tasks
- `rules/` define shared grounding and output constraints
- `flows/` compose multiple skills
- `datasets/fixtures/` and `evals/` hold reusable validation assets

## Current Repository Reality

The repository already has:

- schema-backed skill outputs
- fixtures for RTL planning, CDC, timing, and DV planning
- smoke metadata and golden outputs
- local and CI scripts for structure and artifact validation
- a Verilator-based RTL compile check for supported fixtures

The repository does not yet have:

- a live model-eval harness that executes skills against the corpus
- behavioral scoring for generated RTL
- mutation-based defect suites for audit skills
- downstream quality measurements across chained skills

That means the next quality layer should extend the current smoke assets instead
of replacing them.

## Validation Objectives

The validation system should optimize for the repo goals in `README.md` and
`AGENTS.md`:

- engineering usefulness over presentation
- structured outputs over free-form prose
- deterministic behavior where possible
- evidence-grounded conclusions
- reusable artifacts instead of one-off prompts
- composability across skills and flows

## Initial Skill Scope

Start with the five skills that most directly control front-end quality and
downstream handoff quality in `flows/block-level-rtl-plan/`.

### 1. `block-requirements-normalizer`

Primary validation question:

- does the skill turn a loose brief into a stable, complete, and useful intake
  artifact without inventing requirements

Why it is first:

- every downstream skill depends on requirement quality
- this is the first place to measure focus, compression, and question discipline

### 2. `microarchitecture-spec-author`

Primary validation question:

- does the skill convert normalized requirements into a traceable spec that
  improves downstream RTL generation

Why it is second:

- this is the bridge between intent and implementation
- it should make downstream `rtl-designer` runs more correct and less ambiguous

### 3. `rtl-designer`

Primary validation question:

- does the skill emit synthesizable, traceable RTL that works on the first
  attempt for small blocks

Why it is third:

- this is the main first-attempt correctness target
- this skill creates the artifact that later audits and flows consume

### 4. `rtl-lint-auditor`

Primary validation question:

- does the skill reliably catch code-local blocking RTL issues with low false
  positive rates

Why it is fourth:

- this is the fastest static correctness backstop for generated RTL
- it directly measures whether the repo prevents expensive repair loops

### 5. `rtl-cdc-linter`

Primary validation question:

- does the skill correctly identify real CDC hazards and avoid being fooled by
  naming conventions or partial structure

Why it is fifth:

- CDC is one of the most important early multi-clock failure modes
- the repository already has seed fixtures and rule support for this area

## Validation Dimensions

Each live eval should score one or more of the dimensions below.

### 1. Artifact Contract Integrity

Measure whether the output stays inside the skill contract.

Key metrics:

- schema pass rate
- required-section completeness
- enum and field stability
- deterministic ordering stability across repeated runs

### 2. First-Attempt Correctness

Measure whether the first output is already usable without repair.

Key metrics:

- first-attempt schema pass rate
- first-attempt compile rate for generated RTL
- first-attempt self-checking simulation pass rate
- first-attempt blocking-finding-free rate on cases expected to be clean
- first-attempt blocker-detection rate on cases expected to be faulty

### 3. Agent Understanding And Focus

Measure whether the skill helps the agent converge faster and with less drift.

Key metrics:

- time to first acceptable artifact
- tokens to first acceptable artifact
- clarification-question rate
- unnecessary-question rate
- unsupported-assumption rate
- scope-drift rate

Recommended method:

- compare a baseline run without the skill artifact against a run with the skill
  artifact available to the next stage

### 4. Traceability And Grounding

Measure whether the skill preserves evidence and explicit uncertainty.

Key metrics:

- requirement trace coverage
- unsupported-trace-link rate
- unresolved-item precision
- invented-detail rate
- line or signal grounding accuracy for audit skills

### 5. Downstream Lift

Measure whether one skill materially improves the next stage.

Key metrics:

- normalized requirements -> spec quality lift
- spec -> RTL first-attempt correctness lift
- generated RTL -> audit cleanliness lift after one repair loop
- package or handoff readiness lift after chained execution

### 6. Audit Accuracy

Measure whether analysis skills find the right issues with the right severity.

Key metrics:

- finding precision
- finding recall
- severity accuracy
- file and line accuracy
- duplicate-suppression accuracy
- false positive rate on clean designs

## Per-Skill Scorecards

The first five skills should each have a small scorecard with a primary metric
set and acceptance thresholds.

### `block-requirements-normalizer`

Primary metrics:

- requirement extraction precision and recall against a gold requirement set
- PPA completeness detection accuracy
- blocking-question precision
- unnecessary-question rate
- deterministic `REQ-NNN` stability across repeated runs

Phase 1 target:

- at least 95% schema pass
- at least 90% PPA missing-field detection accuracy
- at most 10% unnecessary-question rate

### `microarchitecture-spec-author`

Primary metrics:

- requirement coverage into spec sections
- unsupported-detail rate
- unresolved-item precision
- diagram appropriateness accuracy
- downstream RTL first-attempt lift versus using the raw brief directly

Phase 1 target:

- at least 90% traced requirement coverage
- at most 10% unsupported-detail rate
- measurable improvement in downstream RTL compile or simulation success

### `rtl-designer`

Primary metrics:

- first-attempt schema pass rate
- first-attempt compile rate
- first-attempt self-checking simulation pass rate
- blocking lint count on cases intended to be clean
- traceability coverage into emitted RTL
- average repair-loop count

Phase 1 target:

- at least 95% schema pass
- at least 85% compile pass on Tier 0 and Tier 1 designs
- at least 75% simulation pass on Tier 0 and Tier 1 designs
- average repair-loop count below 1.0 on Tier 0 designs

### `rtl-lint-auditor`

Primary metrics:

- defect precision and recall on seeded lint mutations
- severity accuracy
- line accuracy
- false positive rate on clean gold RTL

Phase 1 target:

- at least 90% precision
- at least 90% recall on blocking seeded defects
- at most 5% false positive rate on clean Tier 0 and Tier 1 designs

### `rtl-cdc-linter`

Primary metrics:

- crossing precision and recall
- synchronization-method classification accuracy
- severity accuracy
- destination consume-site line accuracy
- naming-only false-safe rate

Phase 1 target:

- at least 90% recall on seeded unsafe crossings
- at least 90% precision on reported violations
- zero false-safe passes on naming-only synchronizer traps

## Evaluation Methods

Use multiple evaluation methods because no single scoring mode is strong enough
for all five skills.

### 1. Schema And Contract Checks

Keep the existing smoke checks as the first gate.

Use for:

- all skills
- all fixtures
- repeated-run determinism checks

### 2. Behavioral RTL Checks

Score generated RTL with tool-backed behavior, not only text comparison.

Use for `rtl-designer` outputs:

- parse and compile with the supported simulator flow
- run self-checking testbenches
- run lint-style structural checks where available
- compare observed behavior against the gold testbench expectations

### 3. Mutation Testing For Audit Skills

Create gold-clean RTL and inject one controlled defect at a time.

Use for:

- `rtl-lint-auditor`
- `rtl-cdc-linter`

Recommended mutation families:

- missing combinational assignment
- reset mismatch
- width truncation or sign hazard
- multi-driver register or output
- unsynchronized single-bit crossing
- unsafe multi-bit crossing
- naming-only synchronizer trap
- duplicated consume-site crossing

### 4. Downstream Chained Evaluation

Run consecutive skills and score whether the previous skill improved the next
skill's result.

Recommended ablations:

- raw brief only
- raw brief plus rules only
- prior skill output only
- full chained flow context

This is the main mechanism for proving:

- faster understanding and focus
- fewer repair loops
- better first-attempt correctness downstream

### 5. Repeated-Run Stability

Run each case multiple times with the same prompt and model configuration.

Score:

- exact schema stability
- stable IDs and ordering where required
- variance in key metrics
- variance in unresolved items and blocking conclusions

## Corpus Strategy

Build the corpus in tiers. Start small, then expand toward hierarchical and
multi-clock designs.

### Tier 0: Tiny Leaf RTL

Purpose:

- maximize signal during early iteration
- isolate single failure modes

Recommended designs:

- counter
- edge detector
- pulse stretcher
- one-hot FSM
- priority arbiter
- small status register block
- 2-FF synchronizer
- shallow single-clock FIFO

### Tier 1: Single-Module Control And Datapath Blocks

Purpose:

- test realistic block behavior while keeping debug cost low

Recommended designs:

- threshold controller
- command dispatcher
- timer or watchdog block
- load/store command processor
- status FIFO wrapper

### Tier 2: Small Hierarchical Designs

Purpose:

- test whether skills preserve traceability and avoid confusion across module
  boundaries

Recommended designs:

- top module instantiating datapath plus controller
- top module instantiating counter plus IRQ block
- small bridge or packetizer with submodules

### Tier 3: Multi-Clock And Reset-Interaction Blocks

Purpose:

- test CDC and early front-end review quality on more realistic crossings

Recommended designs:

- event bridge
- async FIFO wrapper
- status-transfer bridge
- control plus data crossing pair

### Tier 4: Public Or Internal Provenance Cases

Purpose:

- test against designs with stronger real-world credibility

Use for:

- nightly regressions
- comparison against simpler synthetic cases
- final benchmark reporting

## Initial Case Plan

Start with a compact but useful Phase 1 matrix:

- 8 Tier 0 cases
- 4 Tier 1 cases
- 3 Tier 2 cases
- 3 Tier 3 cases

Suggested priority order from the current repository fixtures:

1. `single_clock_controller`
2. `command_dispatch_fsm`
3. `load_store_command_processor`
4. `dual_clock_event_bridge`
5. `unsync_single_bit`
6. `explicit_2ff`
7. `multi_consumer_crossing`
8. `naming_only_sync_trap`

Then add new small leaf cases before expanding the hierarchical set.

## Golden RTL Strategy

The repository should use both internal and public sources, but keep provenance
explicit for every borrowed case.

### Preferred Source: Internal Silicon-Proven Or Tape-Out RTL

Best option:

- ask for 3-10 internal modules that are post-silicon, production, or at least
  taped out

Why this is best:

- it matches the coding style, block shapes, and review standards that matter to
  this repository's users
- it avoids overfitting to public open-source coding conventions

Required provenance metadata for each internal case:

- owner or source team
- module name
- design family
- status: post-silicon, production, taped out, or simulation-only
- any redaction notes
- license or sharing constraint inside the repo

### Public Source Candidates

Use public sources to bootstrap the corpus until internal gold RTL is available.

Important rule:

- keep a `provenance.yaml` record for every borrowed module that distinguishes
  between project-level evidence and exact module-level evidence

Public candidates reviewed on 2026-04-11:

- OpenTitan: the project site states that OpenTitan is in production and
  deployed in volume devices. This makes it the best public source for small
  security and primitive-style blocks.
- Ibex: the public README states that Ibex is production-quality and has seen
  multiple tape-outs. This is a strong source for CPU-adjacent leaf and
  submodule RTL.
- PULPissimo: the public README states that PULPissimo is the main SoC
  controller for recent PULP chips and cites the Quentin 22nm SoC paper. This
  is a strong source for small controllers and subsystem glue logic.
- raven-picorv32: the public README describes it as a silicon-validated SoC
  implementation and a silicon-proven starting point. This is a useful backup
  source for small SoC-level blocks.

Recommended public-case preference:

1. small OpenTitan primitive or utility blocks
2. small Ibex submodules or support blocks
3. small PULP or PULPissimo controllers
4. carefully selected silicon-validated backup modules from other open projects

### Public Source Due-Diligence Checklist

Before adding a public design as gold RTL, capture:

- upstream repository URL
- exact commit SHA
- module path
- license
- project-level silicon or tape-out evidence link
- whether the exact module is known to be instantiated in silicon, or only
  inherits project-level provenance
- why the chosen module is appropriate for Tier 0, Tier 1, Tier 2, or Tier 3

## Gold Artifact Requirements

Each live-eval case should include the artifacts needed to score behavior, not
just structure.

Recommended artifacts:

- prompt or input files
- gold requirements or expected findings
- allowed output rubric
- self-checking testbench for RTL-generation cases
- compile manifest if the case spans multiple files
- mutation notes for defect-seeded audit cases
- provenance metadata for public or internal source tracking

## Proposed Repository Layout

Add a parallel live-eval structure without disturbing the current smoke layer.

```text
docs/
  skill-validation-and-testing-plan.md

evals/
  smoke/
  live/
    block-requirements-normalizer/
      suite.yaml
      cases/
        counter-intake/
          input/
          gold/
          rubric.yaml
    microarchitecture-spec-author/
      suite.yaml
      cases/
    rtl-designer/
      suite.yaml
      cases/
        single-clock-controller/
          input/
          gold/
          tb/
          compile_manifest.f
          rubric.yaml
          provenance.yaml
    rtl-lint-auditor/
      suite.yaml
      cases/
    rtl-cdc-linter/
      suite.yaml
      cases/
```

Recommended supporting scripts:

- `scripts/run_live_skill_eval.py`
- `scripts/score_live_skill_eval.py`
- `scripts/summarize_live_skill_eval.py`

These scripts should remain deterministic wrappers around model execution,
scoring, and report generation. They should not duplicate skill logic.

## Rollout Plan

### Phase 0: Scoring Design

Deliverables:

- this validation plan
- live-eval case format definition
- per-skill scorecards
- provenance template

Exit criteria:

- agreement on the first five skills
- agreement on the first case set
- agreement on baseline metrics and thresholds

### Phase 1: Canary Live Eval For The First Five Skills

Deliverables:

- 1-3 live cases per first-five skill
- self-checking benches for the first `rtl-designer` cases
- mutation cases for `rtl-lint-auditor` and `rtl-cdc-linter`
- a local runner that emits machine-readable results

Exit criteria:

- stable local execution
- enough signal to identify first-attempt correctness regressions

### Phase 2: Expand To Hierarchical And Multi-Clock Cases

Deliverables:

- Tier 2 and Tier 3 cases
- chained-eval scoring for `requirements -> spec -> RTL`
- nightly regression reports

Exit criteria:

- measurable downstream lift across chained skills
- acceptable false positive rates on audit skills

### Phase 3: CI And Governance Integration

Deliverables:

- small PR canary suite
- nightly full live-eval matrix
- trend reporting against the default branch

Recommended CI policy:

- keep static checks required on all PRs
- run only a small live-eval canary set on PRs
- run the larger corpus nightly or on demand until cost and stability justify
  stricter gating

## Reporting

Each live-eval run should emit:

- per-case results
- per-skill summary metrics
- failure examples
- comparison versus the current baseline on `main`
- links to the exact inputs, gold artifacts, and model configuration used

Keep the reporting focused on engineering usefulness. Avoid generic benchmark
scores that do not map back to skill behavior.

## Residual Risks

Even with a strong live-eval layer:

- no public corpus perfectly represents proprietary design environments
- project-level silicon provenance does not automatically prove exact
  module-level silicon use
- first-attempt correctness can vary by model family and prompt wrapper
- audit-skill precision can look inflated if the mutation suite is too narrow

The plan should therefore keep both public and internal corpora, and should
separate exact module provenance from broader project provenance.

## Recommended Immediate Next Steps

1. Approve the first-five skill scope and the Phase 1 metric thresholds.
2. Decide whether internal taped-out or post-silicon RTL can be contributed for
   the first benchmark wave.
3. Create `evals/live/` with one canary case each for:
   `block-requirements-normalizer`, `microarchitecture-spec-author`,
   `rtl-designer`, `rtl-lint-auditor`, and `rtl-cdc-linter`.
4. Add the first self-checking benches and defect-seeded mutation cases.
5. Add a local live-eval runner before making any live suite a required CI gate.

## Public References

- OpenTitan project site: https://opentitan.org/
- lowRISC history: https://lowrisc.org/history/
- Ibex repository: https://github.com/lowRISC/ibex
- PULPissimo repository: https://github.com/pulp-platform/pulpissimo
- raven-picorv32 repository: https://github.com/efabless/raven-picorv32
