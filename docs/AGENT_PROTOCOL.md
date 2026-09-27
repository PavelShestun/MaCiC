# Agent Protocol v0.4.3

The `agents/` directory is part of the reproducible research environment. Canonical role prompts and visibility profiles are versioned and hashed.

## Context firewall

Role separation alone is insufficient. For independent stages, an agent MUST NOT receive a full repository checkout plus an instruction to "ignore" unrelated files. Use an isolated context packet built from an explicit visibility profile.

Canonical profiles live under `agents/profiles/`.

```bash
researchctl context-profiles
researchctl context-build skeptic H-0042 --profile skeptic-blind
researchctl context-build proof-reviewer H-0042 --profile proof-blind
researchctl context-build literature-reviewer H-0042 --profile literature-blind
```

A packet is written under `reports/agent-inputs/H-XXXX/<RUN-ID>/` with two physical zones:

- `agent-visible/` — the only files an LLM may receive.
- `audit-only/` — `INPUT_MANIFEST.json`, `ALIASES.json`, and other provenance that must never be sent to the model.

Use `researchctl context-export H-XXXX RUN-ID DEST` to create a clean model-facing directory. Never hand an agent the packet root. The manifest records included artifacts, declared exclusions, the profile hash, statement hash, agent protocol hash, leakage scan result, and an overall context-packet hash.

## Blindness levels

- Role separation: different tasks, but potentially shared context. Weak isolation.
- Output isolation: outputs of other agents are hidden.
- Task blindness: global desired outcome and proof status are hidden.
- Provenance blindness: generator identity, generator reasoning, and other reviews are hidden.
- Goal blindness: only a neutralized local mathematical object is visible.

Profiles should use the strongest level compatible with the task.

## Sanitization

Blind profiles can hide H-IDs, neutralize project-specific identifiers, and redact configured strings/regexes. Sanitization is not a proof that a capable model cannot infer the broader topic. It is a process control that removes direct leakage and anchoring information.

## Leakage scanner

`researchctl context-audit` scans a generated packet for forbidden context markers. The GitHub `blind-context` job builds smoke packets for blind roles and fails if hidden-stage markers leak.

## Agent run provenance

For a blind run:

```bash
researchctl agent-run-init skeptic H-0042 --model <MODEL> --profile skeptic-blind
```

The run record binds the model, commit, frozen statement, agent protocol, visibility profile, context-packet path/hash, and leakage-scan result.

Never "refresh" an old run by editing hashes. Create a new packet and run record.

## Separation of roles

No single AI role is permitted to design a theorem, prove it, certify semantic adequacy, certify novelty, and approve merge. The role split and the context firewall are independent defenses against self-review and anchoring.


## GitHub enforcement

After merging a change that adds a new required agent/context gate, update the already-active repository ruleset explicitly:

```bash
./scripts/update_github_ruleset.sh OWNER/REPO
```

The bootstrap script intentionally does not overwrite an existing ruleset.
