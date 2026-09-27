from __future__ import annotations
from pathlib import Path
from .model import Repo, load_yaml, dump_yaml
from .deps import build_graph
import json

ALLOWED={"PROJECT_NEW","PROJECT_PRIOR","MATHLIB","EXTERNAL_PUBLISHED","STANDARD_FACT","UNKNOWN"}

def path(repo:Repo,hid:str)->Path: return repo.root/"provenance"/f"{hid}.yaml"

def init_provenance(repo:Repo,hid:str)->Path:
    exact=repo.root/"reports"/"dependencies"/f"{hid}.exact.json"
    g=json.loads(exact.read_text(encoding="utf-8")) if exact.exists() else build_graph(repo,hid)
    deps=[]
    for name,info in sorted(g["nodes"].items()):
        if name==g["root"]: continue
        deps.append({"declaration":name,"type":"PROJECT_PRIOR" if info["kind"]=="project" else "UNKNOWN","source":"","citation":"","review_required": info["kind"]!="project","notes":""})
    data={"hypothesis":hid,"statement_hash":repo.load_card(hid).get("statement",{}).get("frozen_sha256",""),"dependencies":deps}
    p=path(repo,hid); dump_yaml(p,data); return p

def validate_provenance(repo:Repo,hid:str)->list[str]:
    p=path(repo,hid)
    if not p.exists(): return [f"{hid}: missing provenance/{hid}.yaml"]
    d=load_yaml(p); e=[]
    frozen=repo.load_card(hid).get("statement",{}).get("frozen_sha256","")
    if d.get("statement_hash")!=frozen: e.append(f"{hid}: provenance is for a different statement hash")
    for i,x in enumerate(d.get("dependencies",[])):
        if x.get("type") not in ALLOWED: e.append(f"{hid}: provenance dependency {i} has invalid type")
        if x.get("type") in {"EXTERNAL_PUBLISHED","MATHLIB"} and not (x.get("source") or x.get("citation")):
            e.append(f"{hid}: {x.get('declaration')} provenance needs source/citation")
        if x.get("review_required") and x.get("type")=="UNKNOWN": e.append(f"{hid}: unresolved provenance for {x.get('declaration')}")
    return e
