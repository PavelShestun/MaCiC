# Agent prompts - quick index only

Canonical prompts live under [`agents/`](../agents/). This file is intentionally non-normative.

Roles:
- `agents/formalizer/`
- `agents/skeptic/`
- `agents/semantic-reviewer/`
- `agents/proof-reviewer/`
- `agents/literature-reviewer/`
- `agents/provenance-auditor/`
- `agents/reproducer/`
- `agents/red-team/`
- `agents/merge-gate/`

Every role has:
- `SYSTEM.md` - role-level immutable behavior contract;
- `TASK.md` - reusable task template;
- `OUTPUT_SCHEMA.yaml` - machine-readable output contract.

Cross-role rules are in `agents/common/`.

Generate the cryptographic prompt manifest with:

```bash
researchctl agent-manifest
```

The resulting `reports/agents/manifest.json` is included in verification packets. If this file conflicts with `agents/`, the contents of `agents/` are authoritative.
