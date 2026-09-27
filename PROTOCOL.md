# Operational Protocol

## Gate 0 - Candidate registration
A hypothesis receives an H-ID and theorem card before proof search begins.

## Gate 1 - Specification freeze
The intended mathematical statement, Lean declaration name, assumptions and definitions are frozen. Any later semantic change requires a change record and resets downstream review statuses.

## Gate 2 - Formal verification
Lean builds from a clean environment. `sorry`, `admit`, and project-local axioms are prohibited unless explicitly whitelisted as research assumptions.

## Gate 3 - Semantic review
A human reviewer compares the Lean statement with the mathematical statement and verifies that assumptions/definitions do not contain the desired conclusion.

## Gate 4 - Proof reconstruction
The formal proof is compressed into a human-readable dependency graph and proof sketch. Key nontrivial transitions are identified.

## Gate 5 - Adversarial review
A separate reviewer or agent attempts counterexamples, assumption removal, degenerate models, circularity detection and alternative reductions.

## Gate 6 - Literature review
Search is designed to falsify novelty. Record databases, queries, dates, candidate prior art, equivalence analysis, backward/forward citation chasing and unresolved similarities.

## Gate 7 - Independent reproduction
A person or agent who did not author the proof rebuilds the project and reconstructs the core argument from the frozen statement and evidence packet.

## Gate 8 - Final sign-off
`VERIFIED_RESULT` requires named human sign-off for specification, mathematics, formalization and novelty review.
