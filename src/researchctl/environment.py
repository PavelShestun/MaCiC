from __future__ import annotations

import datetime
import json
import shutil
import subprocess
from pathlib import Path

from .fingerprint import environment_paths, sha256_file
from .model import Repo


def _version(cmd: list[str]) -> str | None:
    if shutil.which(cmd[0]) is None:
        return None
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=20).strip().splitlines()[0]
    except Exception:
        return None


def build(repo: Repo) -> dict:
    files=[]
    for p in environment_paths(repo):
        files.append({"path": p.relative_to(repo.root).as_posix(), "sha256": sha256_file(p)})
    return {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": sorted(files, key=lambda x:x["path"]),
        "tools": {
            "lean": _version(["lean","--version"]),
            "lake": _version(["lake","--version"]),
            "python": _version(["python","--version"]),
            "git": _version(["git","--version"]),
        },
    }


def write(repo: Repo) -> Path:
    out=repo.root/"reports"/"environment"
    out.mkdir(parents=True,exist_ok=True)
    p=out/"lock.json"
    p.write_text(json.dumps(build(repo),indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return p


def validate(repo: Repo) -> list[str]:
    p=repo.root/"reports"/"environment"/"lock.json"
    if not p.exists(): return ["missing reports/environment/lock.json; run researchctl env-lock in the target environment"]
    try: old=json.loads(p.read_text(encoding="utf-8"))
    except Exception as e: return [f"invalid environment lock: {e}"]
    oldmap={x["path"]:x["sha256"] for x in old.get("files",[])}
    current={x.relative_to(repo.root).as_posix():sha256_file(x) for x in environment_paths(repo)}
    e=[]
    if oldmap!=current: e.append("environment lock is stale; toolchain/configuration files changed")
    return e
