# v0.4.3 — Blind Agent Context Layer

This release adds enforceable context isolation for independent AI-assisted review stages.

## Added

- `agents/profiles/*.yaml` visibility profiles.
- `researchctl context-profiles` to validate/hash profiles.
- `researchctl context-build ROLE H-ID --profile PROFILE` to compile a minimal isolated packet.
- `researchctl context-audit H-ID PATH` to scan a packet for forbidden context leakage.
- `researchctl agent-run-init ... --profile PROFILE` to bind an agent run to the exact context packet.
- `INPUT_MANIFEST.json` with included artifacts, declared exclusions, sanitization, leakage scan, and packet SHA-256.
- `blind-context` GitHub required check.
- Visibility-profile hashes included in the agent protocol hash and verification packet.

## Security / scientific intent

Blind review is enforced by *not providing* the full repository. A prompt that merely says "ignore other stages" is not considered isolation. Independent agents should receive only the generated packet, preferably in a separate working directory or API call without repository tools.

The system guarantees direct-context control, not epistemic impossibility: an agent may still infer domain or intent from the mathematical content itself.
