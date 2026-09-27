# Daily operating procedure

For the complete human protocol, role separation, Git/GitHub workflow, CI interpretation and scientific release procedure, read `docs/HUMAN_MANUAL.md`.

## Start a hypothesis

```bash
researchctl new H-0042 "Candidate scaling rigidity theorem"
git switch -c hyp/H-0042-scaling-rigidity
```

Write the informal claim, scope, definitions, and falsification targets before long proof search.

## Freeze the claim

Set `statement.lean_file`, `statement.lean_module`, and `statement.lean_declaration`, then:

```bash
researchctl freeze H-0042
researchctl semantic-diff H-0042 --fail-on-change
researchctl validate
```

The freeze commit should be easy to identify in Git history.

## Formalize and inspect

```bash
lake --no-ansi build
researchctl audit H-0042
researchctl deps H-0042
researchctl deps-exact H-0042
researchctl provenance-init H-0042
researchctl ablate H-0042
researchctl review-surface H-0042
```

`deps` is fast and heuristic. `deps-exact` requires Lean and should be used for serious review/release evidence.

## Initialize reviews

Run this only after the evidence you intend to review is in place:

```bash
researchctl fingerprint H-0042
researchctl review-init H-0042
```

It creates:

```text
semantic.yaml
proof.yaml
literature.yaml
reproduction.yaml
final.yaml
```

The generated hash fields bind each review to the current evidence. If the evidence later changes, regenerate the relevant review hash only after the reviewer actually rechecks the changed material.

## Proof reconstruction

Before `PROOF_RECONSTRUCTED`, complete `proofs/H-0042.md` and the proof review. The proof reviewer should be able to identify the key mathematical transitions, detect circularity/trivialization, and explain which project lemmas contain the genuinely new work.

## Novelty review

Maintain the search log in `lit/H-0042.md` and provenance registry in `provenance/H-0042.yaml`. The literature review must record query families, sources/indexes, citation chasing, proof-fingerprint search, serious candidate prior art, and a bounded conclusion. Agents may collect evidence; they may not self-certify novelty.

## Independent reproduction

Use a clean checkout and the registered toolchain. Generate/commit the environment lock:

```bash
researchctl env-lock
```

The reproducer records the tested commit and current formalization fingerprint. Project policy can require the reproducer to be different from the primary research owner.

## Final packet

```bash
researchctl validate
researchctl fingerprint H-0042
researchctl packet H-0042
```

Do not update a final-review hash merely to make CI green. Updating the hash means the reviewer has rechecked the new evidence.

## LLM red-team review

Local prompt generation does not contact a model:

```bash
researchctl redteam H-0042
```

On GitHub, apply label `math:redteam` to opt in to the split trusted/untrusted workflow. Treat its output as adversarial triage, never as certification.

## Negative results

A refuted, already-known, blocked, or specification-bug hypothesis should usually be merged if the evidence is useful and reproducible. Git history is the research record; do not delete failed hypotheses merely because they did not produce a new theorem.


## Infrastructure regression check

After updating Math CI/CD itself, run `researchctl acceptance` and then `scripts/smoke_ci.sh`. The first tests the governance control plane in temporary repositories; the second exercises the current project and Lean integration when available.
