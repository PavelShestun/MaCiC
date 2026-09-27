# Semantic review task template

For `{H_ID}`:
1. Translate the frozen Lean statement and every project-specific definition used by it into ordinary mathematics.
2. Compare them against the theorem card's intended claim.
3. Check hidden trivialization, vacuity, domain mismatches, quantifier changes, implicit typeclass assumptions, and accidental stronger assumptions.
4. Identify any mismatch precisely by declaration/file.
5. Output PASS only if the formal statement/definitions faithfully encode the intended claim within the reviewed scope. This is not a novelty or proof-understanding approval.
