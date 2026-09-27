# v0.4.2 test results

Local QA completed before packaging:

- Python compile: PASS
- unit/integration tests: 19/19 PASS
- built-in sabotage acceptance suite: PASS
- repository validation: PASS
- canonical agent protocol manifest generation: PASS
- assembled role prompt generation: PASS
- agent-run provenance record generation: PASS
- verification packet includes agent protocol artifacts: PASS
- workflow YAML parse: PASS
- ruleset JSON parse: PASS
- shell syntax: PASS
- HUMAN_MANUAL.tex compilation: PASS (15 rendered pages)
- PDF visual QA of the new agent-protocol section: PASS

The local runtime used for this packaging pass does not provide the target project's Lean toolchain; Lean-only acceptance remains a GitHub/local-project test as documented in FIRST_RUN.md. Earlier v0.4 acceptance on the user's environment confirmed Lean 4.34.1 build, fresh axiom traversal, and exact dependency extraction.

# GitHub End-to-End Acceptance Report

Date: 2026-09-27

Repository: `PavelShestun/MaCiC`

Tested version: Math CI/CD v0.4.2

## Summary

The MaCiC control plane was tested locally and on real GitHub-hosted runners.

The objective of this acceptance run was not merely to verify that the happy-path CI pipeline is green, but to intentionally introduce invalid mathematical/research states and confirm that the corresponding gates reject them.

Final result:

- Local unit/integration tests: PASS
- Local sabotage regression suite: PASS
- Lean build: PASS
- Fresh axiom traversal: PASS
- Exact Lean dependency extraction: PASS
- Agent protocol manifest: PASS
- GitHub baseline CI: PASS
- Pull-request sabotage tests: PASS
- Server-side GitHub ruleset enforcement: PASS

The repository ruleset `mathematics-main` is active on the default branch.

---

## Local baseline

The following commands were successfully exercised:

```text
python -m pytest -q
researchctl acceptance
researchctl validate
lake build
researchctl axioms-all
researchctl deps-exact-all
researchctl agent-manifest
researchctl workflow-audit

# GitHub End-to-End Acceptance Report

Date: 2026-09-27

Repository: `PavelShestun/MaCiC`

Tested version: Math CI/CD v0.4.2

## Summary

The MaCiC control plane was tested locally and on real GitHub-hosted runners.

The objective of this acceptance run was not merely to verify that the happy-path CI pipeline is green, but to intentionally introduce invalid mathematical/research states and confirm that the corresponding gates reject them.

Final result:

- Local unit/integration tests: PASS
- Local sabotage regression suite: PASS
- Lean build: PASS
- Fresh axiom traversal: PASS
- Exact Lean dependency extraction: PASS
- Agent protocol manifest: PASS
- GitHub baseline CI: PASS
- Pull-request sabotage tests: PASS
- Server-side GitHub ruleset enforcement: PASS

The repository ruleset `mathematics-main` is active on the default branch.

---

## Local baseline

The following commands were successfully exercised:

```text
python -m pytest -q
researchctl acceptance
researchctl validate
lake build
researchctl axioms-all
researchctl deps-exact-all
researchctl agent-manifest
researchctl workflow-audit

Observed result:
19 tests passed

acceptance:
PASS: baseline passes
PASS: sorry is rejected
PASS: bad Lean references fail validate
PASS: frozen statement drift is rejected
PASS: proof change makes proof review stale

researchctl validate:
All research gates passed.

lake build:
Build completed successfully.

axiom audit:
H-0001 fresh axioms: []

exact dependencies:
exact dependency reports generated successfully

GitHub baseline
A clean push to main was tested on GitHub-hosted runners.
The following jobs completed successfully:
protocol-gate       PASS
unit-tests          PASS
acceptance-suite    PASS
agent-protocol      PASS
workflow-audit      PASS
lean-build          PASS
axiom-audit         PASS
exact-dependencies  PASS
research-summary    PASS

Produced artifacts included:
axiom-audit
agent-protocol-manifest
exact-mathematics-analysis

Sabotage test 1: placeholder proof
An intentionally invalid theorem containing:
theorem intentionally_bad : True := by
  sorry

was submitted through a pull request.
Observed behavior:
lean-build        PASS
protocol-gate     FAIL

The failure was caused by the repository-wide placeholder-proof policy.
Conclusion:
A Lean build that succeeds with sorry is not sufficient to pass MaCiC.
Status: PASS
Sabotage test 2: frozen statement drift
The frozen theorem
theorem identity_example (n : Nat) : n = n

was changed to:
theorem identity_example (n : Nat) (h : True) : n = n

The proof still compiled.
Observed behavior:
lean-build        PASS
protocol-gate     FAIL

The gate reported:
FROZEN_STATEMENT_DRIFT

