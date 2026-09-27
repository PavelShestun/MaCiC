# Human Manual - quick note

The **canonical human operating manual is LaTeX**:

- `docs/HUMAN_MANUAL.tex` - normative editable source
- `docs/HUMAN_MANUAL.pdf` - compiled reading copy

This Markdown file is intentionally non-normative and short.

Daily local checks:

```bash
pytest -q
researchctl acceptance
researchctl validate
researchctl workflow-audit
lake build
researchctl axioms-all
researchctl deps-exact-all
```

For one hypothesis:

```bash
researchctl semantic-diff H-0042
researchctl fingerprint H-0042
researchctl report H-0042
researchctl audit H-0042
```

Do not use this note as a substitute for the LaTeX SOP. In case of disagreement, follow `docs/HUMAN_MANUAL.tex` together with `research-policy.yaml` and enforced CI rules.
