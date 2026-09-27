# Agent Protocol (canonical prompt source)

This directory is the canonical, version-controlled source of prompts for AI agents used in the research workflow.

- `common/SYSTEM.md` applies to every agent role.
- `common/OUTPUT_CONTRACT.md` defines cross-role evidence and provenance requirements.
- Each role directory contains `SYSTEM.md`, `TASK.md`, and `OUTPUT_SCHEMA.yaml`.
- `researchctl agent-manifest` computes SHA-256 hashes and writes `reports/agents/manifest.json`.
- Verification packets include the manifest so a result records which prompt protocol governed AI work.

`docs/PROMPTS.md` is only a short index. If it conflicts with this directory, this directory wins.

Agents do not self-certify novelty, mathematical significance, or final verification. Human sign-off and CI policy remain authoritative.
