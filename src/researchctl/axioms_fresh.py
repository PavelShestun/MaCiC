from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from .model import Repo, load_yaml

AX_BEGIN="MATHCICD_AXIOMS_BEGIN\t"
AX_ITEM="MATHCICD_AXIOM\t"
AX_END="MATHCICD_AXIOMS_END\t"


def _probe_source(module:str,declaration:str)->str:
    return f'''import {module}\nimport Lean.Util.FoldConsts\nimport Lean.Elab.Command\n\nopen Lean Lean.Elab Lean.Elab.Command\n\npartial def mathCICDCollectAxiomsFresh (env : Environment) (todo : List Name)\n    (visited : NameSet := {{}}) (axioms : NameSet := {{}}) : NameSet :=\n  match todo with\n  | [] => axioms\n  | n :: rest =>\n      if visited.contains n then\n        mathCICDCollectAxiomsFresh env rest visited axioms\n      else\n        let visited := visited.insert n\n        match env.find? n with\n        | none => mathCICDCollectAxiomsFresh env rest visited axioms\n        | some info =>\n            let rest := info.getUsedConstantsAsSet.foldl (fun acc d => d :: acc) rest\n            let axioms := match info with\n              | .axiomInfo _ => axioms.insert n\n              | _ => axioms\n            mathCICDCollectAxiomsFresh env rest visited axioms\n\nsyntax (name := mathCICDAxioms) "#math_cicd_axioms " ident : command\n\n@[command_elab mathCICDAxioms] def elabMathCICDAxioms : CommandElab := fun stx => do\n  let declName := stx[1].getId\n  let env := (← getEnv).setExporting false\n  if (env.find? declName).isNone then throwError m!"unknown declaration '{{declName}}'"\n  let axioms := mathCICDCollectAxiomsFresh env [declName]\n  logInfo m!"{AX_BEGIN}{{declName}}"\n  for n in axioms do logInfo m!"{AX_ITEM}{{n}}"\n  logInfo m!"{AX_END}{{declName}}"\n\n#math_cicd_axioms {declaration}\n'''


def _payload(line:str,marker:str)->str|None:
    if marker not in line: return None
    x=line.split(marker,1)[1].strip()
    return x.split()[0] if x else None


def collect(root:Path,module:str,declaration:str,timeout:int=240)->tuple[list[str],str]:
    if shutil.which('lake') is None: raise RuntimeError('lake is not available')
    reports=root/'reports'; reports.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mathcicd_axioms_',dir=str(reports)) as td:
        pth=Path(td)/'Probe.lean'; pth.write_text(_probe_source(module,declaration),encoding='utf-8')
        p=subprocess.run(['lake','env','lean',str(pth)],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
    if p.returncode: raise RuntimeError(f'fresh axiom probe failed for {declaration}:\n{p.stdout[-12000:]}')
    active=False; items=[]
    for raw in p.stdout.splitlines():
        line=raw.strip()
        if _payload(line,AX_BEGIN): active=True; continue
        if _payload(line,AX_END): active=False; continue
        x=_payload(line,AX_ITEM)
        if active and x and x not in items: items.append(x)
    if AX_BEGIN not in p.stdout or AX_END not in p.stdout:
        raise RuntimeError(f'fresh axiom probe emitted no parseable markers for {declaration}:\n{p.stdout[-6000:]}')
    return sorted(items),p.stdout


def policy_errors(repo:Repo,axioms:list[str])->list[str]:
    pp=repo.root/'research-policy.yaml'; policy=load_yaml(pp) if pp.exists() else {}
    ap=policy.get('axiom_policy',{})
    mode=ap.get('mode','allowlist')
    allow=set(ap.get('allow',['propext','Classical.choice','Quot.sound']))
    deny=set(ap.get('deny',['sorryAx']))
    deny_substrings=list(ap.get('deny_substrings',[]))
    e=[]
    for ax in axioms:
        if ax in deny or any(s in ax for s in deny_substrings):
            e.append(f'forbidden axiom {ax}')
        elif mode=='allowlist' and ax not in allow:
            e.append(f'axiom {ax} is not in axiom_policy.allow')
    return e


def audit_one(repo:Repo,hid:str,timeout:int=240)->dict:
    card=repo.load_card(hid); st=card.get('statement',{})
    mod,dec=st.get('lean_module'),st.get('lean_declaration')
    if not mod or not dec: raise ValueError(f'{hid}: lean_module and lean_declaration required')
    axioms,raw=collect(repo.root,mod,dec,timeout=timeout)
    return {
        'hypothesis':hid,'declaration':dec,'module':mod,
        'statement_hash':st.get('frozen_sha256',''),
        'method':'fresh-environment-traversal-setExporting-false',
        'axioms':axioms,'policy_errors':policy_errors(repo,axioms),
    }


def write_audit(repo:Repo,hid:str,timeout:int=240)->Path:
    data=audit_one(repo,hid,timeout=timeout)
    out=repo.root/'reports'/'axioms'; out.mkdir(parents=True,exist_ok=True)
    p=out/f'{hid}.fresh.json'; p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return p
