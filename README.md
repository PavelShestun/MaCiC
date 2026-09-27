# Mathematics CI/CD v0.4.3

A production-oriented template for AI-assisted mathematical research in Lean. The repository treats every headline theorem as a versioned research object with separate gates for formal validity, semantic adequacy, proof understanding, provenance, novelty, and independent reproduction.

The central rule is simple: **a green Lean build is evidence of formal correctness relative to the encoded definitions and axioms; it is not by itself evidence of intended meaning or novelty.**

## What v0.4.3 automates

### Hard verification plane

- Stable hypothesis IDs (`H-XXXX`) and an explicit state machine.
- Lean `sorry` / `admit` detection outside comments and strings.
- Frozen theorem statement hash + human-readable snapshot.
- Statement-drift blocking and forced re-review after semantic changes.
- Review records bound to the exact statement and evidence they reviewed.
- Review freshness: literature, proof-understanding, reproduction, and final approvals become stale when their evidence changes.
- Structured semantic, proof-understanding, literature, reproduction, and final reviews.
- Provenance registry and optional assumption-ablation gate.
- `lake build` plus a **fresh transitive axiom traversal**; built-in `#print axioms` is retained as a secondary diagnostic.
- **Elaborated Lean dependency extraction** from `ConstantInfo`, not regex proof parsing.
- Required exact dependency evidence and environment lock before `VERIFIED_RESULT`.
- GitHub required checks, merge-queue compatibility, CODEOWNERS, and ruleset bootstrap.
- Versioned verification packets with SHA-256 manifests.
- Controlled research release workflow that refuses to overwrite an existing research release.

### Analysis plane

- Semantic statement diff: assumptions/binders vs conclusion.
- Fast source-level dependency graph for local iteration.
- Exact Lean dependency DAG in CI or any environment with Lean installed.
- Review-surface prioritization using provenance and dependency reachability.
- Assumption-ablation experiment registry.
- Adversarial LLM review with a split secret boundary.
- **Blind Agent Context Layer**: role-specific visibility profiles, sanitized context packets, leakage scanning, and cryptographic input manifests.

Analysis tools can focus reviewers. They cannot certify correctness, importance, or novelty.

## Quick start

```bash
python -m pip install -e '.[dev]'
pytest -q
researchctl workflow-audit
researchctl validate
researchctl doctor
```

With Lean installed:

```bash
lake --no-ansi build
researchctl axioms-all
researchctl deps-exact-all
researchctl env-lock
```

Create a theorem research object:

```bash
researchctl new H-0042 "Scaling rigidity candidate"
# edit hypotheses/H-0042.yaml and create the Lean declaration
researchctl freeze H-0042
researchctl deps H-0042                 # fast advisory graph
researchctl deps-exact H-0042           # elaborated graph; requires Lean
researchctl provenance-init H-0042
researchctl ablate H-0042
researchctl review-surface H-0042
researchctl fingerprint H-0042
researchctl review-init H-0042
researchctl report H-0042
```

Before handoff or publication:

```bash
researchctl audit H-0042
researchctl validate
researchctl packet H-0042
```

## Status model

```text
CANDIDATE
  -> SPEC_DRAFT
  -> SPEC_FROZEN
  -> FORMALIZED
  -> SEMANTIC_REVIEWED
  -> PROOF_RECONSTRUCTED
  -> NOVELTY_REVIEWED
  -> INDEPENDENTLY_REPRODUCED
  -> VERIFIED_RESULT
```

First-class terminal outcomes are also supported:

`REFUTED`, `KNOWN_RESULT`, `SPECIFICATION_BUG`, `BLOCKED`, `INCONCLUSIVE`.

A change to a frozen mathematical statement is not an ordinary refactor. Reset the object to `SPEC_DRAFT`, freeze again, and redo downstream reviews.

## Review freshness

The system does not treat a review as a timeless checkbox.

- Semantic review is bound to the frozen statement hash.
- Proof-understanding review is bound to the statement and current formalization fingerprint.
- Literature review is bound to the statement and literature/provenance fingerprint.
- Reproduction review is bound to the statement and formalization/environment fingerprint.
- Final review is bound to the complete evidence fingerprint.

Changing relevant evidence after approval blocks later statuses until the review is renewed.

## Axiom audit

`researchctl axioms-all` does not rely solely on Lean's cached `#print axioms` path. It runs a fresh traversal over the elaborated environment with `setExporting false`, applies `axiom_policy` from `research-policy.yaml`, and stores the ordinary `#print axioms` output only as a comparison report. See `docs/LEAN_TRUST.md`.

## Exact Lean dependencies

