#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "usage: agent_sandbox_docker.sh INPUT_DIR OUTPUT_DIR -- COMMAND [ARGS...]" >&2
  exit 2
}

[[ $# -ge 4 ]] || usage

INPUT_DIR="$1"
OUTPUT_DIR="$2"
shift 2

[[ "${1:-}" == "--" ]] || usage
shift

command -v docker >/dev/null 2>&1 || {
  echo "ERROR: docker is required" >&2
  exit 2
}

INPUT_DIR="$(realpath "$INPUT_DIR")"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(realpath "$OUTPUT_DIR")"

[[ -d "$INPUT_DIR" ]] || {
  echo "ERROR: input directory does not exist: $INPUT_DIR" >&2
  exit 2
}

if [[ -e "$INPUT_DIR/.git" ]]; then
  echo "ERROR: input contains .git" >&2
  exit 3
fi

for forbidden in INPUT_MANIFEST.json ALIASES.json; do
  if find "$INPUT_DIR" -name "$forbidden" -print -quit | grep -q .; then
    echo "ERROR: forbidden audit metadata in input: $forbidden" >&2
    exit 3
  fi
done

IMAGE="${MACIC_SANDBOX_IMAGE:-debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251}"
UID_HOST="$(id -u)"
GID_HOST="$(id -g)"

exec docker run --rm \
  --network none \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --pids-limit 64 \
  --memory 512m \
  --cpus 1 \
  --user "${UID_HOST}:${GID_HOST}" \
  --tmpfs "/tmp:rw,nosuid,nodev,noexec,size=64m,uid=${UID_HOST},gid=${GID_HOST}" \
  --tmpfs "/home/agent:rw,nosuid,nodev,noexec,size=16m,uid=${UID_HOST},gid=${GID_HOST}" \
  --mount "type=bind,src=${INPUT_DIR},dst=/input,readonly" \
  --mount "type=bind,src=${OUTPUT_DIR},dst=/output" \
  --workdir /input \
  --env HOME=/home/agent \
  --env USER=agent \
  --env LOGNAME=agent \
  --env LANG=C.UTF-8 \
  --env LC_ALL=C.UTF-8 \
  --env PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  "$IMAGE" \
  "$@"
