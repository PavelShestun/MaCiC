from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from .model import Repo
from .agent_protocol import build_agent_manifest


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_paths(repo: Repo, hid: str) -> list[Path]:
    card = repo.load_card(hid)
    paths = [
        repo.card_path(hid),
        repo.root / "lit" / f"{hid}.md",
        repo.root / "proofs" / f"{hid}.md",
        repo.root / "provenance" / f"{hid}.yaml",
        repo.root / "ablations" / hid / "manifest.yaml",
        repo.root / "reports" / "statements" / f"{hid}.lean",
        repo.root / "reports" / "dependencies" / f"{hid}.exact.json",
        repo.root / "reports" / "dependencies" / f"{hid}.json",
    ]
    lf = card.get("statement", {}).get("lean_file")
    if lf:
        paths.append(repo.root / lf)
    runs = repo.root / "agent-runs" / hid
    if runs.exists():
        paths.extend(sorted(runs.glob("*.yaml")))
    for f in (repo.root / "reviews" / hid).glob("*.yaml") if (repo.root / "reviews" / hid).exists() else []:
        # Reviews are outputs over evidence, not evidence inputs. Exclude them
        # from the fingerprint to avoid self-reference.
        pass
    return [p for p in paths if p.exists()]


def environment_paths(repo: Repo) -> list[Path]:
    names = ["lean-toolchain", "lakefile.toml", "lakefile.lean", "lake-manifest.json", "pyproject.toml", "research-policy.yaml"]
    return [repo.root / n for n in names if (repo.root / n).exists()]


def build_fingerprint(repo: Repo, hid: str) -> dict:
    files = []
    for p in sorted(evidence_paths(repo, hid), key=lambda x: x.relative_to(repo.root).as_posix()):
        files.append({"path": p.relative_to(repo.root).as_posix(), "sha256": sha256_file(p)})
    env = []
    for p in sorted(environment_paths(repo), key=lambda x: x.relative_to(repo.root).as_posix()):
        env.append({"path": p.relative_to(repo.root).as_posix(), "sha256": sha256_file(p)})
    agent_protocol = build_agent_manifest(repo)
    canonical = json.dumps({"files": files, "environment": env, "agent_protocol_sha256": agent_protocol["agent_protocol_sha256"]}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "hypothesis": hid,
        "statement_hash": repo.load_card(hid).get("statement", {}).get("frozen_sha256", ""),
        "files": files,
        "environment": env,
        "agent_protocol_sha256": agent_protocol["agent_protocol_sha256"],
        "agent_role_hashes": agent_protocol["role_hashes"],
        "evidence_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    }


def write_fingerprint(repo: Repo, hid: str) -> Path:
    data = build_fingerprint(repo, hid)
    out = repo.root / "reports" / "fingerprints"
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{hid}.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def hash_paths(repo: Repo, paths: list[Path]) -> str:
    rows=[]
    for p in sorted((x for x in paths if x.exists()), key=lambda x: x.relative_to(repo.root).as_posix()):
        rows.append((p.relative_to(repo.root).as_posix(), sha256_file(p)))
    raw=json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def domain_fingerprints(repo: Repo, hid: str) -> dict[str, str]:
    card=repo.load_card(hid); lf=card.get("statement",{}).get("lean_file")
    literature=[repo.root/"lit"/f"{hid}.md", repo.root/"provenance"/f"{hid}.yaml"]
    formal=[repo.root/"proofs"/f"{hid}.md", repo.root/"reports"/"statements"/f"{hid}.lean"] + environment_paths(repo)
    if lf: formal.append(repo.root/lf)
    return {
        "statement_sha256": card.get("statement",{}).get("frozen_sha256", ""),
        "formalization_sha256": hash_paths(repo,formal),
        "literature_sha256": hash_paths(repo,literature),
        "environment_sha256": hash_paths(repo,environment_paths(repo)),
        "agent_protocol_sha256": build_agent_manifest(repo)["agent_protocol_sha256"],
        "evidence_sha256": build_fingerprint(repo,hid)["evidence_sha256"],
    }
