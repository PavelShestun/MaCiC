from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .model import Repo


def _version(cmd: list[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=20).strip().splitlines()[0]
    except Exception as e:
        return f"ERROR: {e}"


def run(repo: Repo) -> dict:
    tools = {}
    for name, cmd in {
        "git": ["git", "--version"],
        "python": ["python", "--version"],
        "lake": ["lake", "--version"],
        "lean": ["lean", "--version"],
    }.items():
        tools[name] = {"found": shutil.which(cmd[0]) is not None, "version": _version(cmd) if shutil.which(cmd[0]) else "MISSING"}
    files = {}
    for name in ["research-policy.yaml", "pyproject.toml", "lean-toolchain", "lakefile.toml", ".github/workflows/research-gates.yml"]:
        files[name] = (repo.root / name).exists()
    return {"tools": tools, "required_files": files, "ready_for_python_ci": tools["git"]["found"] and tools["python"]["found"], "ready_for_lean_ci": tools["lake"]["found"] and tools["lean"]["found"]}
