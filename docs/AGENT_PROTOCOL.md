# Agent Protocol v0.4.2

The `agents/` directory is part of the reproducible research environment.

## Why prompts are versioned

An AI-generated mathematical artifact depends not only on model output but also on the instructions that constrained the role. Therefore the project records hashes of all canonical prompt files and includes the protocol hash in result fingerprints and verification packets.

## Separation of roles

No single AI role is permitted to design a theorem, prove it, certify semantic adequacy, certify novelty, and approve merge. The role split is a process-level defense against self-review.

## Prompt changes

Treat changes under `agents/` as research-environment changes:
1. use an `infra/` branch or a dedicated prompt-policy PR;
2. explain the reason for the change;
3. run tests and `researchctl acceptance`;
4. run `researchctl agent-manifest`;
5. expect evidence fingerprints to change;
6. for already reviewed work, decide explicitly which reviews must be repeated.

Never edit recorded prompt hashes to make stale evidence look current. Repeat the affected process instead.