`researchctl deps-exact H-0042` generates a temporary Lean probe importing the theorem's module and queries the elaborated `ConstantInfo.getUsedConstantsAsSet` for the target and each reachable project declaration. It writes:

```text
reports/dependencies/H-0042.exact.json
reports/dependencies/H-0042.exact.dot
```

Project-to-project edges come from elaborated Lean constants. External/environment constants are retained as leaves so the graph stays finite. This is materially stronger than source-token analysis, while `#print axioms` remains the separate trusted-base audit.

## Repository layout

```text
.github/                     workflows, Issue Form, PR template, rulesets
MathCI/                      smoke-test Lean library; replace/extend it
hypotheses/                  canonical theorem cards
lit/                         reproducible literature-search logs
proofs/                      human proof reconstruction
provenance/                  dependency provenance registry
ablations/                   assumption-ablation experiments
reviews/H-XXXX/              structured human reviews
reports/statements/          frozen theorem snapshots
reports/dependencies/        heuristic + exact dependency DAGs
reports/review-surface/      reviewer triage reports
reports/fingerprints/        evidence fingerprints
reports/environment/         reproducibility environment lock
reports/axioms/              #print axioms logs
reports/packets/             verification ZIPs
src/researchctl/             CI/CD command-line implementation
tests/                       unit/integration tests
docs/                        operating and testing manuals
research-policy.yaml         policy-as-code
```

## Required GitHub checks

The example ruleset requires:

- `protocol-gate`
- `unit-tests`
- `acceptance-suite`
- `workflow-audit`
- `lean-build`
- `axiom-audit`
- `exact-dependencies`

The primary gates run on both `pull_request` and `merge_group`, so they are compatible with GitHub merge queues. GitHub documents that merge queues need the separate `merge_group` event for required Actions checks. See `docs/GITHUB_SETUP.md`.

## LLM red-team security boundary

The PR-side workflow has no model secret. It creates only a bounded text bundle. A separate trusted `workflow_run` workflow checks out the default branch, treats the artifact as data, and calls the model. It never executes PR code with `OPENAI_API_KEY`.

Automated adversarial review is opt-in with the `math:redteam` label and is advisory only.

## Human operating manual

Start with **`docs/HUMAN_MANUAL.tex`** (compiled copy: `docs/HUMAN_MANUAL.pdf`). It connects the mathematical protocol, Git/GitHub workflow, human/agent roles, CI gates, review freshness, literature review, verification packets, and scientific CD/release process.

## Local acceptance tests

```bash
researchctl acceptance
make smoke-ci
```

`researchctl acceptance` is a non-destructive sabotage regression suite for the control plane. `make smoke-ci` checks the local project. The full real-Lean/GitHub acceptance matrix remains in `docs/FIRST_RUN.md`.

See `docs/PATCH_v0.4.2.md` for the acceptance defects fixed in this release.

## Human documentation

The canonical human SOP is `docs/HUMAN_MANUAL.tex`; `docs/HUMAN_MANUAL.pdf` is its compiled reading copy. Markdown documentation is intentionally concise/non-normative where it overlaps the human SOP.

## Agent protocol

Canonical AI role prompts live under `agents/`, not in `docs/PROMPTS.md`. Each role has `SYSTEM.md`, `TASK.md`, and `OUTPUT_SCHEMA.yaml`; cross-role rules live in `agents/common/`.

Useful commands:

```bash
researchctl agent-manifest
researchctl agent-prompt skeptic H-0001
researchctl context-build skeptic H-0001 --profile skeptic-blind
researchctl agent-run-init skeptic H-0001 --model gpt-5.6-sol --profile skeptic-blind
```

`agent-manifest` hashes the canonical prompt set. The protocol hash is included in research fingerprints and verification packets. `agent-run-init` records the role/model/commit/statement/prompt hashes for a concrete AI-assisted step.


## Blind Agent Context Layer

For independent checks, do not give an agent the repository and ask it to ignore irrelevant files. Build an isolated packet instead:

```bash
researchctl context-profiles
researchctl context-build skeptic H-0042 --profile skeptic-blind
researchctl agent-run-init skeptic H-0042 --model <MODEL> --profile skeptic-blind
```

The packet is physically split into `agent-visible/` and `audit-only/`. Only `agent-visible/` may be supplied to the model; `audit-only/` contains `INPUT_MANIFEST.json` and `ALIASES.json` for provenance and must remain hidden. Export a safe model input with:

```bash
researchctl context-export H-0042 <RUN-ID> ./isolated-agent-input
```

The export command copies only the audited `agent-visible/` tree and refuses non-empty destinations. Blind packets intentionally omit global workflow context, other-agent outputs, proof status, novelty claims, and project goals unless a profile explicitly permits them.
