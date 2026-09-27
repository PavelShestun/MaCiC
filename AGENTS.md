# Instructions for autonomous coding/research agents

Read `docs/AGENT_CONTRACT.md`, `PROTOCOL.md`, and `research-policy.yaml` before modifying research objects.

Non-negotiable rules:

- Never change a frozen mathematical statement merely to make a proof pass.
- A semantic change requires status reset to `SPEC_DRAFT`, a new freeze, and renewed downstream reviews.
- Never set `VERIFIED_RESULT`, novelty `SUPPORTED`, or human sign-off/reviewer identity fields on behalf of humans.
- Never fabricate literature searches, citations, reviewer identities, dates, reproduction evidence, provenance, or ablation results.
- `lake build` success is formal evidence only. Do not infer semantic adequacy, importance, or novelty from it.
- Do not update a review hash simply to make CI green. A new hash means a human re-reviewed the changed evidence.
- Prefer `researchctl deps-exact` over source heuristics when Lean is available, but never describe dependency analysis as a replacement for kernel/axiom checking.
- Treat LLM red-team output as advisory only; it cannot satisfy a human review gate.
- Never weaken GitHub workflow security to expose secrets to PR-controlled code.
- Keep infrastructure changes separate from theorem/definition changes when practical.
- Before proposing merge, run `researchctl validate`, `researchctl workflow-audit`, and the relevant Lean build/audit.

## Canonical role prompts

Role-specific prompts are canonical under `agents/`. Do not duplicate or override them in ad-hoc chat instructions without recording the deviation. Before an AI-assisted research step, use `researchctl agent-prompt ROLE H-ID` and record the run with `researchctl agent-run-init ROLE H-ID --model MODEL`. Prompt protocol hashes are research provenance.
