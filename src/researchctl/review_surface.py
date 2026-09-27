from __future__ import annotations

import json
from pathlib import Path

from .model import Repo, load_yaml
from .provenance import path as provenance_path


def _load_graph(repo: Repo, hid: str) -> dict:
    exact = repo.root / "reports" / "dependencies" / f"{hid}.exact.json"
    fallback = repo.root / "reports" / "dependencies" / f"{hid}.json"
    p = exact if exact.exists() else fallback
    if not p.exists():
        raise FileNotFoundError(f"no dependency report for {hid}; run researchctl deps-exact or deps")
    return json.loads(p.read_text(encoding="utf-8"))


def analyze(repo: Repo, hid: str) -> dict:
    g = _load_graph(repo, hid)
    prov = {}
    pp = provenance_path(repo, hid)
    if pp.exists():
        pd = load_yaml(pp)
        prov = {x.get("declaration"): x.get("type", "UNKNOWN") for x in pd.get("dependencies", [])}
    root = g["root"]
    children: dict[str, set[str]] = {n: set() for n in g["nodes"]}
    parents: dict[str, set[str]] = {n: set() for n in g["nodes"]}
    for e in g["edges"]:
        children.setdefault(e["from"], set()).add(e["to"])
        parents.setdefault(e["to"], set()).add(e["from"])

    def descendants(n: str) -> set[str]:
        seen = set(); stack = list(children.get(n, ()))
        while stack:
            x = stack.pop()
            if x in seen: continue
            seen.add(x); stack.extend(children.get(x, ()))
        return seen

    rows = []
    for n, info in g["nodes"].items():
        if info.get("kind") != "project":
            continue
        ptype = "PROJECT_NEW" if n == root else prov.get(n, "UNKNOWN")
        ds = descendants(n)
        project_ds = [d for d in ds if g["nodes"].get(d, {}).get("kind") == "project"]
        new_ds = [d for d in project_ds if prov.get(d) == "PROJECT_NEW"]
        rows.append({
            "declaration": n,
            "provenance": ptype,
            "direct_dependencies": len(children.get(n, ())),
            "project_descendants": len(project_ds),
            "new_descendants": len(new_ds),
            "incoming_project_edges": sum(1 for p in parents.get(n, ()) if g["nodes"].get(p, {}).get("kind") == "project"),
            "priority_score": 100 * (ptype == "PROJECT_NEW") + 10 * len(new_ds) + len(project_ds),
        })
    rows.sort(key=lambda r: (-r["priority_score"], r["declaration"]))
    new_surface = [r["declaration"] for r in rows if r["provenance"] == "PROJECT_NEW"]
    unresolved = [r["declaration"] for r in rows if r["provenance"] == "UNKNOWN" and r["declaration"] != root]
    return {
        "hypothesis": hid,
        "graph_method": g.get("method"),
        "root": root,
        "recommended_review_order": [r["declaration"] for r in rows],
        "novel_project_surface": new_surface,
        "unresolved_project_provenance": unresolved,
        "metrics": rows,
        "note": "Priority is a triage heuristic, not a mathematical importance score or proof of novelty.",
    }


def write(repo: Repo, hid: str) -> Path:
    data = analyze(repo, hid)
    out = repo.root / "reports" / "review-surface"
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"{hid}.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p
