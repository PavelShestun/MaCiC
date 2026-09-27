from __future__ import annotations
from pathlib import Path
import re
from .model import Repo, dump_yaml, load_yaml
from .semantic import read_snapshot, binders

ASSUMPTION_HINT=re.compile(r"^(h|ha|hb|hc|assump|hyp|cond|premise)",re.I)

def generate(repo:Repo,hid:str)->Path:
    old=read_snapshot(repo,hid)
    if not old: raise ValueError("no statement snapshot; freeze statement first")
    bs=binders(old); candidates=[]
    for i,b in enumerate(bs,1):
        # Include explicit Prop-looking binders and hypothesis-like names. Human may edit manifest.
        t=b["type"]; n=b["name"]
        likely=bool(ASSUMPTION_HINT.match(n)) or any(op in t for op in ["=","<",">","∧","∨","→"]) or t in {"True","False"}
        candidates.append({"id":f"A{i}","binder":n,"type":t,"kind":b["kind"],"candidate_assumption":likely,"status":"UNKNOWN","evidence":"","notes":""})
    out=repo.root/"ablations"/hid; out.mkdir(parents=True,exist_ok=True)
    manifest={"hypothesis":hid,"statement_hash":repo.load_card(hid).get("statement",{}).get("frozen_sha256",""),"method":"remove-one-binder candidate analysis","assumptions":candidates}
    p=out/"manifest.yaml"; dump_yaml(p,manifest)
    md=[f"# Assumption ablation - {hid}","","Each row is a candidate experiment. `UNKNOWN` is acceptable before novelty/final review.","","| ID | Binder | Type | Candidate? | Status | Evidence |","|---|---|---|---|---|---|"]
    for a in candidates: md.append(f"| {a['id']} | `{a['binder']}` | `{a['type']}` | {a['candidate_assumption']} | {a['status']} | |")
    (out/"README.md").write_text("\n".join(md)+"\n",encoding="utf-8")
    return p

def validate(repo:Repo,hid:str,required:bool=False)->list[str]:
    p=repo.root/"ablations"/hid/"manifest.yaml"
    if not p.exists(): return [f"{hid}: missing ablation manifest"] if required else []
    d=load_yaml(p); e=[]; frozen=repo.load_card(hid).get("statement",{}).get("frozen_sha256","")
    if d.get("statement_hash")!=frozen: e.append(f"{hid}: ablation manifest is for a different statement hash")
    for a in d.get("assumptions",[]):
        status=a.get("status","UNKNOWN")
        if status not in {"UNKNOWN","NECESSARY","NOT_NECESSARY","REDUNDANT_WITH_OTHERS","COUNTEREXAMPLE_FOUND","NOT_AN_ASSUMPTION"}: e.append(f"{hid}: invalid ablation status {status}")
        if status not in {"UNKNOWN","NOT_AN_ASSUMPTION"} and not a.get("evidence"): e.append(f"{hid}: ablation {a.get('id')} status {status} needs evidence")
    return e
