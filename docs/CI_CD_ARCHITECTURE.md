# Mathematics CI/CD architecture

## Trust model

The system intentionally splits trust into layers:

1. **Lean kernel/build layer** - verifies elaborated proof objects relative to encoded definitions, imports, and axioms.
2. **Repository invariant layer** - prevents placeholder proofs, statement drift, illegal research-state transitions, stale evidence, and incomplete records.
3. **Human semantic layer** - checks that formal definitions and theorem statements mean what the project claims they mean.
4. **Human proof-understanding layer** - reconstructs the mathematical mechanism rather than accepting a large generated proof as an opaque artifact.
5. **Provenance/novelty layer** - checks prior art, dependency origin, and claim language.
6. **Independent reproduction layer** - reruns the result from a clean checkout/environment and verifies the current evidence object.

No layer is allowed to silently stand in for another.

## Hard verification plane

Machine-checkable merge/release blockers include:

- stable `H-ID` and valid status transition;
- frozen Lean declaration hash and snapshot;
- no `sorry` / `admit` outside comments/strings;
- successful Lean build;
- theorem-level axiom audit;
- required structured reviews;
- review freshness fingerprints;
- provenance policy;
- optional assumption-ablation policy;
- exact elaborated dependency report before final verification;
- environment lock before final verification;
- minimum distinct human signers;
- allowed final novelty status.

## Analysis plane

Advisory tools include:

- semantic statement diff;
- source-level dependency graph for rapid local iteration;
- exact dependency graph for reviewer navigation;
- review-surface prioritization;
- ablation experiments;
- adversarial LLM review.

These tools reduce search cost. They do not supply the human scientific judgment required for semantic adequacy, importance, equivalence to the literature, or novelty.

## Exact dependency architecture

`deps-exact` imports the registered Lean module and queries the elaborated environment. For each project declaration visible from that module it calls `ConstantInfo.getUsedConstantsAsSet`, then traverses project-to-project edges reachable from the headline theorem. Non-project environment constants are retained as leaves.

This gives exact constant usage for the elaborated declaration bodies/types while bounding traversal to the project's research surface. It is separate from the axiom audit: dependency navigation answers "what does this proof use?" while `#print axioms` answers "what trusted axioms does this result depend on?".

## Review freshness architecture

A review is valid only for the evidence version it examined.

- semantic -> statement SHA-256;
- proof-understanding -> statement + formalization fingerprint;
- literature -> statement + literature/provenance fingerprint;
- reproduction -> statement + formalization/environment fingerprint;
- final -> complete evidence fingerprint.

This prevents a common failure mode where a review remains marked PASS after the underlying proof, literature search, toolchain, or provenance record changes.

## Release architecture

`research-release.yml` is manual and should be protected by a GitHub Environment requiring human approval. It revalidates the repository, requires `VERIFIED_RESULT`, rebuilds Lean, reruns the axiom audit, re-extracts exact dependencies, checks committed dependency evidence for drift, refreshes review-surface/fingerprint reports, builds a verification packet, and refuses to overwrite an existing research release tag.

## Secret boundary

Untrusted PR code must never execute in a job that has model secrets or write-capable repository credentials. The red-team feature uses two workflows:

- unprivileged PR preparation, no secrets;
- trusted `workflow_run` consumer from the default branch, artifact treated only as bounded text.

The repository's own workflow audit rejects `pull_request_target` by default and flags weaker action pinning as a warning.


## v0.4.1 control-plane regression gate

`acceptance-suite` runs `researchctl acceptance` on every PR. It deliberately constructs synthetic bad states in temporary directories and requires the governance code to reject them. It complements unit tests: unit tests check functions, while acceptance tests check expected control behavior. Real Lean/GitHub sabotage tests remain in `docs/FIRST_RUN.md`.

For team operating procedure and interpretation of each gate, see `docs/HUMAN_MANUAL.md`.
