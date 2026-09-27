#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND="${MACIC_SANDBOX_BACKEND:-auto}"

if [[ "$BACKEND" == "auto" ]]; then
  if [[ "${GITHUB_ACTIONS:-}" == "true" ]]; then
    BACKEND="docker"
  elif command -v bwrap >/dev/null 2>&1; then
    BACKEND="bwrap"
  elif command -v docker >/dev/null 2>&1; then
    BACKEND="docker"
  else
    echo "ERROR: neither bubblewrap nor docker is available" >&2
    exit 2
  fi
fi

case "$BACKEND" in
  bwrap)
    RUNNER="$ROOT/scripts/agent_sandbox.sh"
    ;;
  docker)
    RUNNER="$ROOT/scripts/agent_sandbox_docker.sh"
    ;;
  *)
    echo "ERROR: unknown sandbox backend: $BACKEND" >&2
    exit 2
    ;;
esac

echo "sandbox backend: $BACKEND"

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

"$RUNNER" \
  "$EXPORT_DIR" \
  "$OUTPUT_DIR" \
  -- /bin/sh -eu -c '
    # Expected input.
    test -f /input/STATEMENT.md
    test -f /input/TASK.md

    # Audit-only metadata must not exist.
    test ! -e /input/ALIASES.json
    test ! -e /input/INPUT_MANIFEST.json

    # Host secrets/environment must not cross the boundary.
    test -z "${MACIC_SECRET_SENTINEL:-}"
    test -z "${GH_TOKEN:-}"
    test -z "${GITHUB_TOKEN:-}"
    test -z "${OPENAI_API_KEY:-}"
    test -z "${SSH_AUTH_SOCK:-}"

    # Host checkout / credentials must be absent.
    test ! -e /home/shestun
    test ! -e /root/.ssh
    test ! -e /.git

    # Container/runtime escape surfaces must not be exposed.
    test ! -e /var/run/docker.sock
    test ! -e /run/docker.sock
    test ! -e /github/workspace
    test ! -e /workspace
    test ! -e /host
    test ! -e /mnt/host

    # No effective Linux capabilities.
    if [ -r /proc/self/status ]; then
      capeff="$(grep "^CapEff:" /proc/self/status | tr -s "[:space:]" " " | cut -d " " -f2)"
      test "$capeff" = "0000000000000000"
    fi

    # Input must be immutable.
    if echo X >> /input/TASK.md 2>/dev/null; then
      echo "FAIL: input unexpectedly writable" >&2
      exit 1
    fi

    # Network namespace must expose no external interface.
    if grep -E "^[[:space:]]*(eth|ens|enp)[^:]*:" /proc/net/dev >/dev/null; then
      echo "FAIL: external network interface exists" >&2
      cat /proc/net/dev >&2
      exit 1
    fi

    # Explicit output boundary must be writable.
    echo "sandbox-pass" > /output/sentinel
  '

test "$(cat "$OUTPUT_DIR/sentinel")" = "sandbox-pass"

# Docker additionally promises an immutable container root filesystem.
# Bubblewrap uses an ephemeral private root namespace; it may be writable,
# but those writes are not host-visible or persistent.
if [[ "$BACKEND" == "docker" ]]; then
  "$RUNNER" \
    "$EXPORT_DIR" \
    "$OUTPUT_DIR" \
    -- /bin/sh -eu -c '
      if echo escape > /escape-test 2>/dev/null; then
        echo "FAIL: Docker root filesystem writable" >&2
        exit 1
      fi

      if echo escape > /etc/macic-escape-test 2>/dev/null; then
        echo "FAIL: Docker /etc writable" >&2
        exit 1
      fi
    '

  echo "PASS: Docker root filesystem is read-only"
fi

echo "PASS: execution sandbox isolates filesystem, environment, network, input, and output"
