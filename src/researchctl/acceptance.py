from __future__ import annotations

import copy
import tempfile
from pathlib import Path
from typing import Callable

from .fingerprint import domain_fingerprints
from .gates import validate_card, validate_repo
from .lean import statement_hash
from .model import Repo, dump_yaml
from .reviews import review_state
from .semantic import write_snapshot


def _mk_repo(root: Path, status: str = "SPEC_FROZEN") -> Repo:
    for d in [
        "hypotheses", "lit", "proofs", "reviews/H-0001", "reports/statements",
        "provenance", "ablations/H-0001"
    ]:
        (root / d).mkdir(parents=True, exist_ok=True)
    lean = root / "A.lean"
    lean.write_text("theorem foo (n : Nat) : n = n := by\n  rfl\n", encoding="utf-8")
    h, text = statement_hash(lean, "foo")
    write_snapshot(Repo(root), "H-0001", text)
    (root / "lit/H-0001.md").write_text("literature evidence\n", encoding="utf-8")
    (root / "proofs/H-0001.md").write_text("proof reconstruction\n", encoding="utf-8")
    dump_yaml(root / "hypotheses/H-0001.yaml", {
        "id": "H-0001", "title": "acceptance theorem", "created": "2026-01-01", "status": status,
        "owners": {"research": "alice", "formalization": "bob"},
        "statement": {
            "informal": "identity", "lean_file": "A.lean", "lean_module": "A",
            "lean_declaration": "foo", "frozen_sha256": h, "freeze_commit": "TEST"
        },
        "claims_of_novelty": {"status": "UNKNOWN", "scope": ""},
        "human_signoff": {"specification": "", "mathematics": "", "formalization": "", "novelty": ""},
    })
    dump_yaml(root / "research-policy.yaml", {
        "require_statement_snapshot": True,
        "require_fresh_literature_review": True,
        "require_fresh_reproduction_review": True,
        "require_fresh_final_review": True,
        "require_github_login_on_reviews": False,
    })
    return Repo(root)


def _pass_semantic(repo: Repo) -> None:
    c = repo.load_card("H-0001")
    dump_yaml(repo.root / "reviews/H-0001/semantic.yaml", {
        "reviewer": "semantic-reviewer", "date": "2026-01-02", "decision": "pass", "summary": "checked",
        "statement_hash_reviewed": c["statement"]["frozen_sha256"],
        "definitions_match_intent": True, "assumptions_explicit": True,
        "conclusion_matches_claim": True, "hidden_trivialization_checked": True,
    })


def _pass_proof(repo: Repo) -> str:
    c = repo.load_card("H-0001"); fp = domain_fingerprints(repo, "H-0001")["formalization_sha256"]
    dump_yaml(repo.root / "reviews/H-0001/proof.yaml", {
        "reviewer": "proof-reviewer", "date": "2026-01-02", "decision": "pass", "summary": "understood",
        "statement_hash_reviewed": c["statement"]["frozen_sha256"], "formalization_sha256_reviewed": fp,
        "human_sketch_complete": True, "key_transitions_understood": True, "no_circularity_found": True,
        "no_hidden_trivialization_found": True, "review_surface_checked": True,
    })
    return fp


def run() -> list[dict[str, str]]:
    results: list[dict[str, str]] = []

    def case(name: str, fn: Callable[[Path], None]) -> None:
        with tempfile.TemporaryDirectory(prefix="mathcicd_acceptance_") as td:
            try:
                fn(Path(td))
                results.append({"case": name, "result": "PASS"})
            except Exception as ex:
                results.append({"case": name, "result": "FAIL", "detail": str(ex)})

    def baseline(root: Path) -> None:
        repo = _mk_repo(root)
        assert validate_repo(repo) == []
    case("baseline passes", baseline)

    def sorry(root: Path) -> None:
        repo = _mk_repo(root)
        (root / "Bad.lean").write_text("theorem bad : True := by\n  sorry\n", encoding="utf-8")
        assert any("forbidden placeholder sorry" in x for x in validate_repo(repo))
    case("sorry is rejected", sorry)

    def badref(root: Path) -> None:
        repo = _mk_repo(root, status="CANDIDATE")
        c = repo.load_card("H-0001"); c["statement"]["lean_file"] = "A"
        dump_yaml(repo.card_path("H-0001"), c)
        errs = validate_repo(repo)
        assert any("INVALID_LEAN_REFERENCE" in x for x in errs)
    case("bad Lean references fail validate", badref)

    def drift(root: Path) -> None:
        repo = _mk_repo(root)
        (root / "A.lean").write_text("theorem foo (n : Nat) (h : True) : n = n := by\n  rfl\n", encoding="utf-8")
        assert any("FROZEN_STATEMENT_DRIFT" in x for x in validate_repo(repo))
    case("frozen statement drift is rejected", drift)

    def stale(root: Path) -> None:
        repo = _mk_repo(root, status="PROOF_RECONSTRUCTED")
        _pass_semantic(repo); old = _pass_proof(repo)
        assert validate_card(repo, repo.card_path("H-0001")) == []
        (root / "proofs/H-0001.md").write_text("changed proof reconstruction\n", encoding="utf-8")
        assert domain_fingerprints(repo, "H-0001")["formalization_sha256"] != old
        assert review_state(repo, "H-0001", "proof")["state"] == "STALE"
        assert any("proof review is stale" in x for x in validate_card(repo, repo.card_path("H-0001")))
    case("proof change makes proof review stale", stale)

    return results
