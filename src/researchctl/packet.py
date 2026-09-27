from __future__ import annotations
from pathlib import Path
import json, shutil, zipfile, datetime
from .model import Repo, load_yaml
from .lean import statement_hash
from .fingerprint import write_fingerprint
from .agent_protocol import write_agent_manifest, canonical_prompt_paths

def build_packet(repo:Repo,hid:str,out:Path)->Path:
    card=repo.load_card(hid)
    write_fingerprint(repo,hid)
    write_agent_manifest(repo)
    stage=out/hid
    if stage.exists(): shutil.rmtree(stage)
    stage.mkdir(parents=True)
    files=[repo.card_path(hid), repo.root/'lit'/f'{hid}.md', repo.root/'proofs'/f'{hid}.md']
    rev=repo.root/'reviews'/hid
    if rev.exists(): files += list(rev.glob('*.yaml'))
    extra=[
        repo.root/'provenance'/f'{hid}.yaml',
        repo.root/'ablations'/hid/'manifest.yaml',
        repo.root/'ablations'/hid/'README.md',
        repo.root/'reports'/'statements'/f'{hid}.lean',
        repo.root/'reports'/'dependencies'/f'{hid}.json',
        repo.root/'reports'/'dependencies'/f'{hid}.dot',
        repo.root/'reports'/'dependencies'/f'{hid}.exact.json',
        repo.root/'reports'/'dependencies'/f'{hid}.exact.dot',
        repo.root/'reports'/'review-surface'/f'{hid}.json',
        repo.root/'reports'/'fingerprints'/f'{hid}.json',
        repo.root/'reports'/'environment'/'lock.json',
        repo.root/'reports'/'axioms'/f'{hid}.fresh.json',
        repo.root/'reports'/'axioms'/f'{hid}.print-axioms.txt',
        repo.root/'reports'/'redteam'/f'{hid}.md',
        repo.root/'reports'/'agents'/'manifest.json',
    ]
    files += [x for x in extra if x.exists()]
    runs=repo.root/'agent-runs'/hid
    if runs.exists(): files += list(runs.glob('*.yaml'))
    files += canonical_prompt_paths(repo)
    prompt_dir=repo.root/'reports'/'agents'/'prompts'
    if prompt_dir.exists(): files += list(prompt_dir.glob(f'{hid}-*.md'))
    lf=card.get('statement',{}).get('lean_file')
    if lf and (repo.root/lf).exists(): files.append(repo.root/lf)
    manifest={'id':hid,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':[]}
    import hashlib
    for f in files:
        if not f.exists(): continue
        rel=f.relative_to(repo.root)
        dest=stage/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(f,dest)
        b=f.read_bytes(); manifest['files'].append({'path':rel.as_posix(),'sha256':hashlib.sha256(b).hexdigest()})
    (stage/'MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    zip_path=out/f'{hid}-verification-packet.zip'
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for f in stage.rglob('*'):
            if f.is_file(): z.write(f,f.relative_to(stage))
    return zip_path