with different expected and current statement SHA-256 hashes.
Conclusion:
An agent or developer cannot silently weaken or otherwise modify a frozen theorem statement without triggering re-review.
Status: PASS
Sabotage test 3: unauthorized custom axiom
The following declarations were introduced:
axiom Magic : False

theorem bad_axiom : False :=
  Magic

Local fresh axiom traversal reported:
H-0002 fresh axioms: ['MathCI.Magic']
AXIOM POLICY FAILED

Standard Lean diagnostic also reported:
'MathCI.bad_axiom' depends on axioms: [MathCI.Magic]

The GitHub pull request produced an axiom-audit failure.
Conclusion:
Unauthorized extensions of the trusted axiom base are detected and rejected.
Status: PASS
Sabotage test 4: stale proof review
A proof-understanding review and reproduction review were bound to a formalization fingerprint.
The theorem statement was left unchanged while the proof implementation was changed.
Observed behavior:
statement_changed: false

but the formalization/evidence fingerprint changed.
After advancing the object to a status where proof review is required:
researchctl validate

reported:
proof review is stale; formalization/environment changed

Conclusion:
Review approval is not treated as a timeless checkbox. A relevant proof change invalidates downstream review evidence.
Status: PASS
BUG-004: isolated GitHub job missing Lean build
Symptom
The first GitHub axiom-audit run failed with:
unknown module prefix 'MathCI'

although the separate lean-build job was green.
Root cause
GitHub Actions jobs execute on isolated runners.
The dependency:
needs: lean-build

controls execution order but does not transfer the previous job's filesystem or .lake/build directory.
The axiom-audit job attempted to inspect elaborated Lean modules before building them on its own runner.
Fix
The job was changed to run:
lake --no-ansi build

before:
researchctl axioms-all

Verification
A subsequent clean GitHub baseline completed:
axiom-audit PASS

Status: FIXED AND VERIFIED
BUG-005: stale .olean cache in exact dependency analysis
Symptom
During the custom-axiom pull-request test:
axiom-audit

correctly saw:
MathCI.Magic
MathCI.bad_axiom

while:
exact-dependencies

reported that these declarations were absent from the imported environment.
Root cause
The GitHub cache contained both:
.lake/packages
.lake/build

but its key depended only on environment/configuration files and not on Lean source contents.
A source-changing pull request could therefore restore .olean files compiled from an older revision.
Risk
This could produce a plausible but stale elaborated dependency report.
For a mathematical research CI system, this is unacceptable because the dependency evidence could refer to a different proof than the current source tree.
Fix
The cache was changed to retain only:
.lake/packages

The current checkout is rebuilt inside the exact-dependencies job before dependency extraction.
Verification
The following clean main GitHub run completed successfully:
protocol-gate       PASS
unit-tests          PASS
acceptance-suite    PASS
agent-protocol      PASS
workflow-audit      PASS
lean-build          PASS
axiom-audit         PASS
exact-dependencies  PASS
research-summary    PASS

Status: FIXED AND VERIFIED
Server-side merge enforcement
The repository ruleset:
mathematics-main

was activated for the default branch.
Required checks:
protocol-gate
unit-tests
acceptance-suite
agent-protocol
workflow-audit
lean-build
axiom-audit
exact-dependencies

An intentionally failing pull request was created after activation.
Observed:
mergeStateStatus: BLOCKED

Attempting:
gh pr merge --squash

returned:
the base branch policy prohibits the merge

Therefore the scientific gates are not merely advisory CI output; GitHub server-side policy prevents an invalid pull request from being merged into main.
Status: PASS
Current trust statement
As of this acceptance run, MaCiC has demonstrated the following properties:
1. A successful Lean build alone cannot bypass the research protocol.
2. Placeholder proofs are rejected.
3. Frozen theorem statements cannot silently drift.
4. Unauthorized axioms are rejected.
5. Review evidence is invalidated after relevant changes.
6. Exact dependency analysis is generated from the current rebuilt Lean source rather than stale build artifacts.
7. Agent prompt protocol versions are cryptographically fingerprinted.
8. Required mathematical and infrastructure checks execute on GitHub-hosted runners.
9. Failed required checks cause GitHub to block merge into the protected default branch.
This acceptance report validates the control infrastructure only.
It does not imply that any particular mathematical theorem is:
- semantically appropriate,
- mathematically important,
- novel,
- independently reproduced,
- or publication-ready.
Those conclusions remain subject to the theorem-specific research workflow and human review protocol.
Known hardening items
The following items remain for production hardening:
1. Replace ubuntu-latest with an explicitly pinned runner image, preferably ubuntu-24.04.
2. Update GitHub Actions that still trigger Node.js 20 deprecation warnings.
3. Pin third-party GitHub Actions to immutable commit SHA values.
4. Configure a multi-person production ruleset when independent reviewers are available.
5. Configure the protected research-release environment.
6. Continue expanding the automated acceptance suite as new failure modes are discovered.
