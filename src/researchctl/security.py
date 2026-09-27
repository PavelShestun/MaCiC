from __future__ import annotations

from pathlib import Path

from .model import Repo


def audit_workflows(repo: Repo) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    wdir = repo.root / ".github" / "workflows"
    if not wdir.exists():
        return ["missing .github/workflows"], warnings
    for p in sorted(list(wdir.glob("*.yml")) + list(wdir.glob("*.yaml"))):
        txt = p.read_text(encoding="utf-8")
        rel = p.relative_to(repo.root)
        if "pull_request_target:" in txt:
            errors.append(f"{rel}: pull_request_target is forbidden by default; use privilege separation instead")
        if "workflow_run:" in txt:
            risky = [
                "github.event.workflow_run.head_sha",
                "github.event.workflow_run.head_branch",
                "refs/pull/",
            ]
            if "actions/checkout" in txt and any(x in txt for x in risky):
                errors.append(f"{rel}: workflow_run checks out a potentially untrusted head ref")
        if "permissions:" not in txt:
            warnings.append(f"{rel}: no explicit permissions block")
        if "uses: actions/checkout@" in txt and "uses: actions/checkout@v" in txt:
            warnings.append(f"{rel}: GitHub Action is tag-pinned, not immutable-SHA-pinned")
    return errors, warnings
