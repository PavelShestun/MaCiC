#!/usr/bin/env bash
set -euo pipefail

python -m pytest -q
researchctl acceptance
researchctl agent-manifest
researchctl workflow-audit
researchctl validate

if command -v lake >/dev/null 2>&1 && { [ -f lakefile.toml ] || [ -f lakefile.lean ]; }; then
  lake --no-ansi build
  researchctl axioms-all
  researchctl deps-exact-all
  researchctl env-lock
else
  echo "Lean toolchain unavailable: skipping Lean-only smoke checks" >&2
fi

echo "Math CI/CD smoke test passed"
