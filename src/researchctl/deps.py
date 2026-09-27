from __future__ import annotations
from pathlib import Path
import json,re
from .model import Repo
from .lean import strip_comments_and_strings

DECL_START = re.compile(r"^\s*(?:private\s+|protected\s+)?(?:theorem|lemma|def|abbrev|opaque|axiom|structure|class|inductive)\s+([A-Za-z0-9_'.]+)\b")
IDENT = re.compile(r"\b[A-Za-z_][A-Za-z0-9_'.]*\b")
KEYWORDS=set("theorem lemma def abbrev opaque axiom structure class inductive by fun match with let in if then else have show from exact apply intro intros cases constructor refine simp simpa rw rfl trivial assumption omega aesop decide native_decide where termination_by decreasing_by import namespace end open variable variables universe universes set_option private protected noncomputable classical".split())

def project_declarations(root:Path)->dict[str,dict]:
    """Best-effort index of project declarations with namespace-qualified names.

    This index is used only to classify elaborated dependency edges as project vs
    environment/library and to locate source lines. Exact dependency discovery is
    performed by Lean in ``lean_exact.py``.
    """
    out={}
    ns_start=re.compile(r"^\s*namespace\s+([A-Za-z0-9_'.]+)\s*$")
    end_re=re.compile(r"^\s*end(?:\s+([A-Za-z0-9_'.]+))?\s*$")
    for p in root.rglob("*.lean"):
        if ".lake" in p.parts or "reports" in p.parts: continue
        lines=p.read_text(encoding="utf-8").splitlines()
        namespace=[]
        decl_rows=[]
        for i,line in enumerate(lines):
            clean=strip_comments_and_strings(line)
            mns=ns_start.match(clean)
            if mns:
                namespace.extend(mns.group(1).split('.')); continue
            mend=end_re.match(clean)
            if mend:
                if namespace: namespace.pop()
                continue
            m=DECL_START.match(clean)
            if not m: continue
            raw=m.group(1)
            full=raw if '.' in raw or not namespace else '.'.join(namespace+[raw])
            decl_rows.append((i,full))
        for idx,(i,name) in enumerate(decl_rows):
            j=decl_rows[idx+1][0] if idx+1<len(decl_rows) else len(lines)
            out[name]={"file":str(p.relative_to(root)),"line":i+1,"text":"\n".join(lines[i:j])}
    return out

def _local_names(text:str)->set[str]:
    names=set()
    for m in re.finditer(r"[\(\[\{]\s*([^:\]\}\)]+?)\s*:",text):
        names.update(x for x in m.group(1).split() if re.match(r"^[A-Za-z_][A-Za-z0-9_']*$",x))
    for m in re.finditer(r"\b(?:let|have|intro|intros)\s+([A-Za-z_][A-Za-z0-9_']*)",text): names.add(m.group(1))
    return names

def direct_dependencies(text:str,self_name:str)->list[str]:
    clean=strip_comments_and_strings(text); locals_=_local_names(clean)
    ids=[]
    for x in IDENT.findall(clean):
        if x in KEYWORDS or x in locals_ or x==self_name or x.isupper(): continue
        if x in {"Nat","Int","Bool","True","False","Prop","Type","Sort"}: continue
        if x not in ids: ids.append(x)
    return ids

def build_graph(repo:Repo,hid:str,max_depth:int=3)->dict:
    card=repo.load_card(hid); target=card.get("statement",{}).get("lean_declaration","").split(".")[-1]
    all_decl=project_declarations(repo.root)
    # find short or fully qualified declaration
    root_name=target
    if root_name not in all_decl:
        candidates=[k for k in all_decl if k.split(".")[-1]==root_name]
        if candidates: root_name=candidates[0]
    nodes={}; edges=[]; seen=set()
    def walk(name,depth):
        if name in seen or depth>max_depth: return
        seen.add(name)
        info=all_decl.get(name)
        nodes[name]={"kind":"project" if info else ("library" if "." in name else "unknown"), **({"file":info["file"],"line":info["line"]} if info else {})}
        if not info: return
        for dep in direct_dependencies(info["text"],name):
            # resolve short project name first
            resolved=dep
            if dep not in all_decl:
                c=[k for k in all_decl if k.split(".")[-1]==dep]
                if len(c)==1: resolved=c[0]
            if resolved not in all_decl and "." not in resolved: continue
            edges.append({"from":name,"to":resolved})
            if resolved not in nodes:
                di=all_decl.get(resolved); nodes[resolved]={"kind":"project" if di else "library", **({"file":di["file"],"line":di["line"]} if di else {})}
            if resolved in all_decl: walk(resolved,depth+1)
    walk(root_name,0)
    return {"hypothesis":hid,"root":root_name,"method":"source-heuristic","warning":"Advisory review-surface graph; not an elaborated kernel dependency proof.","nodes":nodes,"edges":edges}

def write_graph(repo:Repo,hid:str)->tuple[Path,Path]:
    g=build_graph(repo,hid); out=repo.root/"reports"/"dependencies"; out.mkdir(parents=True,exist_ok=True)
    jp=out/f"{hid}.json"; jp.write_text(json.dumps(g,indent=2,ensure_ascii=False),encoding="utf-8")
    lines=["digraph proof {","  rankdir=LR;"]
    for n,d in g["nodes"].items():
        shape="box" if d["kind"]=="project" else "ellipse"
        lines.append(f'  "{n}" [shape={shape}, label="{n}\\n[{d["kind"]}]"];')
    for e in g["edges"]: lines.append(f'  "{e["from"]}" -> "{e["to"]}";')
    lines.append("}")
    dp=out/f"{hid}.dot"; dp.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return jp,dp
