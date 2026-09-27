# GitHub setup

## 1. CODEOWNERS

Replace every placeholder team/user in `CODEOWNERS` before requiring code-owner approval. Assign different groups where possible for mathematics, Lean/formalization, literature/provenance, and research-infrastructure ownership.

## 2. First workflow run

Push the repository and let `research-gates` report once before making checks mandatory. Required status checks that have never reported in a repository can be awkward to configure and troubleshoot.

## 3. Main ruleset

Inspect `.github/rulesets/main.example.json`, then apply it manually or with:

```bash
scripts/bootstrap_github.sh OWNER/REPO
```

The example requires:

- pull requests;
- stale review dismissal;
- latest-push approval;
- CODEOWNERS review;
- resolved review threads;
- no branch deletion/force-push;
- `protocol-gate`;
- `unit-tests`;
- `acceptance-suite`;
- `workflow-audit`;
- `lean-build`;
- `axiom-audit`;
- `exact-dependencies`.

## 4. Merge queue

Optional. The main workflow listens to `merge_group`, which is required for GitHub Actions status checks used by merge queue.

## 5. Research release environment

Create a GitHub Environment named `research-release` and configure required human reviewers. The manual release workflow uses this environment so a final publication/release action has an explicit human approval boundary.

## 6. LLM red-team configuration

Optional:

- secret: `OPENAI_API_KEY`;
- variable: `MATH_CICD_REDTEAM_MODEL`;
- PR label: `math:redteam`.

The preparation workflow runs without secrets. The trusted consumer checks out the default branch and never executes PR code with the model secret.

## 7. Actions security

`researchctl workflow-audit` rejects `pull_request_target` by default because privileged workflows must not execute untrusted PR code. The audit also warns when Actions are pinned only to version tags rather than immutable commit SHAs. For a high-assurance deployment, replace `@vN` action references with reviewed full commit SHAs and use Dependabot/Renovate to update them deliberately.

## 8. Release/tag governance

Treat tags under `result/H-XXXX/...` as research publication identifiers. Do not rewrite or delete them. If your GitHub plan supports suitable tag rulesets, protect that namespace separately.

## 9. Acceptance test

Follow `docs/FIRST_RUN.md` before declaring the infrastructure operational.


## 10. Team operating procedure

Before using the repository for real research, have all contributors read `docs/HUMAN_MANUAL.md`. The ruleset enforces machine gates; the manual defines the scientific meaning of statuses and human responsibilities.
