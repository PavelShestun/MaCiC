#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage:
  agent_sandbox.sh INPUT_DIR OUTPUT_DIR -- COMMAND [ARGS...]

Example:
  scripts/agent_sandbox.sh \
    ./isolated-agent-input \
    ./agent-output \
    -- /bin/sh -c 'cat /input/TASK.md'
USAGE
  exit 2
}

[[ $# -ge 4 ]] || usage

INPUT_DIR="$1"
OUTPUT_DIR="$2"
shift 2

[[ "${1:-}" == "--" ]] || usage
shift

command -v bwrap >/dev/null 2>&1 || {
  echo "ERROR: bubblewrap (bwrap) is required" >&2
  exit 2
}

INPUT_DIR="$(realpath "$INPUT_DIR")"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"

[[ -d "$INPUT_DIR" ]] || {
  echo "ERROR: input directory does not exist: $INPUT_DIR" >&2
  exit 2
}

# Never allow the repository itself to be used as the visible input.
if [[ -e "$INPUT_DIR/.git" ]]; then
  echo "ERROR: input contains .git; refusing sandbox launch" >&2
  exit 3
fi

# Known audit-only files must never cross the execution boundary.
for forbidden in \
  INPUT_MANIFEST.json \
  ALIASES.json
do
  if find "$INPUT_DIR" -name "$forbidden" -print -quit | grep -q .; then
    echo "ERROR: forbidden audit metadata in agent-visible input: $forbidden" >&2
    exit 3
  fi
done

args=(
  --die-with-parent
  --new-session

  # New namespaces, including network.
  --unshare-all

  # Minimal virtual filesystem.
  --proc /proc
  --dev /dev
  --tmpfs /tmp
  --tmpfs /run

  # Fake isolated home.
  --dir /home
  --dir /home/agent

  # Only explicit research input is visible.
  --ro-bind "$INPUT_DIR" /input

  # Only explicit result directory is writable/persistent.
  --bind "$OUTPUT_DIR" /output

  --chdir /input

  # Remove inherited host environment.
  --setenv HOME /home/agent
  --setenv USER agent
  --setenv LOGNAME agent
  --setenv LANG C.UTF-8
  --setenv LC_ALL C.UTF-8
  --setenv PATH /usr/local/bin:/usr/bin:/bin
)

# Runtime binaries/libraries are visible read-only.
for path in /usr /bin /sbin /lib /lib64 /usr/local; do
  if [[ -e "$path" ]]; then
    args+=(--ro-bind "$path" "$path")
  fi
done

# Minimal /etc required by some runtimes.
for file in \
  /etc/passwd \
  /etc/group \
  /etc/nsswitch.conf \
  /etc/hosts
do
  if [[ -e "$file" ]]; then
    args+=(--ro-bind "$file" "$file")
  fi
done

exec /usr/bin/env -i \
  bwrap "${args[@]}" -- "$@"
