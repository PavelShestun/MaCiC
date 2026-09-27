from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

from .model import Repo

CANONICAL_NAMES = {"SYSTEM.md", "TASK.md", "OUTPUT_SCHEMA.yaml"}
EXPECTED_ROLES = ("formalizer", "skeptic", "semantic-reviewer", "proof-reviewer", "literature-reviewer", "provenance-auditor", "reproducer", "red-team", "merge-gate")
COMMON_NAMES = {"SYSTEM.md", "OUTPUT_CONTRACT.md"}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_prompt_paths(repo: Repo) -> list[Path]:
    root = repo.root / "agents"
    if not root.exists():
        return []
    paths: list[Path] = []
    common = root / "common"
    if common.exists():
        paths.extend(p for p in common.iterdir() if p.is_file() and p.name in COMMON_NAMES)
    for role in sorted(p for p in root.iterdir() if p.is_dir() and p.name != "common"):
        paths.extend(p for p in role.iterdir() if p.is_file() and p.name in CANONICAL_NAMES)
    return sorted(paths, key=lambda p: p.relative_to(repo.root).as_posix())


def build_agent_manifest(repo: Repo) -> dict:
    files = []
    role_rows: dict[str, list[dict]] = {}
    for p in canonical_prompt_paths(repo):
        rel = p.relative_to(repo.root).as_posix()
        row = {"path": rel, "sha256": _sha256_bytes(p.read_bytes())}
        files.append(row)
        parts = Path(rel).parts
        role = "common" if len(parts) > 1 and parts[1] == "common" else (parts[1] if len(parts) > 1 else "unknown")
        role_rows.setdefault(role, []).append(row)

    role_hashes: dict[str, str] = {}
    for role, rows in sorted(role_rows.items()):
        raw = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        role_hashes[role] = _sha256_bytes(raw)

    canonical = {"files": files, "role_hashes": role_hashes}
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "protocol_version": (repo.root / "VERSION").read_text(encoding="utf-8").strip() if (repo.root / "VERSION").exists() else "",
        "files": files,
        "role_hashes": role_hashes,
        "agent_protocol_sha256": _sha256_bytes(raw),
    }


def write_agent_manifest(repo: Repo) -> Path:
    data = build_agent_manifest(repo)
    data["generated_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    out = repo.root / "reports" / "agents"
    out.mkdir(parents=True, exist_ok=True)
    p = out / "manifest.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def role_prompt(repo: Repo, role: str) -> dict[str, str]:
    root = repo.root / "agents"
    common_system = (root / "common" / "SYSTEM.md").read_text(encoding="utf-8")
    output_contract = (root / "common" / "OUTPUT_CONTRACT.md").read_text(encoding="utf-8")
    role_dir = root / role
    if not role_dir.exists():
        raise FileNotFoundError(f"unknown agent role: {role}")
    return {
        "common_system": common_system,
        "output_contract": output_contract,
        "system": (role_dir / "SYSTEM.md").read_text(encoding="utf-8"),
        "task": (role_dir / "TASK.md").read_text(encoding="utf-8"),
        "schema": (role_dir / "OUTPUT_SCHEMA.yaml").read_text(encoding="utf-8"),
    }


def protocol_errors(repo: Repo) -> list[str]:
    errors: list[str] = []
    root = repo.root / "agents"
    for rel in (Path("common/SYSTEM.md"), Path("common/OUTPUT_CONTRACT.md")):
        if not (root / rel).exists():
            errors.append(f"missing canonical agent file agents/{rel.as_posix()}")
    for role in EXPECTED_ROLES:
        for name in sorted(CANONICAL_NAMES):
            if not (root / role / name).exists():
                errors.append(f"missing canonical agent file agents/{role}/{name}")
    return errors


def assemble_prompt(repo: Repo, role: str, hid: str) -> str:
    rp = role_prompt(repo, role)
    manifest = build_agent_manifest(repo)
    card = repo.load_card(hid)
    frozen = card.get("statement", {}).get("frozen_sha256", "")
    return "\n\n".join([
        f"# Agent role: {role}",
        f"Hypothesis: {hid}",
        f"Frozen statement SHA256: {frozen}",
        f"Agent protocol SHA256: {manifest['agent_protocol_sha256']}",
        f"Role prompt SHA256: {manifest['role_hashes'].get(role, '')}",
        rp["common_system"],
        rp["output_contract"],
        rp["system"],
        rp["task"].replace("{H_ID}", hid),
        "# Output schema\n```yaml\n" + rp["schema"] + "\n```",
    ])


def write_assembled_prompt(repo: Repo, role: str, hid: str) -> Path:
    text = assemble_prompt(repo, role, hid)
    out = repo.root / "reports" / "agents" / "prompts"
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{hid}-{role}.md"
    p.write_text(text, encoding="utf-8")
    return p


def init_agent_run(repo: Repo, hid: str, role: str, model: str) -> Path:
    import subprocess
    import yaml
    manifest = build_agent_manifest(repo)
    card = repo.load_card(hid)
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo.root, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        commit = "UNCOMMITTED"
    out = repo.root / "agent-runs" / hid
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    p = out / f"{stamp}-{role}.yaml"
    data = {
        "hypothesis_id": hid,
        "role": role,
        "model": model,
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "commit": commit,
        "statement_sha256": card.get("statement", {}).get("frozen_sha256", ""),
        "agent_protocol_sha256": manifest["agent_protocol_sha256"],
        "role_prompt_sha256": manifest["role_hashes"].get(role, ""),
        "assembled_prompt": f"reports/agents/prompts/{hid}-{role}.md",
        "input_artifacts": [],
        "output_artifacts": [],
        "outcome": "IN_PROGRESS",
        "notes": "",
    }
    p.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return p
