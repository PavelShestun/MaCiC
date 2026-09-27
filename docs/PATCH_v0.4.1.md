# v0.4.1 acceptance-hardening patch

This patch is based on defects found during live acceptance testing of v0.4.0.

## Fixed

### BUG-001 - invalid Lean references could pass `validate` at early statuses

`researchctl validate` now performs referential-integrity checks whenever any Lean reference is supplied, including at `CANDIDATE`:

- `lean_file` exists and ends in `.lean`;
- `lean_module` matches the file path convention;
- `lean_declaration` is extractable from the declared file.

Exact environment resolution is still confirmed by Lean jobs.

### BUG-002 - `freeze` / `semantic-diff` could leak Python tracebacks

Both commands now emit controlled diagnostics and explain the three distinct Lean reference fields.

### BUG-003 - `report` displayed `pass` without review freshness

`researchctl report` now reports `PASS / VALID` or `PASS / STALE` independently of current lifecycle enforcement. This makes stale approvals visible before they become mandatory gates.

### Improvement - domain fingerprints are visible

`researchctl fingerprint H-XXXX` now prints:

- statement SHA-256;
- formalization SHA-256;
- literature/provenance SHA-256;
- environment SHA-256;
- complete evidence SHA-256.

### Improvement - built-in sabotage regression suite

`researchctl acceptance` is non-destructive and tests core governance regressions in temporary repositories:

- baseline;
- `sorry` rejection;
- invalid Lean-reference rejection;
- frozen statement drift;
- stale proof review after evidence change.

The GitHub workflow now exposes this as required check `acceptance-suite`.

## Still tested separately with real Lean/GitHub

The built-in temporary acceptance suite does not replace the full first-run test. Real runner tests remain required for:

- custom axiom injection;
- transitive custom axiom injection;
- exact elaborated dependency extraction;
- release workflow and GitHub rulesets.

See `docs/FIRST_RUN.md`.
