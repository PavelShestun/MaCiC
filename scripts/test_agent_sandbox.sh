#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

command -v bwrap >/dev/null 2>&1 || {
  echo "ERROR: bubblewrap is required" >&2
  exit 2
}

RUN_ID="SANDBOX-CI"
EXPORT_DIR="$(mktemp -d)"
OUTPUT_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$EXPORT_DIR" "$OUTPUT_DIR"
  rm -rf "reports/agent-inputs/H-0001/$RUN_ID"
}
trap cleanup EXIT

researchctl context-build skeptic H-0001 \
  --profile skeptic-blind \
  --run-id "$RUN_ID" >/dev/null

researchctl context-export \
  H-0001 \
  "$RUN_ID" \
  "$EXPORT_DIR" >/dev/null

test -f "$EXPORT_DIR/STATEMENT.md"
test -f "$EXPORT_DIR/TASK.md"
test ! -e "$EXPORT_DIR/ALIASES.json"
test ! -e "$EXPORT_DIR/INPUT_MANIFEST.json"

export MACIC_SECRET_SENTINEL="MUST_NOT_ENTER_SANDBOX"

scripts/agent_sandbox.sh \
  "$EXPORT_DIR" \
  "$OUTPUT_DIR" \
  -- /bin/sh -eu -c '
    test -f /input/STATEMENT.md
    test -f /input/TASK.md

    test ! -e /input/ALIASES.json
    test ! -e /input/INPUT_MANIFEST.json

    test -z "${MACIC_SECRET_SENTINEL:-}"
    test -z "${GH_TOKEN:-}"
    test -z "${GITHUB_TOKEN:-}"
    test -z "${OPENAI_API_KEY:-}"
    test -z "${SSH_AUTH_SOCK:-}"

    test ! -e /home/shestun
    test ! -e /root/.ssh
    test ! -e /home/agent/.ssh
    test ! -e /.git

    if echo X >> /input/TASK.md 2>/dev/null; then
      echo "FAIL: input unexpectedly writable" >&2
      exit 1
    fi

    if curl -fsS --connect-timeout 2 https://github.com >/dev/null 2>&1; then
      echo "FAIL: network unexpectedly reachable" >&2
      exit 1
    fi

    echo "sandbox-pass" > /output/sentinel
  '

test "$(cat "$OUTPUT_DIR/sentinel")" = "sandbox-pass"

echo "PASS: execution sandbox isolates filesystem, environment, network, input, and output"
