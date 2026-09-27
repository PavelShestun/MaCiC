from __future__ import annotations

import datetime
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

import yaml

from .model import Repo

PROFILE_DIR = Path("agents/profiles")
BLIND_SYSTEM = """# Isolated mathematical analysis task\n\nYou are given only the material required for the task below. Treat the supplied claim as an arbitrary mathematical object. Do not assume that it is true, false, important, original, machine-generated, formally verified, or intended for publication. Do not infer missing project context. Work only from the supplied packet and report uncertainty explicitly.\n"""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_profile(repo: Repo, name: str) -> dict[str, Any]:
    p = repo.root / PROFILE_DIR / f"{name}.yaml"
    if not p.exists():
        raise FileNotFoundError(f"unknown visibility profile: {name}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    data.setdefault("name", name)
    data.setdefault("include", [])
    data.setdefault("exclude", [])
    data.setdefault("sanitize", {})
    data.setdefault("leakage", {})
    return data


def profile_paths(repo: Repo) -> list[Path]:
    root = repo.root / PROFILE_DIR
    return sorted(root.glob("*.yaml")) if root.exists() else []


def _statement(repo: Repo, hid: str) -> str:
    p = repo.root / "reports" / "statements" / f"{hid}.lean"
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    card = repo.load_card(hid)
    return str(card.get("statement", {}).get("informal", "")).strip()


def _render_list(value: Any) -> str:
    if not value:
        return "(none recorded)"
    if isinstance(value, list):
        rows = []
        for i, item in enumerate(value, 1):
            if isinstance(item, dict):
                rows.append(f"{i}. " + "; ".join(f"{k}={v}" for k, v in item.items()))
            else:
                rows.append(f"{i}. {item}")
        return "\n".join(rows)
    return str(value)


def _source_artifact(repo: Repo, hid: str, name: str) -> tuple[str, str] | None:
    card = repo.load_card(hid)
    if name == "frozen_statement":
        return "STATEMENT.md", _statement(repo, hid)
    if name == "informal_statement":
        return "CLAIM.md", str(card.get("statement", {}).get("informal", ""))
    if name == "definitions":
        return "DEFINITIONS.md", _render_list(card.get("definitions", []))
    if name == "assumptions":
        return "ASSUMPTIONS.md", _render_list(card.get("assumptions", []))
    if name == "notation":
        return "NOTATION.md", _render_list(card.get("notation", []))
    mapping = {
        "proof_reconstruction": repo.root / "proofs" / f"{hid}.md",
        "literature_log": repo.root / "lit" / f"{hid}.md",
        "provenance": repo.root / "provenance" / f"{hid}.yaml",
        "exact_dependencies": repo.root / "reports" / "dependencies" / f"{hid}.exact.json",
        "review_surface": repo.root / "reports" / "review-surface" / f"{hid}.json",
        "lean_source": repo.root / str(card.get("statement", {}).get("lean_file", "")),
    }
    p = mapping.get(name)
    if p and p.exists() and p.is_file():
        return p.name, p.read_text(encoding="utf-8")
    return None


def _collect_identifiers(card: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key in ("title",):
        v = card.get(key)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
    st = card.get("statement", {}) or {}
    for key in ("lean_declaration", "lean_module"):
        v = st.get(key)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
            out.append(v.split(".")[-1])
    for seq_key in ("definitions",):
        for item in card.get(seq_key, []) or []:
            if isinstance(item, str):
                # collect identifier-like leading token only, not ordinary prose
                m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_'.]*)", item)
                if m:
                    out.append(m.group(1))
            elif isinstance(item, dict):
                for k in ("name", "declaration", "symbol"):
                    v = item.get(k)
                    if isinstance(v, str) and v.strip():
                        out.append(v.strip())
    return sorted({x for x in out if len(x) >= 3}, key=lambda x: (-len(x), x))


def _sanitize_text(text: str, card: dict[str, Any], profile: dict[str, Any]) -> tuple[str, dict[str, str]]:
    cfg = profile.get("sanitize", {}) or {}
    aliases: dict[str, str] = {}
    if cfg.get("hide_hypothesis_id", True):
        hid = str(card.get("id", ""))
        if hid:
            text = text.replace(hid, "CLAIM")
            aliases[hid] = "CLAIM"
    if cfg.get("neutralize_identifiers", False):
        counters = {"Claim": 0, "Object": 0}
        for ident in _collect_identifiers(card):
            if ident in aliases:
                continue
            kind = "Claim" if "theorem" in ident.lower() or ident == (card.get("statement", {}) or {}).get("lean_declaration") else "Object"
            counters[kind] += 1
            alias = f"{kind}_{counters[kind]:02d}"
            text = re.sub(rf"(?<![A-Za-z0-9_']){re.escape(ident)}(?![A-Za-z0-9_'])", alias, text)
            aliases[ident] = alias
    for pat in cfg.get("redact_regex", []) or []:
        text = re.sub(str(pat), "[REDACTED]", text, flags=re.IGNORECASE)
    return text, aliases


def _forbidden_markers(repo: Repo, hid: str, profile: dict[str, Any]) -> list[str]:
    card = repo.load_card(hid)
    markers: list[str] = []
    leakage = profile.get("leakage", {}) or {}
    if leakage.get("forbid_project_title", True):
        title = str(card.get("title", "")).strip()
        if title:
            markers.append(title)
    if leakage.get("forbid_hypothesis_id", True):
        markers.append(hid)
    if leakage.get("forbid_global_stage_terms", True):
        markers.extend([
            "VERIFIED_RESULT", "NOVELTY_REVIEWED", "SEMANTIC_REVIEWED",
            "PROOF_RECONSTRUCTED", "INDEPENDENTLY_REPRODUCED",
            "publication-ready", "new theorem candidate", "generator output",
        ])
    markers.extend(str(x) for x in leakage.get("forbidden_markers", []) or [])
    return [x for x in markers if x]


def audit_packet_dir(packet_dir: Path, forbidden: list[str]) -> list[str]:
    """Audit only the agent-visible payload.

    A packet root may contain an ``audit-only`` sibling with provenance that is
    intentionally *not* visible to the model. Passing an entire packet root to
    an agent is therefore prohibited; use ``context-export``.
    """
    visible = packet_dir / "agent-visible" if (packet_dir / "agent-visible").is_dir() else packet_dir
    errors: list[str] = []
    forbidden_filenames = {"INPUT_MANIFEST.json", "ALIASES.json"}
    for p in sorted(visible.rglob("*")):
        if not p.is_file():
            continue
        if p.name in forbidden_filenames:
            errors.append(f"{p.relative_to(visible)}: audit-only metadata present in agent-visible tree")
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for marker in forbidden:
            if marker.lower() in text.lower():
                errors.append(f"{p.relative_to(visible)}: forbidden context marker leaked: {marker!r}")
    return errors


def export_context(repo: Repo, hid: str, run_id: str, destination: Path) -> Path:
    """Export exactly the model-visible payload to a clean directory.

    Audit metadata (aliases, manifests, original identifiers) is never copied.
    The destination must not already contain files so operators cannot
    accidentally mix hidden metadata into the exported context.
    """
    packet = repo.root / "reports" / "agent-inputs" / hid / run_id
    visible = packet / "agent-visible"
    audit = packet / "audit-only"
    if not visible.is_dir() or not audit.is_dir():
        raise FileNotFoundError(f"two-zone context packet not found for {hid}/{run_id}")
    manifest = audit / "INPUT_MANIFEST.json"
    if not manifest.exists():
        raise FileNotFoundError(f"audit manifest missing for {hid}/{run_id}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    profile = load_profile(repo, data["visibility_profile"])
    errs = audit_packet_dir(packet, _forbidden_markers(repo, hid, profile))
    if errs:
        raise ValueError("blind context leakage detected: " + "; ".join(errs))
    destination = destination.resolve()
    if destination.exists():
        if any(destination.iterdir()):
            raise FileExistsError(f"destination is not empty: {destination}")
    else:
        destination.mkdir(parents=True)
    for src in visible.rglob("*"):
        rel = src.relative_to(visible)
        dst = destination / rel
        if src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    # Defense in depth: audit-only filenames must never be exported.
    for name in ("INPUT_MANIFEST.json", "ALIASES.json"):
        if any(x.name == name for x in destination.rglob("*")):
            raise RuntimeError(f"unsafe export contains audit-only file: {name}")
    return destination


def build_context(repo: Repo, hid: str, role: str, profile_name: str, run_id: str | None = None) -> Path:
    profile = load_profile(repo, profile_name)
    allowed_roles = profile.get("roles", []) or []
    if allowed_roles and role not in allowed_roles:
        raise ValueError(f"profile {profile_name} is not allowed for role {role}")
    card = repo.load_card(hid)
    from .agent_protocol import build_agent_manifest, role_prompt
    manifest = build_agent_manifest(repo)
    run_id = run_id or datetime.datetime.now(datetime.timezone.utc).strftime("AR-%Y%m%dT%H%M%SZ")
    out = repo.root / "reports" / "agent-inputs" / hid / run_id
    visible = out / "agent-visible"
    audit = out / "audit-only"
    visible.mkdir(parents=True, exist_ok=False)
    audit.mkdir(parents=True, exist_ok=False)

    aliases: dict[str, str] = {}
    input_rows = []
    for artifact in profile.get("include", []):
        src = _source_artifact(repo, hid, str(artifact))
        if src is None:
            if artifact in (profile.get("optional", []) or []):
                continue
            raise FileNotFoundError(f"required context artifact {artifact!r} is missing for {hid}")
        filename, text = src
        clean, amap = _sanitize_text(text, card, profile)
        aliases.update(amap)
        target = visible / filename
        target.write_text(clean.rstrip() + "\n", encoding="utf-8")
        input_rows.append({"artifact": artifact, "file": f"agent-visible/{filename}", "sha256": _sha256(target.read_bytes())})

    rp = role_prompt(repo, role)
    if profile.get("prompt_mode", "blind") == "blind":
        task = str(profile.get("task", "Analyze the supplied mathematical material according to the task constraints."))
        task, amap = _sanitize_text(task, card, profile)
        aliases.update(amap)
        prompt = "\n\n".join([
            BLIND_SYSTEM,
            "# Task\n" + task,
            "# Output format\nReturn YAML with keys: outcome, findings, unresolved_risks. Do not include project names, hidden-stage guesses, role labels, or claims about material you were not shown.",
        ])
    else:
        prompt = "\n\n".join([rp["system"], rp["task"].replace("{H_ID}", hid), rp["schema"]])
    (visible / "TASK.md").write_text(prompt.rstrip() + "\n", encoding="utf-8")
    input_rows.append({"artifact": "task", "file": "agent-visible/TASK.md", "sha256": _sha256((visible / "TASK.md").read_bytes())})

    if aliases:
        (audit / "ALIASES.json").write_text(json.dumps(aliases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    forbidden = _forbidden_markers(repo, hid, profile)
    leak_errors = audit_packet_dir(out, forbidden)
    if leak_errors:
        shutil.rmtree(out)
        raise ValueError("blind context leakage detected: " + "; ".join(leak_errors))

    profile_path = repo.root / PROFILE_DIR / f"{profile_name}.yaml"
    packet_payload = {
        "run_id": run_id,
        "role": role,
        "visibility_profile": profile_name,
        "profile_sha256": _sha256(profile_path.read_bytes()),
        "agent_protocol_sha256": manifest["agent_protocol_sha256"],
        "role_prompt_sha256": manifest["role_hashes"].get(role, ""),
        "statement_sha256": card.get("statement", {}).get("frozen_sha256", ""),
        "included_artifacts": input_rows,
        "declared_exclusions": profile.get("exclude", []),
        "sanitization": profile.get("sanitize", {}),
        "leakage_markers_checked": forbidden,
        "leakage_scan": "PASS",
        "visible_root": "agent-visible",
        "audit_root": "audit-only",
    }
    raw = json.dumps(packet_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    packet_payload["context_packet_sha256"] = _sha256(raw)
    (audit / "INPUT_MANIFEST.json").write_text(json.dumps(packet_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def profiles_manifest(repo: Repo) -> dict[str, Any]:
    rows = []
    for p in profile_paths(repo):
        rows.append({"path": p.relative_to(repo.root).as_posix(), "sha256": _sha256(p.read_bytes())})
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"profiles": rows, "visibility_profiles_sha256": _sha256(raw)}


def audit_profiles(repo: Repo) -> list[str]:
    errors: list[str] = []
    required = {"skeptic-blind", "proof-blind", "reproducer-blind", "literature-blind", "semantic-blind"}
    present = {p.stem for p in profile_paths(repo)}
    for name in sorted(required - present):
        errors.append(f"missing visibility profile agents/profiles/{name}.yaml")
    for p in profile_paths(repo):
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception as ex:
            errors.append(f"invalid profile {p.name}: {ex}")
            continue
        if not data.get("roles"):
            errors.append(f"visibility profile {p.name} has no roles")
        if not data.get("include"):
            errors.append(f"visibility profile {p.name} has empty include set")
    return errors
