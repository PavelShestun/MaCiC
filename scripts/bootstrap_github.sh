#!/usr/bin/env bash
set -euo pipefail
repo="${1:-}"
if [[ -z "$repo" ]]; then echo "usage: scripts/bootstrap_github.sh OWNER/REPO" >&2; exit 2; fi
command -v gh >/dev/null || { echo "gh CLI required" >&2; exit 2; }

echo "Creating/updating standard labels in $repo"
while IFS='|' read -r name color description; do
  gh label create "$name" --repo "$repo" --color "$color" --description "$description" --force >/dev/null
done <<'LABELS'
math:redteam|B60205|Opt in to automated adversarial mathematics review
math:hypothesis|1D76DB|Research hypothesis / theorem object
math:blocked|D93F0B|Research object is blocked or inconclusive
math:verified|0E8A16|Human-governed verified result; never set by an agent alone
math:negative-result|6F42C1|Refuted, known, or specification-bug outcome worth preserving
LABELS

existing="$(gh api "repos/$repo/rulesets" --jq '.[] | select(.name=="mathematics-main") | .id' | head -n1 || true)"
if [[ -n "$existing" ]]; then
  echo "Ruleset mathematics-main already exists as id=$existing; not overwriting it."
  echo "Inspect/update it manually or delete it before re-running bootstrap."
else
  echo "Applying example ruleset to $repo"
  gh api --method POST "repos/$repo/rulesets" --input .github/rulesets/main.example.json >/dev/null
fi

echo "Bootstrap complete. Next: replace CODEOWNERS placeholders, configure research-release environment, and run docs/FIRST_RUN.md."
