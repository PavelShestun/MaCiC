from __future__ import annotations
from pathlib import Path
from typing import Any
import datetime, subprocess
from .model import Repo, STATUSES, TRANSITIONS, load_yaml
from .lean import find_placeholders, statement_hash
from .semantic import read_snapshot
from .provenance import validate_provenance
from .ablation import validate as validate_ablation
from .fingerprint import domain_fingerprints
from .environment import validate as validate_environment_lock
from .references import validate_lean_reference

ORDER = {s:i for i,s in enumerate(["CANDIDATE","SPEC_DRAFT","SPEC_FROZEN","FORMALIZED","SEMANTIC_REVIEWED","PROOF_RECONSTRUCTED","NOVELTY_REVIEWED","INDEPENDENTLY_REPRODUCED","VERIFIED_RESULT"])}

def get(d:dict[str,Any], dotted:str, default=None):
    cur:Any=d
    for p in dotted.split('.'):
        if not isinstance(cur,dict) or p not in cur: return default
        cur=cur[p]
    return cur

def load_review(root:Path,hid:str,name:str):
    p=root/'reviews'/hid/f'{name}.yaml'
    if not p.exists(): return None
    try: return load_yaml(p)
    except Exception: return None

def passing_review(root:Path,hid:str,name:str)->bool:
    d=load_review(root,hid,name)
    return bool(d and d.get('reviewer') and d.get('date') and d.get('decision') == 'pass' and d.get('summary'))



def review_content_errors(repo:Repo, hid:str, name:str, card:dict, policy:dict)->list[str]:
    d=load_review(repo.root,hid,name)
    if not d or d.get('decision') != 'pass': return []
    e=[]
    prefix=f"{hid}: {name} review"
    if policy.get('require_github_login_on_reviews',False) and not d.get('github_login'):
        e.append(f"{prefix} needs github_login")
    if name=='semantic':
        for k in ('definitions_match_intent','assumptions_explicit','conclusion_matches_claim','hidden_trivialization_checked'):
            if d.get(k) is not True: e.append(f"{prefix} requires {k}: true")
    elif name=='proof':
        for k in ('human_sketch_complete','key_transitions_understood','no_circularity_found','no_hidden_trivialization_found','review_surface_checked'):
            if d.get(k) is not True: e.append(f"{prefix} requires {k}: true")
    elif name=='literature':
        if not d.get('search_completed_through'): e.append(f"{prefix} needs search_completed_through date")
        if not d.get('query_families'): e.append(f"{prefix} needs non-empty query_families")
        if not d.get('databases_or_indexes'): e.append(f"{prefix} needs non-empty databases_or_indexes")
        claim=card.get('claims_of_novelty',{}).get('status','UNKNOWN')
        if claim not in {'NOT_APPLICABLE','KNOWN'} and policy.get('require_citation_chasing_for_novelty',True):
            for k in ('backward_citation_chase','forward_citation_chase','proof_fingerprint_search'):
                if d.get(k) is not True: e.append(f"{prefix} requires {k}: true")
        if d.get('novelty_assessment') in {None,'','UNKNOWN'}:
            e.append(f"{prefix} novelty_assessment is unresolved")
    elif name=='reproduction':
        for k in ('clean_checkout','lean_build','statement_hash_matches','proof_reconstructed_without_generator_context'):
            if d.get(k) is not True: e.append(f"{prefix} requires {k}: true")
        if not d.get('commit'): e.append(f"{prefix} needs reproduced commit SHA")
        primary=card.get('owners',{}).get('research')
        if policy.get('require_reproducer_distinct_from_primary_author',True) and primary and d.get('reviewer')==primary:
            e.append(f"{prefix} reviewer must differ from primary research owner")
    elif name=='final':
        for k in ('all_required_evidence_checked','claim_language_approved','reproducibility_approved'):
            if d.get(k) is not True: e.append(f"{prefix} requires {k}: true")
    return e

