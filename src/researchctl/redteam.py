from __future__ import annotations
from pathlib import Path
import json, os, urllib.request
from .model import Repo
from .semantic import diff_card, read_snapshot
from .deps import build_graph
from .agent_protocol import role_prompt, build_agent_manifest

def system_prompt(repo:Repo)->str:
    rp=role_prompt(repo,"red-team")
    return "\n\n".join([rp["common_system"], rp["output_contract"], rp["system"]])

def task_prompt(repo:Repo)->str:
    return role_prompt(repo,"red-team")["task"]


def build_prompt(repo:Repo,hid:str)->str:
    card=repo.load_card(hid)
    manifest=build_agent_manifest(repo)
    pieces=[f"# Red-team review target {hid}", f"Agent protocol SHA256: {manifest['agent_protocol_sha256']}", task_prompt(repo).replace("{H_ID}",hid),"\n## Hypothesis card\n```yaml\n"+Path(repo.card_path(hid)).read_text(encoding='utf-8')+"\n```"]
    snap=read_snapshot(repo,hid)
    if snap: pieces.append("\n## Frozen statement\n```lean\n"+snap+"\n```")
    for rel,title in [(repo.root/'proofs'/f'{hid}.md','Proof reconstruction'),(repo.root/'lit'/f'{hid}.md','Literature log'),(repo.root/'provenance'/f'{hid}.yaml','Provenance')]:
        if rel.exists(): pieces.append(f"\n## {title}\n```\n{rel.read_text(encoding='utf-8')}\n```")
    try:
        exact=repo.root/'reports'/'dependencies'/f'{hid}.exact.json'
        graph=json.loads(exact.read_text(encoding='utf-8')) if exact.exists() else build_graph(repo,hid)
        pieces.append("\n## Dependency graph\n```json\n"+json.dumps(graph,indent=2,ensure_ascii=False)+"\n```")
    except Exception as ex: pieces.append(f"\nDependency graph unavailable: {ex}")
    try: pieces.append("\n## Statement drift\n```json\n"+json.dumps(diff_card(repo,hid),indent=2,ensure_ascii=False)+"\n```")
    except Exception: pass
    pieces.append("\nAudit the claim aggressively. Identify the smallest set of human checks that could invalidate it.")
    return "\n".join(pieces)

def save_prompt(repo:Repo,hid:str)->Path:
    p=repo.root/'reports'/'redteam'/f'{hid}-prompt.md'; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(system_prompt(repo)+"\n\n"+build_prompt(repo,hid),encoding='utf-8'); return p

def run_openai(repo:Repo,hid:str,model:str)->Path:
    key=os.environ.get('OPENAI_API_KEY')
    if not key: raise RuntimeError('OPENAI_API_KEY is not set')
    payload={"model":model,"instructions":system_prompt(repo),"input":build_prompt(repo,hid),"store":False}
    req=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(payload).encode(),headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=180) as r: data=json.loads(r.read())
    text=data.get('output_text')
    if not text:
        chunks=[]
        for item in data.get('output',[]):
            for c in item.get('content',[]):
                if c.get('type')=='output_text': chunks.append(c.get('text',''))
        text='\n'.join(chunks)
    p=repo.root/'reports'/'redteam'/f'{hid}.md'; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(text or json.dumps(data,indent=2),encoding='utf-8'); return p
