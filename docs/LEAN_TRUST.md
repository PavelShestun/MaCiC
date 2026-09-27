# Lean trust and axiom audit policy

## Why the template does more than `#print axioms`

`#print axioms` remains useful and the template stores its output, but high-assurance CI should not make it the only axiom gate. In September 2026 a Lean issue reported cases where imported inductive declarations could make `Lean.collectAxioms` / `#print axioms` under-report transitive axioms. An earlier issue also concerned axioms referenced by axioms and native evaluation.

Therefore `researchctl axioms-all` performs two audits:

1. **Fresh environment traversal (hard gate).** A generated Lean probe sets `env.setExporting false`, traverses each declaration's elaborated `ConstantInfo.getUsedConstantsAsSet` from scratch, follows types and values, and records every reachable `axiomInfo`. Axioms are checked against `research-policy.yaml`.
2. **Built-in `#print axioms` (diagnostic comparison).** The ordinary Lean report is saved alongside the fresh report.

The default project policy is an allowlist:

```yaml
axiom_policy:
  mode: allowlist
  allow:
    - propext
    - Classical.choice
    - Quot.sound
  deny:
    - sorryAx
```

A project that intentionally assumes a domain-specific axiom must add it explicitly and explain that choice in the research record. Native-evaluation axioms are not on the default allowlist, so `native_decide`-style trust expansion is visible rather than silently accepted.

## Kernel vs audit tooling

A bug in axiom-reporting tooling is not a kernel unsoundness bug. The purpose of the fresh traversal is to make the *audit* robust against memoization/export-table issues while Lean's kernel remains the checker of the proof object itself.

## Independent checking

For publication-grade or adversarial inputs, a project may add an independent checker stage as another required status check. Keep that stage logically separate from Lean build and from the repository governance gates so failures are attributable.
