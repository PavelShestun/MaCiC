# Research statuses

## Main verification path

- `CANDIDATE`: registered idea; no correctness or novelty claim.
- `SPEC_DRAFT`: statement and definitions are being stabilized.
- `SPEC_FROZEN`: exact Lean declaration header is hashed; semantic drift is now gated.
- `FORMALIZED`: proof exists and the Lean project builds, but semantics are not yet signed off.
- `SEMANTIC_REVIEWED`: a human reviewer passed the intended-semantics review for the current frozen hash.
- `PROOF_RECONSTRUCTED`: the mathematical proof has been compressed/reconstructed for human understanding.
- `NOVELTY_REVIEWED`: reproducible literature/provenance review passed; this is still evidence, not an automatic novelty oracle.
- `INDEPENDENTLY_REPRODUCED`: an independent reviewer reproduced the result for the current frozen hash.
- `VERIFIED_RESULT`: all project policy gates and human sign-offs are complete.

## Terminal outcomes

- `REFUTED`: a valid counterexample or contradiction to the hypothesis was established.
- `KNOWN_RESULT`: the claim is materially covered by prior work.
- `SPECIFICATION_BUG`: the formal statement does not encode the intended research claim.
- `BLOCKED`: progress is prevented by a documented dependency or verification obstacle.
- `INCONCLUSIVE`: investigation ended without a justified stronger conclusion.

A changed frozen statement must return to `SPEC_DRAFT`; downstream reviews no longer apply to the new claim.
