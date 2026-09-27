# v0.4.2 - Agent Protocol

This release makes AI instructions first-class, versioned research artifacts.

## Added
- canonical `agents/` hierarchy;
- shared cross-role system and output contracts;
- role-specific SYSTEM/TASK/OUTPUT_SCHEMA files;
- `researchctl agent-manifest`;
- `researchctl agent-prompt ROLE H-ID`;
- `researchctl agent-run-init ROLE H-ID --model MODEL`;
- `agent_protocol_sha256` in hypothesis fingerprints;
- role prompt hashes in the agent manifest;
- canonical prompt files, manifest, assembled prompts, and agent-run provenance in verification packets;
- red-team implementation now reads the canonical `agents/red-team/` prompt instead of a hard-coded Python string.

`docs/PROMPTS.md` is now only a quick index. Canonical prompt content is under `agents/`.
