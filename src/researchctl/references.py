from __future__ import annotations

from pathlib import Path
from typing import Any

from .lean import extract_declaration_header
from .model import Repo


def expected_module_from_file(path: str) -> str:
    p = Path(path)
    if p.suffix == ".lean":
        p = p.with_suffix("")
    parts = [x for x in p.parts if x not in {".", ""}]
    return ".".join(parts)


def validate_lean_reference(repo: Repo, card: dict[str, Any]) -> list[str]:
    """Cheap referential-integrity checks that do not require Lean execution.

    These checks run for every hypothesis as soon as any Lean reference is
    supplied. Exact environment resolution remains the job of Lean CI, but a
    typo or swapped lean_file/lean_module/lean_declaration must never survive
    `researchctl validate`.
    """
    st = card.get("statement", {}) or {}
    lf = str(st.get("lean_file") or "").strip()
    mod = str(st.get("lean_module") or "").strip()
    dec = str(st.get("lean_declaration") or "").strip()
    if not any((lf, mod, dec)):
        return []

    hid = card.get("id", "<unknown>")
    errs: list[str] = []
    if not lf:
        errs.append(f"{hid}: INVALID_LEAN_REFERENCE missing statement.lean_file")
    if not mod:
        errs.append(f"{hid}: INVALID_LEAN_REFERENCE missing statement.lean_module")
    if not dec:
        errs.append(f"{hid}: INVALID_LEAN_REFERENCE missing statement.lean_declaration")
    if not lf:
        return errs

    if not lf.endswith(".lean"):
        errs.append(f"{hid}: INVALID_LEAN_REFERENCE lean_file must end in .lean: {lf}")
    path = repo.root / lf
    if not path.exists():
        errs.append(f"{hid}: INVALID_LEAN_REFERENCE lean_file does not exist: {lf}")
        return errs
    if not path.is_file():
        errs.append(f"{hid}: INVALID_LEAN_REFERENCE lean_file is not a file: {lf}")
        return errs

    if mod:
        expected = expected_module_from_file(lf)
        if expected and mod != expected:
            errs.append(
                f"{hid}: INVALID_LEAN_REFERENCE lean_module={mod!r} does not match "
                f"lean_file={lf!r}; expected {expected!r}"
            )

    if dec:
        try:
            extract_declaration_header(path, dec)
        except Exception as ex:
            errs.append(f"{hid}: INVALID_LEAN_REFERENCE declaration {dec!r} not found/extractable in {lf}: {ex}")
    return errs


def format_reference_help(card: dict[str, Any]) -> str:
    st = card.get("statement", {}) or {}
    lf = st.get("lean_file", "")
    mod = st.get("lean_module", "")
    dec = st.get("lean_declaration", "")
    return (
        "Lean reference fields must be distinct:\n"
        f"  lean_file:        {lf or '<path/to/File.lean>'}\n"
        f"  lean_module:      {mod or '<Path.To.File>'}\n"
        f"  lean_declaration: {dec or '<Namespace.theorem_name>'}"
    )
