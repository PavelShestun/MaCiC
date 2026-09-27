from __future__ import annotations

from typing import Any

from .fingerprint import domain_fingerprints
from .model import Repo, load_yaml


def _review(repo: Repo, hid: str, name: str) -> dict[str, Any] | None:
    p = repo.root / "reviews" / hid / f"{name}.yaml"
    if not p.exists():
        return None
    try:
        return load_yaml(p)
    except Exception:
        return None


def review_state(repo: Repo, hid: str, name: str) -> dict[str, Any]:
    """Return review decision plus freshness independent of current lifecycle status."""
    card = repo.load_card(hid)
    d = _review(repo, hid, name)
    if d is None:
        return {"state": "MISSING", "decision": "missing", "reviewer": "", "reasons": []}

    decision = str(d.get("decision") or "inconclusive")
    reviewer = str(d.get("reviewer") or "")
    reasons: list[str] = []
    frozen = card.get("statement", {}).get("frozen_sha256", "")
    fps = domain_fingerprints(repo, hid)

    if decision == "pass":
        if name in {"semantic", "proof", "literature", "reproduction"}:
            rh = d.get("statement_hash_reviewed")
            if rh not in {None, "", frozen}:
                reasons.append("statement hash changed")
        if name == "proof" and d.get("formalization_sha256_reviewed") != fps["formalization_sha256"]:
            reasons.append("formalization/environment changed")
        if name == "literature" and d.get("literature_sha256_reviewed") != fps["literature_sha256"]:
            reasons.append("literature/provenance evidence changed")
        if name == "reproduction" and d.get("formalization_sha256_reviewed") != fps["formalization_sha256"]:
            reasons.append("formalization/environment changed")
        if name == "final" and d.get("evidence_sha256_reviewed") != fps["evidence_sha256"]:
            reasons.append("evidence bundle changed")

    if decision != "pass":
        state = decision.upper() if decision else "INCONCLUSIVE"
    elif reasons:
        state = "STALE"
    else:
        state = "VALID"
    return {"state": state, "decision": decision, "reviewer": reviewer, "reasons": reasons, "data": d}
