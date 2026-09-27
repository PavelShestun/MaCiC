from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .model import Repo
from .deps import project_declarations

DECL_BEGIN = "MATHCICD_DECL_BEGIN\t"
DECL_END = "MATHCICD_DECL_END\t"
DEP_PREFIX = "MATHCICD_DEP\t"
MISSING_PREFIX = "MATHCICD_MISSING\t"


def lean_available() -> bool:
    return shutil.which("lake") is not None


def _probe_source(module: str, declarations: list[str]) -> str:
    calls = "\n".join(f"#math_cicd_deps? {d}" for d in declarations)
    return f'''import {module}\nimport Lean.Util.FoldConsts\nimport Lean.Elab.Command\n\nopen Lean Lean.Elab Lean.Elab.Command\n\nsyntax (name := mathCICDDeps) "#math_cicd_deps? " ident : command\n\n@[command_elab mathCICDDeps] def elabMathCICDDeps : CommandElab := fun stx => do\n  let declName := stx[1].getId\n  let env ← getEnv\n  match env.find? declName with\n  | none =>\n      logInfo m!"{MISSING_PREFIX}{{declName}}"\n  | some info =>\n      let deps := info.getUsedConstantsAsSet\n      logInfo m!"{DECL_BEGIN}{{declName}}"\n      for n in deps do\n        logInfo m!"{DEP_PREFIX}{{n}}"\n      logInfo m!"{DECL_END}{{declName}}"\n\n{calls}\n'''


def _run_batch_probe(root: Path, module: str, declarations: list[str], timeout: int = 240) -> tuple[int, str]:
    reports = root / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mathcicd_deps_", dir=str(reports)) as td:
        probe = Path(td) / "Probe.lean"
        probe.write_text(_probe_source(module, declarations), encoding="utf-8")
        p = subprocess.run(
            ["lake", "env", "lean", str(probe)],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return p.returncode, p.stdout


def _payload(line: str, marker: str) -> str | None:
    if marker not in line:
        return None
    x = line.split(marker, 1)[1].strip()
    return x.split()[0] if x else None


def parse_batch_output(out: str) -> tuple[dict[str, list[str]], list[str]]:
    graph: dict[str, list[str]] = {}
    missing: list[str] = []
    current: str | None = None
    for raw in out.splitlines():
        line = raw.strip()
        x = _payload(line, DECL_BEGIN)
        if x:
            current = x
            graph.setdefault(current, [])
            continue
        x = _payload(line, DECL_END)
        if x:
            current = None
            continue
        x = _payload(line, MISSING_PREFIX)
        if x:
            missing.append(x)
            continue
        x = _payload(line, DEP_PREFIX)
        if x and current and x != current and x not in graph[current]:
            graph[current].append(x)
    return {k: sorted(v) for k, v in graph.items()}, sorted(set(missing))


def build_exact_graph(repo: Repo, hid: str, *, max_project_nodes: int = 500, timeout: int = 240) -> dict:
    if not lean_available():
        raise RuntimeError("lake is not available; install Lean/elan or run this command in the Lean CI job")
    card = repo.load_card(hid)
    st = card.get("statement", {})
    module = st.get("lean_module")
    root_decl = st.get("lean_declaration")
    if not module or not root_decl:
        raise ValueError(f"{hid}: statement.lean_module and statement.lean_declaration are required")

    project = project_declarations(repo.root)
    candidates = sorted(set([root_decl, *project.keys()]))
    if len(candidates) > max_project_nodes:
        raise RuntimeError(
            f"project contains {len(candidates)} indexed declarations, exceeding max_project_nodes={max_project_nodes}; "
            "raise the limit explicitly if this is expected"
        )

    rc, out = _run_batch_probe(repo.root, module, candidates, timeout=timeout)
    if rc != 0:
        raise RuntimeError(f"Lean dependency probe failed:\n{out[-12000:]}")
    adjacency, missing = parse_batch_output(out)
    if root_decl not in adjacency:
        raise RuntimeError(
            f"root declaration {root_decl} was not found in the imported Lean environment. "
            f"Probe missing count={len(missing)}. Tail:\n{out[-6000:]}"
        )

    # Traverse exact elaborated edges, recurring through project declarations
    # that are visible in the target module's environment. Environment/library
    # constants remain leaves to keep the research graph finite.
    nodes: dict[str, dict] = {}
    edges: list[dict[str, str]] = []
    queue = [root_decl]
    seen: set[str] = set()
    while queue:
        name = queue.pop(0)
        if name in seen:
            continue
        seen.add(name)
        info = project.get(name)
        nodes[name] = {
            "kind": "project" if info else "environment",
            **({"file": info["file"], "line": info["line"]} if info else {}),
        }
        for dep in adjacency.get(name, []):
            di = project.get(dep)
            nodes.setdefault(dep, {
                "kind": "project" if di else "environment",
                **({"file": di["file"], "line": di["line"]} if di else {}),
            })
            edges.append({"from": name, "to": dep})
            if di and dep in adjacency and dep not in seen:
                queue.append(dep)

    return {
        "hypothesis": hid,
        "root": root_decl,
        "method": "lean-elaborated-constantinfo",
        "scope": "Exact constants from elaborated ConstantInfo for every reachable project declaration; non-project environment constants are leaves.",
        "statement_hash": st.get("frozen_sha256", ""),
        "lean_module": module,
        "indexed_project_declarations": len(project),
        "probed_visible_project_declarations": len(adjacency),
        "nodes": dict(sorted(nodes.items())),
        "edges": sorted(edges, key=lambda e: (e["from"], e["to"])),
    }


def write_exact_graph(repo: Repo, hid: str, *, max_project_nodes: int = 500, timeout: int = 240) -> tuple[Path, Path]:
    g = build_exact_graph(repo, hid, max_project_nodes=max_project_nodes, timeout=timeout)
    out = repo.root / "reports" / "dependencies"
    out.mkdir(parents=True, exist_ok=True)
    jp = out / f"{hid}.exact.json"
    jp.write_text(json.dumps(g, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    dot = ["digraph proof {", "  rankdir=LR;"]
    for n, d in g["nodes"].items():
        shape = "box" if d["kind"] == "project" else "ellipse"
        safe = n.replace('"', '\\"')
        dot.append(f'  "{safe}" [shape={shape}, label="{safe}\\n[{d["kind"]}]"];')
    for e in g["edges"]:
        a = e["from"].replace('"', '\\"'); b = e["to"].replace('"', '\\"')
        dot.append(f'  "{a}" -> "{b}";')
    dot.append("}")
    dp = out / f"{hid}.exact.dot"
    dp.write_text("\n".join(dot) + "\n", encoding="utf-8")
    return jp, dp