def validate_card(repo:Repo, card_path:Path) -> list[str]:
    e=[]
    try: d=load_yaml(card_path)
    except Exception as ex: return [f"{card_path}: {ex}"]
    hid=d.get('id')
    if hid != card_path.stem: e.append(f"{card_path}: id must equal filename")
    for k in ('id','title','status','created','statement'):
        if not d.get(k): e.append(f"{card_path}: missing {k}")
    status=d.get('status')
    if status not in STATUSES: e.append(f"{card_path}: invalid status {status}"); return e
    e.extend(f"{card_path}: {x}" for x in validate_lean_reference(repo,d))
    for p in [repo.root/'lit'/f'{hid}.md', repo.root/'proofs'/f'{hid}.md']:
        if not p.exists(): e.append(f"{card_path}: missing {p.relative_to(repo.root)}")
    if status in ORDER and ORDER[status] >= ORDER['SPEC_FROZEN']:
        lf=get(d,'statement.lean_file'); dec=get(d,'statement.lean_declaration'); frozen=get(d,'statement.frozen_sha256')
        if not all([lf,dec,frozen]): e.append(f"{card_path}: frozen-or-later requires lean_file, lean_declaration, frozen_sha256")
        elif (repo.root/lf).exists():
            try:
                now,_=statement_hash(repo.root/lf,dec)
                if now != frozen: e.append(f"{card_path}: FROZEN_STATEMENT_DRIFT expected={frozen} current={now}")
            except Exception as ex: e.append(f"{card_path}: statement extraction failed: {ex}")
        else: e.append(f"{card_path}: lean file does not exist: {lf}")
    policy_path=repo.root/'research-policy.yaml'
    policy=load_yaml(policy_path) if policy_path.exists() else {}
    required_reviews={
        'SEMANTIC_REVIEWED':['semantic'],
        'PROOF_RECONSTRUCTED':['semantic','proof'],
        'NOVELTY_REVIEWED':['semantic','proof','literature'],
        'INDEPENDENTLY_REPRODUCED':['semantic','proof','literature','reproduction'],
        'VERIFIED_RESULT':['semantic','proof','literature','reproduction','final'],
    }
    if status in required_reviews:
        for name in required_reviews[status]:
            if not passing_review(repo.root,hid,name): e.append(f"{card_path}: status {status} requires a PASS review at reviews/{hid}/{name}.yaml")
            else: e.extend(f"{card_path}: {x}" for x in review_content_errors(repo,hid,name,d,policy))
    if status in {'SEMANTIC_REVIEWED','PROOF_RECONSTRUCTED','NOVELTY_REVIEWED','INDEPENDENTLY_REPRODUCED','VERIFIED_RESULT'}:
        sem=load_review(repo.root,hid,'semantic')
        frozen=get(d,'statement.frozen_sha256')
        if sem and sem.get('statement_hash_reviewed') != frozen:
            e.append(f"{card_path}: semantic review is for a different statement hash")
    if status in {'INDEPENDENTLY_REPRODUCED','VERIFIED_RESULT'}:
        rep=load_review(repo.root,hid,'reproduction')
        frozen=get(d,'statement.frozen_sha256')
        if rep and rep.get('statement_hash_reviewed') != frozen:
            e.append(f"{card_path}: reproduction review is for a different statement hash")
    fps=domain_fingerprints(repo,hid)
    if status in {'PROOF_RECONSTRUCTED','NOVELTY_REVIEWED','INDEPENDENTLY_REPRODUCED','VERIFIED_RESULT'}:
        proofrev=load_review(repo.root,hid,'proof')
        frozen=get(d,'statement.frozen_sha256')
        if proofrev and proofrev.get('statement_hash_reviewed') != frozen:
            e.append(f"{card_path}: proof review is for a different statement hash")
        if proofrev and proofrev.get('formalization_sha256_reviewed') != fps['formalization_sha256']:
            e.append(f"{card_path}: proof review is stale; formalization/environment changed")
    if status in {'NOVELTY_REVIEWED','INDEPENDENTLY_REPRODUCED','VERIFIED_RESULT'}:
        litrev=load_review(repo.root,hid,'literature')
        frozen=get(d,'statement.frozen_sha256')
        if litrev and litrev.get('statement_hash_reviewed') not in {None,'',frozen}:
            e.append(f"{card_path}: literature review is for a different statement hash")
        if policy_path.exists() and policy.get('require_fresh_literature_review',True) and litrev and litrev.get('literature_sha256_reviewed') != fps['literature_sha256']:
            e.append(f"{card_path}: literature review is stale; literature/provenance evidence changed")
    if status in {'INDEPENDENTLY_REPRODUCED','VERIFIED_RESULT'}:
        rep=load_review(repo.root,hid,'reproduction')
        if policy_path.exists() and policy.get('require_fresh_reproduction_review',True) and rep and rep.get('formalization_sha256_reviewed') != fps['formalization_sha256']:
            e.append(f"{card_path}: reproduction review is stale; formalization/environment changed")
    if status == 'VERIFIED_RESULT':
        final=load_review(repo.root,hid,'final')
        if policy_path.exists() and policy.get('require_fresh_final_review',True) and final and final.get('evidence_sha256_reviewed') != fps['evidence_sha256']:
            e.append(f"{card_path}: final review is stale; evidence bundle changed")
    if status in ORDER and ORDER[status] >= ORDER['SPEC_FROZEN']:
        snapshot=read_snapshot(repo,hid)
        if policy.get('require_statement_snapshot',True) and not snapshot:
            e.append(f"{card_path}: missing frozen statement snapshot reports/statements/{hid}.lean")
    if status in {'NOVELTY_REVIEWED','INDEPENDENTLY_REPRODUCED','VERIFIED_RESULT'} and policy.get('require_provenance_before_novelty',True):
        e.extend(f"{card_path}: {x}" for x in validate_provenance(repo,hid))
    if status in {'NOVELTY_REVIEWED','INDEPENDENTLY_REPRODUCED','VERIFIED_RESULT'} and policy.get('require_ablation_before_novelty',False):
        e.extend(f"{card_path}: {x}" for x in validate_ablation(repo,hid,required=True))
    if status == 'VERIFIED_RESULT':
        if policy.get('require_exact_dependencies_before_final',True):
            dep=repo.root/'reports'/'dependencies'/f'{hid}.exact.json'
            if not dep.exists(): e.append(f"{card_path}: VERIFIED_RESULT requires exact Lean dependency report; run researchctl deps-exact {hid}")
            else:
                import json
                try:
                    gd=json.loads(dep.read_text(encoding='utf-8'))
                    if gd.get('statement_hash') != get(d,'statement.frozen_sha256'):
                        e.append(f"{card_path}: exact dependency report is for a different statement hash")
                except Exception as ex: e.append(f"{card_path}: invalid exact dependency report: {ex}")
        if policy.get('require_environment_lock_before_final',True):
            e.extend(f"{card_path}: {x}" for x in validate_environment_lock(repo))
        signers=[]
        for k in ('specification','mathematics','formalization','novelty'):
            v=get(d,f'human_signoff.{k}')
            if not v: e.append(f"{card_path}: VERIFIED_RESULT requires human_signoff.{k}")
            else: signers.append(str(v))
        min_signers=int(policy.get('minimum_distinct_final_signers',2))
        if len(set(signers)) < min_signers: e.append(f"{card_path}: VERIFIED_RESULT requires at least {min_signers} distinct human signers")
        allowed=set(policy.get('novelty_status_for_verified',['SUPPORTED','NOT_APPLICABLE']))
        if get(d,'claims_of_novelty.status') not in allowed:
            e.append(f"{card_path}: VERIFIED_RESULT novelty status must be one of {sorted(allowed)}")
    return e

