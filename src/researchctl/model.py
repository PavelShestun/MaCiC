from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib, yaml

STATUSES = [
    "CANDIDATE", "SPEC_DRAFT", "SPEC_FROZEN", "FORMALIZED",
    "SEMANTIC_REVIEWED", "PROOF_RECONSTRUCTED", "NOVELTY_REVIEWED",
    "INDEPENDENTLY_REPRODUCED", "VERIFIED_RESULT",
    "REFUTED", "KNOWN_RESULT", "SPECIFICATION_BUG", "BLOCKED", "INCONCLUSIVE",
]
TERMINAL = {"VERIFIED_RESULT","REFUTED","KNOWN_RESULT","SPECIFICATION_BUG","BLOCKED","INCONCLUSIVE"}
TRANSITIONS = {
    "CANDIDATE": {"SPEC_DRAFT","REFUTED","KNOWN_RESULT","BLOCKED","INCONCLUSIVE"},
    "SPEC_DRAFT": {"SPEC_FROZEN","REFUTED","KNOWN_RESULT","SPECIFICATION_BUG","BLOCKED","INCONCLUSIVE"},
    "SPEC_FROZEN": {"FORMALIZED","SPEC_DRAFT","REFUTED","KNOWN_RESULT","SPECIFICATION_BUG","BLOCKED","INCONCLUSIVE"},
    "FORMALIZED": {"SEMANTIC_REVIEWED","SPEC_DRAFT","REFUTED","KNOWN_RESULT","SPECIFICATION_BUG","BLOCKED","INCONCLUSIVE"},
    "SEMANTIC_REVIEWED": {"PROOF_RECONSTRUCTED","SPEC_DRAFT","REFUTED","KNOWN_RESULT","SPECIFICATION_BUG","BLOCKED","INCONCLUSIVE"},
    "PROOF_RECONSTRUCTED": {"NOVELTY_REVIEWED","SPEC_DRAFT","REFUTED","KNOWN_RESULT","SPECIFICATION_BUG","BLOCKED","INCONCLUSIVE"},
    "NOVELTY_REVIEWED": {"INDEPENDENTLY_REPRODUCED","SPEC_DRAFT","KNOWN_RESULT","BLOCKED","INCONCLUSIVE"},
    "INDEPENDENTLY_REPRODUCED": {"VERIFIED_RESULT","SPEC_DRAFT","KNOWN_RESULT","BLOCKED","INCONCLUSIVE"},
}

@dataclass
class Repo:
    root: Path
    def card_path(self, hid: str) -> Path: return self.root / "hypotheses" / f"{hid}.yaml"
    def load_card(self, hid: str) -> dict[str, Any]:
        return load_yaml(self.card_path(hid))

def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists(): raise FileNotFoundError(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict): raise ValueError(f"{path} must contain a YAML mapping")
    return data

def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
