from __future__ import annotations
import argparse, datetime, json, os, subprocess, sys
from pathlib import Path
from .model import Repo, load_yaml, dump_yaml, STATUSES
from .gates import validate_repo, transition_errors
from .lean import statement_hash, run_lake, print_axioms
from .packet import build_packet
from .semantic import write_snapshot, diff_card, read_snapshot
from .deps import write_graph, build_graph
from .provenance import init_provenance
from .ablation import generate as generate_ablation
from .redteam import save_prompt, run_openai
from .lean_exact import write_exact_graph
from .review_surface import write as write_review_surface
from .fingerprint import write_fingerprint, build_fingerprint, domain_fingerprints
from .doctor import run as doctor_run
from .environment import write as write_env_lock
from .security import audit_workflows
from .affected import affected_hypotheses
from .axioms_fresh import write_audit as write_fresh_axiom_audit, audit_one as fresh_axiom_audit
from .references import validate_lean_reference, format_reference_help
from .reviews import review_state
from .acceptance import run as run_acceptance
from .agent_protocol import write_agent_manifest, build_agent_manifest, protocol_errors, write_assembled_prompt, init_agent_run

def root_from(p:str|None)->Path:
    return Path(p or os.getcwd()).resolve()

def cmd_new(a):
    repo=Repo(root_from(a.root)); hid=a.id.upper()
    if not hid.startswith('H-'): raise SystemExit('ID must look like H-0001')
    if repo.card_path(hid).exists(): raise SystemExit(f'{hid} already exists')
    today=datetime.date.today().isoformat()
    card={'id':hid,'title':a.title,'status':'CANDIDATE','created':today,'owners':{'research':'','formalization':''},
          'statement':{'informal':'','lean_module':'','lean_declaration':'','lean_file':'','frozen_sha256':'','freeze_commit':''},
          'assumptions':[],'definitions':[],'depends_on':[],
          'claims_of_novelty':{'status':'UNKNOWN','scope':'','closest_known_results':[]},
          'human_signoff':{'specification':'','mathematics':'','formalization':'','novelty':''},'notes':''}
    dump_yaml(repo.card_path(hid),card)
    for src,dst in [('literature_log.md',repo.root/'lit'/f'{hid}.md'),('proof_reconstruction.md',repo.root/'proofs'/f'{hid}.md')]:
        t=repo.root/'templates'/src; text=t.read_text(encoding='utf-8').replace('{{HID}}',hid).replace('{{TITLE}}',a.title)
        dst.parent.mkdir(parents=True,exist_ok=True); dst.write_text(text,encoding='utf-8')
    (repo.root/'reviews'/hid).mkdir(parents=True,exist_ok=True)
    print(repo.card_path(hid).relative_to(repo.root))

