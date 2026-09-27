from __future__ import annotations
from pathlib import Path
import difflib, re
from .lean import extract_declaration_header
from .model import Repo, sha256_text

BINDER_RE = re.compile(r"([\(\[\{])\s*([^:\]\}\)]+?)\s*:\s*([^\]\}\)]+)[\)\]\}]")

def snapshot_path(repo: Repo, hid: str) -> Path:
    return repo.root / "reports" / "statements" / f"{hid}.lean"

def write_snapshot(repo: Repo, hid: str, text: str) -> Path:
    p=snapshot_path(repo,hid); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text.rstrip()+"\n",encoding="utf-8")
    return p

def read_snapshot(repo: Repo, hid: str) -> str | None:
    p=snapshot_path(repo,hid)
    return p.read_text(encoding="utf-8").rstrip() if p.exists() else None

def binders(header: str) -> list[dict[str,str]]:
    out=[]
    for m in BINDER_RE.finditer(header):
        opener,name,typ=m.groups()
        out.append({"kind":{"(":"explicit","[":"instance","{":"implicit"}[opener],"name":name.strip(),"type":typ.strip()})
    return out

def conclusion(header: str) -> str:
    # Take final top-level colon after theorem name/binders. Heuristic but useful for review.
    depth=0; positions=[]
    for i,c in enumerate(header):
        if c in "([{": depth+=1
        elif c in ")]}": depth=max(0,depth-1)
        elif c==":" and depth==0: positions.append(i)
    return header[positions[-1]+1:].strip() if positions else ""

def semantic_diff(old: str, new: str) -> dict:
    ob,nb=binders(old),binders(new)
    oc,nc=conclusion(old),conclusion(new)
    return {
        "old_sha256": sha256_text(old), "new_sha256": sha256_text(new),
        "statement_changed": old.strip()!=new.strip(),
        "binders_changed": ob!=nb,
        "conclusion_changed": oc!=nc,
        "old_binders": ob, "new_binders": nb,
        "old_conclusion": oc, "new_conclusion": nc,
        "unified_diff": "\n".join(difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile="frozen",tofile="current",lineterm="")),
    }

def diff_card(repo: Repo, hid: str) -> dict:
    card=repo.load_card(hid); st=card.get("statement",{})
    current=extract_declaration_header(repo.root/st["lean_file"],st["lean_declaration"])
    old=read_snapshot(repo,hid)
    if old is None:
        return {"error":"no frozen statement snapshot; run researchctl freeze again or researchctl snapshot", "current":current}
    return semantic_diff(old,current)
