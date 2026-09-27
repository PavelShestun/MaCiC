# v0.4.3.1 — Two-zone Blind Context Hardening

Fixes BUG-006 discovered during manual acceptance.

## Problem

The original v0.4.3 packet colocated `ALIASES.json` and `INPUT_MANIFEST.json` with model-visible files. Passing the whole directory to an agent could reveal the original H-ID, theorem name, module, and audit metadata.

## Fix

- `context-build` now creates `agent-visible/` and `audit-only/`.
- `ALIASES.json` and `INPUT_MANIFEST.json` exist only under `audit-only/`.
- New `researchctl context-export H-ID RUN-ID DEST` exports only `agent-visible/`.
- Export refuses non-empty destinations.
- `context-audit` audits only the model-visible tree and rejects audit-only filenames there.
- Acceptance and unit tests include boundary sabotage checks.

Operational rule: **never give a blind agent the packet root; give only a `context-export` destination or the `agent-visible/` directory.**