def cmd_freeze(a):
    repo=Repo(root_from(a.root)); card=repo.load_card(a.id); st=card.setdefault('statement',{})
    referrs=validate_lean_reference(repo,card)
    if referrs:
        print(f'FREEZE FAILED {a.id}', file=sys.stderr)
        for x in referrs: print('-',x,file=sys.stderr)
        print(format_reference_help(card),file=sys.stderr)
        raise SystemExit(2)
    lf=st.get('lean_file'); dec=st.get('lean_declaration')
    try:
        h,text=statement_hash(repo.root/lf,dec)
    except Exception as ex:
        print(f'FREEZE FAILED {a.id}: {ex}',file=sys.stderr)
        print(format_reference_help(card),file=sys.stderr)
        raise SystemExit(2)
    st['frozen_sha256']=h
    try: st['freeze_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo.root,text=True,stderr=subprocess.DEVNULL).strip()
    except Exception: st['freeze_commit']='UNCOMMITTED'
    card['status']='SPEC_FROZEN'; dump_yaml(repo.card_path(a.id),card)
    write_snapshot(repo,a.id,text)
    print(text); print(f'\nSHA256 {h}')

def cmd_validate(a):
    repo=Repo(root_from(a.root)); errs=validate_repo(repo)
    if a.base: errs += transition_errors(repo,a.base)
    if errs:
        print('RESEARCH GATE FAILED')
        for x in errs: print('-',x)
        raise SystemExit(1)
    print('All research gates passed.')

def cmd_status(a):
    repo=Repo(root_from(a.root)); card=repo.load_card(a.id)
    print(json.dumps(card,indent=2,ensure_ascii=False))

def cmd_transition(a):
    repo=Repo(root_from(a.root)); card=repo.load_card(a.id)
    if a.status not in STATUSES: raise SystemExit('unknown status')
    card['status']=a.status; dump_yaml(repo.card_path(a.id),card); print(f'{a.id}: {a.status}')

def cmd_audit(a):
    repo=Repo(root_from(a.root)); errs=validate_repo(repo)
    card=repo.load_card(a.id); st=card.get('statement',{})
    print(f"# Audit {a.id}\nstatus: {card.get('status')}")
    if errs:
        print('\nRepository gate errors:'); [print('-',x) for x in errs]
    if (repo.root/'lakefile.toml').exists() or (repo.root/'lakefile.lean').exists():
        rc,out=run_lake(repo.root); print(f'\n## lake build: {"PASS" if rc==0 else "FAIL"}\n{out[-5000:]}')
        if st.get('lean_module') and st.get('lean_declaration'):
            rc2,out2=print_axioms(repo.root,st['lean_module'],st['lean_declaration']); print(f'\n## #print axioms: {"PASS" if rc2==0 else "FAIL"}\n{out2[-5000:]}')
            if rc2: errs.append('Lean axiom audit failed')
        if rc: errs.append('lake build failed')
    else: print('\nNo Lake project detected; Lean build skipped.')
    if errs: raise SystemExit(1)

def cmd_packet(a):
    repo=Repo(root_from(a.root)); p=build_packet(repo,a.id,repo.root/'reports'/'packets'); print(p)

def cmd_review_init(a):
    repo=Repo(root_from(a.root)); card=repo.load_card(a.id)
    dest=repo.root/'reviews'/a.id; dest.mkdir(parents=True,exist_ok=True)
    fps=domain_fingerprints(repo,a.id); frozen=card.get('statement',{}).get('frozen_sha256','')
    for name in ('semantic','proof','literature','reproduction','final'):
        src=repo.root/'templates'/'reviews'/f'{name}.yaml'; out=dest/f'{name}.yaml'
        if not out.exists():
            data=load_yaml(src)
            if 'statement_hash_reviewed' in data: data['statement_hash_reviewed']=frozen
            if name=='proof': data['formalization_sha256_reviewed']=fps['formalization_sha256']
            if name=='literature': data['literature_sha256_reviewed']=fps['literature_sha256']
            if name=='reproduction': data['formalization_sha256_reviewed']=fps['formalization_sha256']
            if name=='final': data['evidence_sha256_reviewed']=fps['evidence_sha256']
            dump_yaml(out,data)
    print(dest.relative_to(repo.root))

def cmd_report(a):
    repo=Repo(root_from(a.root)); card=repo.load_card(a.id); errs=validate_repo(repo)
    hid=a.id; frozen=card.get('statement',{}).get('frozen_sha256','')
    print(f'# {hid} - {card.get("title")}')
    print(f'status: {card.get("status")}')
    print(f'frozen statement: {frozen or "NO"}')
    for name in ('semantic','proof','literature','reproduction','final'):
        rs=review_state(repo,hid,name)
        who=f" by {rs.get('reviewer','')}" if rs.get('reviewer') else ''
        if rs['state']=='STALE':
            print(f"{name}: PASS / STALE{who} - {'; '.join(rs['reasons'])}")
        elif rs['state']=='VALID':
            print(f"{name}: PASS / VALID{who}")
        elif rs['state']=='MISSING':
            print(f"{name}: MISSING")
        else:
            print(f"{name}: {rs['state']}{who}")
    mine=[x for x in errs if hid in x]
    print(f'gates: {"PASS" if not mine else "BLOCKED"}')
    for x in mine: print('-',x)

def cmd_axioms_all(a):
    repo=Repo(root_from(a.root)); failed=False
    outdir=repo.root/'reports'/'axioms'; outdir.mkdir(parents=True,exist_ok=True)
    for card_path in sorted((repo.root/'hypotheses').glob('H-*.yaml')):
        card=load_yaml(card_path); st=card.get('statement',{})
        mod,dec=st.get('lean_module'),st.get('lean_declaration')
        if not mod or not dec: continue
        hid=card_path.stem
        try:
            data=fresh_axiom_audit(repo,hid,timeout=a.timeout)
            (outdir/f'{hid}.fresh.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            print(f"## {hid} fresh axioms: {data['axioms']}")
            for err in data['policy_errors']:
                failed=True; print(f'AXIOM POLICY FAILED for {hid}: {err}',file=sys.stderr)
        except Exception as ex:
            failed=True; print(f'FRESH AXIOM AUDIT FAILED for {hid}: {ex}',file=sys.stderr)
        # Keep Lean's built-in report as a secondary diagnostic, not the sole gate.
        rc,out=print_axioms(repo.root,mod,dec)
        (outdir/f'{hid}.print-axioms.txt').write_text(out,encoding='utf-8')
        if rc != 0:
            failed=True; print(f'#print axioms diagnostic failed for {hid}',file=sys.stderr)
    if failed: raise SystemExit(1)


def cmd_snapshot(a):
    repo=Repo(root_from(a.root)); card=repo.load_card(a.id); st=card.get('statement',{})
    h,text=statement_hash(repo.root/st['lean_file'],st['lean_declaration'])
    frozen=st.get('frozen_sha256')
    if frozen and frozen != h and not a.force:
        raise SystemExit(f'current statement hash {h} differs from frozen {frozen}; use --force only after resetting to SPEC_DRAFT')
    p=write_snapshot(repo,a.id,text); print(p.relative_to(repo.root))

def cmd_semantic_diff(a):
    repo=Repo(root_from(a.root))
    try:
        card=repo.load_card(a.id)
        referrs=validate_lean_reference(repo,card)
        if referrs:
            print(f'SEMANTIC DIFF FAILED {a.id}',file=sys.stderr)
            for x in referrs: print('-',x,file=sys.stderr)
            print(format_reference_help(card),file=sys.stderr)
            raise SystemExit(2)
        d=diff_card(repo,a.id)
    except SystemExit:
        raise
    except Exception as ex:
        print(f'SEMANTIC DIFF FAILED {a.id}: {ex}',file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(d,indent=2,ensure_ascii=False))
    if a.fail_on_change and d.get('statement_changed'): raise SystemExit(2)

def cmd_deps(a):
    repo=Repo(root_from(a.root)); jp,dp=write_graph(repo,a.id); g=build_graph(repo,a.id)
    print(f'{jp.relative_to(repo.root)}\n{dp.relative_to(repo.root)}')
    print(f"nodes={len(g['nodes'])} edges={len(g['edges'])} method={g['method']}")

def cmd_provenance_init(a):
    repo=Repo(root_from(a.root)); print(init_provenance(repo,a.id).relative_to(repo.root))

def cmd_ablate(a):
    repo=Repo(root_from(a.root)); print(generate_ablation(repo,a.id).relative_to(repo.root))

def cmd_redteam(a):
    repo=Repo(root_from(a.root))
    if a.run_openai:
        p=run_openai(repo,a.id,a.model or os.environ.get('MATH_CICD_REDTEAM_MODEL','gpt-5'))
    else:
        p=save_prompt(repo,a.id)
    print(p.relative_to(repo.root))



def cmd_deps_exact(a):
    repo=Repo(root_from(a.root))
    jp,dp=write_exact_graph(repo,a.id,max_project_nodes=a.max_project_nodes,timeout=a.timeout)
    print(f'{jp.relative_to(repo.root)}\n{dp.relative_to(repo.root)}')



def cmd_deps_exact_all(a):
    repo=Repo(root_from(a.root)); failed=[]; count=0
    for cp in sorted((repo.root/'hypotheses').glob('H-*.yaml')):
        card=load_yaml(cp); st=card.get('statement',{})
        if not st.get('lean_module') or not st.get('lean_declaration') or not st.get('frozen_sha256'):
            continue
        try:
            jp,dp=write_exact_graph(repo,cp.stem,max_project_nodes=a.max_project_nodes,timeout=a.timeout)
            print(f'{cp.stem}: {jp.relative_to(repo.root)}')
            try: write_review_surface(repo,cp.stem)
            except Exception as ex: print(f'{cp.stem}: review-surface warning: {ex}',file=sys.stderr)
            count+=1
        except Exception as ex:
            failed.append((cp.stem,str(ex))); print(f'{cp.stem}: FAIL {ex}',file=sys.stderr)
    print(f'exact dependency reports: {count}')
    if failed: raise SystemExit(1)

def cmd_review_surface(a):
    repo=Repo(root_from(a.root)); p=write_review_surface(repo,a.id); print(p.relative_to(repo.root))

def cmd_fingerprint(a):
    repo=Repo(root_from(a.root)); p=write_fingerprint(repo,a.id); fps=domain_fingerprints(repo,a.id)
    print(p.relative_to(repo.root))
    for key in ('statement_sha256','formalization_sha256','literature_sha256','environment_sha256','agent_protocol_sha256','evidence_sha256'):
        print(f'{key}: {fps[key]}')





def cmd_workflow_audit(a):
    repo=Repo(root_from(a.root)); errors,warnings=audit_workflows(repo)
    for w in warnings: print(f'WARNING: {w}')
    for e in errors: print(f'ERROR: {e}')
    if errors: raise SystemExit(1)

def cmd_affected(a):
    repo=Repo(root_from(a.root))
    for hid in affected_hypotheses(repo,a.base): print(hid)

def cmd_env_lock(a):
    repo=Repo(root_from(a.root)); p=write_env_lock(repo); print(p.relative_to(repo.root))

def cmd_doctor(a):
    repo=Repo(root_from(a.root)); d=doctor_run(repo); print(json.dumps(d,indent=2,ensure_ascii=False))
    if a.require_lean and not d['ready_for_lean_ci']: raise SystemExit(2)


def cmd_acceptance(a):
    results=run_acceptance(); failed=False
    print('# Math CI/CD acceptance suite')
    for r in results:
        line=f"{r['result']}: {r['case']}"
        if r.get('detail'): line += f" - {r['detail']}"
        print(line)
        failed = failed or r['result'] != 'PASS'
    if failed: raise SystemExit(1)

def cmd_agent_manifest(a):
    repo=Repo(root_from(a.root)); errs=protocol_errors(repo)
    if errs:
        for e in errs: print(f'ERROR: {e}')
        raise SystemExit(1)
    p=write_agent_manifest(repo); data=build_agent_manifest(repo)
    print(p.relative_to(repo.root))
    print(f"agent_protocol_sha256: {data['agent_protocol_sha256']}")
    for role,h in sorted(data['role_hashes'].items()):
        print(f"{role}: {h}")


def cmd_agent_prompt(a):
    repo=Repo(root_from(a.root)); errs=protocol_errors(repo)
    if errs:
        for e in errs: print(f"ERROR: {e}")
        raise SystemExit(1)
    p=write_assembled_prompt(repo,a.role,a.id); print(p.relative_to(repo.root))

def cmd_agent_run_init(a):
    repo=Repo(root_from(a.root)); errs=protocol_errors(repo)
    if errs:
        for e in errs: print(f"ERROR: {e}")
        raise SystemExit(1)
    write_assembled_prompt(repo,a.role,a.id)
    p=init_agent_run(repo,a.id,a.role,a.model); print(p.relative_to(repo.root))


def main():
    p=argparse.ArgumentParser(prog='researchctl'); p.add_argument('--root')
    s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('new'); q.add_argument('id'); q.add_argument('title'); q.set_defaults(fn=cmd_new)
    q=s.add_parser('freeze'); q.add_argument('id'); q.set_defaults(fn=cmd_freeze)
    q=s.add_parser('validate'); q.add_argument('--base'); q.set_defaults(fn=cmd_validate)
    q=s.add_parser('status'); q.add_argument('id'); q.set_defaults(fn=cmd_status)
    q=s.add_parser('transition'); q.add_argument('id'); q.add_argument('status'); q.set_defaults(fn=cmd_transition)
    q=s.add_parser('audit'); q.add_argument('id'); q.set_defaults(fn=cmd_audit)
    q=s.add_parser('packet'); q.add_argument('id'); q.set_defaults(fn=cmd_packet)
    q=s.add_parser('review-init'); q.add_argument('id'); q.set_defaults(fn=cmd_review_init)
    q=s.add_parser('report'); q.add_argument('id'); q.set_defaults(fn=cmd_report)
    q=s.add_parser('axioms-all'); q.add_argument('--timeout',type=int,default=240); q.set_defaults(fn=cmd_axioms_all)
    q=s.add_parser('snapshot'); q.add_argument('id'); q.add_argument('--force',action='store_true'); q.set_defaults(fn=cmd_snapshot)
    q=s.add_parser('semantic-diff'); q.add_argument('id'); q.add_argument('--fail-on-change',action='store_true'); q.set_defaults(fn=cmd_semantic_diff)
    q=s.add_parser('deps'); q.add_argument('id'); q.set_defaults(fn=cmd_deps)
    q=s.add_parser('deps-exact'); q.add_argument('id'); q.add_argument('--max-project-nodes',type=int,default=500); q.add_argument('--timeout',type=int,default=240); q.set_defaults(fn=cmd_deps_exact)
    q=s.add_parser('deps-exact-all'); q.add_argument('--max-project-nodes',type=int,default=500); q.add_argument('--timeout',type=int,default=240); q.set_defaults(fn=cmd_deps_exact_all)
    q=s.add_parser('review-surface'); q.add_argument('id'); q.set_defaults(fn=cmd_review_surface)
    q=s.add_parser('fingerprint'); q.add_argument('id'); q.set_defaults(fn=cmd_fingerprint)
    q=s.add_parser('workflow-audit'); q.set_defaults(fn=cmd_workflow_audit)
    q=s.add_parser('affected'); q.add_argument('--base',required=True); q.set_defaults(fn=cmd_affected)
    q=s.add_parser('env-lock'); q.set_defaults(fn=cmd_env_lock)
    q=s.add_parser('doctor'); q.add_argument('--require-lean',action='store_true'); q.set_defaults(fn=cmd_doctor)
    q=s.add_parser('acceptance'); q.set_defaults(fn=cmd_acceptance)
    q=s.add_parser('agent-manifest'); q.set_defaults(fn=cmd_agent_manifest)
    q=s.add_parser('agent-prompt'); q.add_argument('role'); q.add_argument('id'); q.set_defaults(fn=cmd_agent_prompt)
    q=s.add_parser('agent-run-init'); q.add_argument('role'); q.add_argument('id'); q.add_argument('--model',required=True); q.set_defaults(fn=cmd_agent_run_init)
    q=s.add_parser('provenance-init'); q.add_argument('id'); q.set_defaults(fn=cmd_provenance_init)
    q=s.add_parser('ablate'); q.add_argument('id'); q.set_defaults(fn=cmd_ablate)
    q=s.add_parser('redteam'); q.add_argument('id'); q.add_argument('--run-openai',action='store_true'); q.add_argument('--model'); q.set_defaults(fn=cmd_redteam)
    a=p.parse_args(); a.fn(a)
if __name__=='__main__': main()
