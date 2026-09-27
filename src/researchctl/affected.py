from __future__ import annotations

import subprocess
from pathlib import Path

from .model import Repo


def affected_hypotheses(repo: Repo, base: str) -> list[str]:
    p = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=repo.root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or f"git diff failed against {base}")
    paths = [Path(x) for x in p.stdout.splitlines() if x.strip()]
    ids: set[str] = set()
    global_change = False
    global_prefixes = {"src", "scripts", ".github", "templates", "schemas"}
    global_files = {"research-policy.yaml", "pyproject.toml", "lean-toolchain", "lakefile.toml", "lakefile.lean"}
    for path in paths:
        if path.as_posix() in global_files or (path.parts and path.parts[0] in global_prefixes):
            global_change = True
        for part in path.parts:
            if part.startswith("H-"):
                stem = Path(part).stem
                if stem.startswith("H-"):
                    ids.add(stem)
    if global_change:
        ids.update(p.stem for p in (repo.root / "hypotheses").glob("H-*.yaml"))
    return sorted(ids)
