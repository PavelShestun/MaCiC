#!/usr/bin/env bash
set -euo pipefail
repo="${1:-}"
file="${2:-.github/rulesets/main.example.json}"
name="${3:-mathematics-main}"
if [[ -z "$repo" ]]; then
  echo "usage: scripts/update_github_ruleset.sh OWNER/REPO [ruleset-json] [ruleset-name]" >&2
  exit 2
fi
command -v gh >/dev/null || { echo "gh CLI required" >&2; exit 2; }
[[ -f "$file" ]] || { echo "ruleset file not found: $file" >&2; exit 2; }
python -m json.tool "$file" >/dev/null
id="$(gh api "repos/$repo/rulesets" --jq ".[] | select(.name==\"$name\") | .id" | head -n1 || true)"
if [[ -z "$id" ]]; then
  echo "ruleset '$name' not found; run bootstrap_github.sh first" >&2
  exit 1
fi
echo "Updating ruleset $name (id=$id) in $repo from $file"
gh api --method PUT "repos/$repo/rulesets/$id" --input "$file" >/dev/null
echo "Ruleset updated."
gh api "repos/$repo/rulesets/$id" --jq '{id,name,enforcement,required_checks: [.rules[] | select(.type=="required_status_checks") | .parameters.required_status_checks[].context]}'
