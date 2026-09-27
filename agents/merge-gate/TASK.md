# Merge-gate task template

For PR/hypothesis `{H_ID}`:
1. Check statement drift, placeholder proofs, invalid Lean references, status transition, axiom policy, evidence freshness, provenance completeness, literature blockers, reproduction, and required human sign-offs.
2. Separate hard blockers from advisory concerns.
3. Return only `BLOCK_MERGE` or `GATES_SATISFIED` as the workflow verdict.
4. `GATES_SATISFIED` means repository policy is satisfied; it is not a scientific endorsement.
