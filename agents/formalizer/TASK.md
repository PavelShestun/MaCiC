# Formalizer task template

For hypothesis `{H_ID}`:
1. Read the theorem card, frozen statement snapshot, relevant definitions, and current Lean sources.
2. Verify that the declaration to be proved matches the frozen statement hash before modifying proof code.
3. Attempt a proof without changing definitions, assumptions, quantifiers, domains, or conclusion.
4. If blocked, stop and produce a Statement Change Request describing the minimal semantic change, why it is needed, and how it changes the mathematical claim. Do not implement the semantic change.
5. Name helper lemmas mathematically; document non-obvious Mathlib/external dependencies.
6. Run the available Lean build and repository gates.
7. Return a structured record matching `OUTPUT_SCHEMA.yaml`.