def validate_repo(repo:Repo)->list[str]:
    e=[]
    for card in sorted((repo.root/'hypotheses').glob('H-*.yaml')): e.extend(validate_card(repo,card))
    for path in sorted(repo.root.rglob('*.lean')):
        if '.lake' in path.parts: continue
        for line,tok in find_placeholders(path): e.append(f"{path.relative_to(repo.root)}:{line}: forbidden placeholder {tok}")
    return e

def git_show_yaml(root:Path, ref:str, rel:Path):
    p=subprocess.run(['git','show',f'{ref}:{rel.as_posix()}'],cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    if p.returncode: return None
    import yaml
    try: return yaml.safe_load(p.stdout) or {}
    except Exception: return None

def transition_errors(repo:Repo, base_ref:str)->list[str]:
    e=[]
    for card in sorted((repo.root/'hypotheses').glob('H-*.yaml')):
        new=load_yaml(card); old=git_show_yaml(repo.root,base_ref,card.relative_to(repo.root))
        if not old: continue
        a,b=old.get('status'),new.get('status')
        if a==b: continue
        if a in TRANSITIONS and b not in TRANSITIONS[a]: e.append(f"{card}: illegal status transition {a} -> {b}")
        old_hash=get(old,'statement.frozen_sha256'); new_hash=get(new,'statement.frozen_sha256')
        if old_hash and new_hash and old_hash != new_hash and b != 'SPEC_DRAFT':
            e.append(f"{card}: frozen statement hash changed; status must reset to SPEC_DRAFT before re-review")
    return e
