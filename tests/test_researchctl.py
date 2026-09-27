import json
from pathlib import Path
from researchctl.lean import strip_comments_and_strings, find_placeholders, extract_declaration_header, statement_hash
from researchctl.model import TRANSITIONS

def test_comment_stripping_does_not_flag_sorry_in_comment(tmp_path: Path):
    p=tmp_path/'A.lean'
    p.write_text('-- sorry\n/-- admit -/\ntheorem ok : True := by\n  trivial\n',encoding='utf-8')
    assert find_placeholders(p) == []

def test_real_sorry_is_flagged(tmp_path: Path):
    p=tmp_path/'A.lean'; p.write_text('theorem bad : True := by\n  sorry\n',encoding='utf-8')
    assert find_placeholders(p) == [(2,'sorry')]

def test_statement_extraction(tmp_path: Path):
    p=tmp_path/'A.lean'; p.write_text('theorem foo (n : Nat) : n = n := by\n  rfl\n',encoding='utf-8')
    h=extract_declaration_header(p,'foo')
    assert h == 'theorem foo (n : Nat) : n = n'
    assert len(statement_hash(p,'foo')[0]) == 64

def test_verified_not_directly_from_candidate():
    assert 'VERIFIED_RESULT' not in TRANSITIONS['CANDIDATE']
from researchctl.semantic import semantic_diff, binders
from researchctl.model import Repo, dump_yaml
from researchctl.ablation import generate as generate_ablation


def test_semantic_diff_detects_conclusion_change():
    old='theorem foo (n : Nat) (h : n > 0) : n = n'
    new='theorem foo (n : Nat) (h : n > 0) : n > 0'
    d=semantic_diff(old,new)
    assert d['statement_changed']
    assert d['conclusion_changed']
    assert not d['binders_changed']


def test_binders_extracts_hypothesis():
    bs=binders('theorem foo (n : Nat) (h : n > 0) : n = n')
    assert [x['name'] for x in bs] == ['n','h']


def test_ablation_manifest_bound_to_statement_hash(tmp_path: Path):
    (tmp_path/'hypotheses').mkdir(); (tmp_path/'reports'/'statements').mkdir(parents=True)
    dump_yaml(tmp_path/'hypotheses'/'H-0001.yaml', {'id':'H-0001','statement':{'frozen_sha256':'abc'}})
    (tmp_path/'reports'/'statements'/'H-0001.lean').write_text('theorem foo (n : Nat) (h : n > 0) : n = n\n')
    p=generate_ablation(Repo(tmp_path),'H-0001')
    assert 'statement_hash: abc' in p.read_text()

from researchctl.deps import project_declarations
from researchctl.lean_exact import parse_batch_output
from researchctl.fingerprint import domain_fingerprints
from researchctl.security import audit_workflows


def test_project_declarations_qualifies_namespace(tmp_path: Path):
    p=tmp_path/'N.lean'
    p.write_text('namespace A\ntheorem foo : True := by trivial\nend A\n',encoding='utf-8')
    d=project_declarations(tmp_path)
    assert 'A.foo' in d


def test_exact_dependency_output_parser():
    out='''x:1: info: MATHCICD_DECL_BEGIN\tA.foo\nx:1: info: MATHCICD_DEP\tNat\nx:1: info: MATHCICD_DEP\tA.bar\nx:1: info: MATHCICD_DECL_END\tA.foo\n'''
    g,missing=parse_batch_output(out)
    assert missing == []
    assert g['A.foo'] == ['A.bar','Nat']


def test_domain_fingerprint_changes_with_literature(tmp_path: Path):
    (tmp_path/'hypotheses').mkdir(); (tmp_path/'lit').mkdir(); (tmp_path/'proofs').mkdir()
    dump_yaml(tmp_path/'hypotheses'/'H-0001.yaml', {'id':'H-0001','statement':{'frozen_sha256':'abc'}})
    (tmp_path/'lit'/'H-0001.md').write_text('one',encoding='utf-8')
    (tmp_path/'proofs'/'H-0001.md').write_text('proof',encoding='utf-8')
    a=domain_fingerprints(Repo(tmp_path),'H-0001')['literature_sha256']
    (tmp_path/'lit'/'H-0001.md').write_text('two',encoding='utf-8')
    b=domain_fingerprints(Repo(tmp_path),'H-0001')['literature_sha256']
    assert a != b


def test_workflow_audit_rejects_pull_request_target(tmp_path: Path):
    d=tmp_path/'.github'/'workflows'; d.mkdir(parents=True)
    (d/'bad.yml').write_text('on:\n  pull_request_target:\npermissions:\n  contents: read\n',encoding='utf-8')
    errors,_=audit_workflows(Repo(tmp_path))
    assert any('pull_request_target' in e for e in errors)

from researchctl.gates import validate_card
from researchctl.fingerprint import domain_fingerprints


def _minimal_repo(tmp_path: Path, status: str='SPEC_FROZEN') -> Repo:
    for d in ['hypotheses','lit','proofs','reports/statements','reviews/H-0001','templates/reviews']:
        (tmp_path/d).mkdir(parents=True,exist_ok=True)
    lean=tmp_path/'A.lean'; lean.write_text('theorem foo (n : Nat) : n = n := by\n  rfl\n',encoding='utf-8')
    from researchctl.lean import statement_hash
    h,text=statement_hash(lean,'foo')
    (tmp_path/'reports/statements/H-0001.lean').write_text(text+'\n',encoding='utf-8')
    (tmp_path/'lit/H-0001.md').write_text('lit evidence',encoding='utf-8')
    (tmp_path/'proofs/H-0001.md').write_text('proof evidence',encoding='utf-8')
    dump_yaml(tmp_path/'hypotheses/H-0001.yaml',{
        'id':'H-0001','title':'x','created':'2026-01-01','status':status,
        'owners':{'research':'alice'},
        'statement':{'lean_file':'A.lean','lean_declaration':'foo','lean_module':'A','frozen_sha256':h},
        'claims_of_novelty':{'status':'UNKNOWN'},
        'human_signoff':{'specification':'','mathematics':'','formalization':'','novelty':''},
    })
    dump_yaml(tmp_path/'research-policy.yaml',{'require_statement_snapshot':True})
    return Repo(tmp_path)


def test_proof_review_becomes_stale_when_formalization_changes(tmp_path: Path):
    repo=_minimal_repo(tmp_path,'PROOF_RECONSTRUCTED')
    fps=domain_fingerprints(repo,'H-0001')
    dump_yaml(tmp_path/'reviews/H-0001/semantic.yaml',{
        'reviewer':'s','date':'2026-01-02','decision':'pass','summary':'ok',
        'statement_hash_reviewed':repo.load_card('H-0001')['statement']['frozen_sha256'],
        'definitions_match_intent':True,'assumptions_explicit':True,'conclusion_matches_claim':True,'hidden_trivialization_checked':True,
    })
    dump_yaml(tmp_path/'reviews/H-0001/proof.yaml',{
        'reviewer':'p','date':'2026-01-02','decision':'pass','summary':'ok',
        'statement_hash_reviewed':repo.load_card('H-0001')['statement']['frozen_sha256'],
        'formalization_sha256_reviewed':fps['formalization_sha256'],
        'human_sketch_complete':True,'key_transitions_understood':True,'no_circularity_found':True,'no_hidden_trivialization_found':True,'review_surface_checked':True,
    })
    assert validate_card(repo,repo.card_path('H-0001')) == []
    (tmp_path/'proofs/H-0001.md').write_text('changed proof evidence',encoding='utf-8')
    errs=validate_card(repo,repo.card_path('H-0001'))
    assert any('proof review is stale' in e for e in errs)


def test_verified_requires_exact_dependency_report_and_environment_lock(tmp_path: Path):
    repo=_minimal_repo(tmp_path,'VERIFIED_RESULT')
    # This test intentionally leaves reviews/signoffs incomplete too; assert the
    # infrastructure-specific final gates are present among the failures.
    errs=validate_card(repo,repo.card_path('H-0001'))
    assert any('exact Lean dependency report' in e for e in errs)
    assert any('environment/lock.json' in e for e in errs)

from researchctl.axioms_fresh import policy_errors


def test_axiom_allowlist_blocks_custom_axiom(tmp_path: Path):
    dump_yaml(tmp_path/'research-policy.yaml', {'axiom_policy': {'mode':'allowlist','allow':['propext','Classical.choice','Quot.sound'],'deny':['sorryAx']}})
    repo=Repo(tmp_path)
    assert policy_errors(repo,['Classical.choice']) == []
    assert any('not in axiom_policy.allow' in e for e in policy_errors(repo,['MyAxiom']))
    assert any('forbidden axiom' in e for e in policy_errors(repo,['sorryAx']))

from researchctl.references import validate_lean_reference
from researchctl.reviews import review_state
from researchctl.acceptance import run as run_acceptance


def test_candidate_bad_lean_reference_is_rejected(tmp_path: Path):
    (tmp_path/'hypotheses').mkdir(); (tmp_path/'lit').mkdir(); (tmp_path/'proofs').mkdir()
    (tmp_path/'lit/H-0001.md').write_text('x',encoding='utf-8')
    (tmp_path/'proofs/H-0001.md').write_text('x',encoding='utf-8')
    dump_yaml(tmp_path/'hypotheses/H-0001.yaml',{
        'id':'H-0001','title':'x','created':'2026-01-01','status':'CANDIDATE',
        'statement':{'lean_file':'MathCI.Example','lean_module':'MathCI.bad','lean_declaration':'MathCI.foo'},
    })
    errs=validate_card(Repo(tmp_path),tmp_path/'hypotheses/H-0001.yaml')
    assert any('INVALID_LEAN_REFERENCE' in e for e in errs)


def test_review_state_reports_stale_before_gate_stage(tmp_path: Path):
    repo=_minimal_repo(tmp_path,'SPEC_FROZEN')
    fps=domain_fingerprints(repo,'H-0001')
    dump_yaml(tmp_path/'reviews/H-0001/proof.yaml',{
        'reviewer':'p','date':'2026-01-02','decision':'pass','summary':'ok',
        'statement_hash_reviewed':repo.load_card('H-0001')['statement']['frozen_sha256'],
        'formalization_sha256_reviewed':fps['formalization_sha256'],
    })
    assert review_state(repo,'H-0001','proof')['state']=='VALID'
    (tmp_path/'proofs/H-0001.md').write_text('changed',encoding='utf-8')
    assert review_state(repo,'H-0001','proof')['state']=='STALE'


def test_acceptance_suite_passes():
    results=run_acceptance()
    assert results
    assert all(x['result']=='PASS' for x in results), results

from researchctl.agent_protocol import build_agent_manifest, write_agent_manifest


def test_agent_protocol_hash_changes_when_prompt_changes(tmp_path: Path):
    (tmp_path/'agents/common').mkdir(parents=True)
    (tmp_path/'agents/formalizer').mkdir(parents=True)
    (tmp_path/'VERSION').write_text('0.4.2\n', encoding='utf-8')
    (tmp_path/'agents/common/SYSTEM.md').write_text('common', encoding='utf-8')
    (tmp_path/'agents/common/OUTPUT_CONTRACT.md').write_text('contract', encoding='utf-8')
    (tmp_path/'agents/formalizer/SYSTEM.md').write_text('system', encoding='utf-8')
    (tmp_path/'agents/formalizer/TASK.md').write_text('task one', encoding='utf-8')
    (tmp_path/'agents/formalizer/OUTPUT_SCHEMA.yaml').write_text('type: object\n', encoding='utf-8')
    repo=Repo(tmp_path)
    a=build_agent_manifest(repo)['agent_protocol_sha256']
    (tmp_path/'agents/formalizer/TASK.md').write_text('task two', encoding='utf-8')
    b=build_agent_manifest(repo)['agent_protocol_sha256']
    assert a != b


def test_agent_manifest_contains_role_hashes(tmp_path: Path):
    (tmp_path/'agents/common').mkdir(parents=True)
    (tmp_path/'agents/skeptic').mkdir(parents=True)
    for p,text in [
        ('agents/common/SYSTEM.md','common'),
        ('agents/common/OUTPUT_CONTRACT.md','contract'),
        ('agents/skeptic/SYSTEM.md','system'),
        ('agents/skeptic/TASK.md','task'),
        ('agents/skeptic/OUTPUT_SCHEMA.yaml','type: object\n'),
    ]:
        (tmp_path/p).write_text(text,encoding='utf-8')
    repo=Repo(tmp_path)
    p=write_agent_manifest(repo)
    data=__import__('json').loads(p.read_text(encoding='utf-8'))
    assert 'common' in data['role_hashes']
    assert 'skeptic' in data['role_hashes']
    assert len(data['agent_protocol_sha256']) == 64

from researchctl.blind_context import build_context, audit_profiles, audit_packet_dir, load_profile, export_context


def _blind_repo(tmp_path: Path) -> Repo:
    for d in ['hypotheses','reports/statements','agents/common','agents/skeptic','agents/profiles']:
        (tmp_path/d).mkdir(parents=True,exist_ok=True)
    (tmp_path/'VERSION').write_text('0.4.3\n',encoding='utf-8')
    dump_yaml(tmp_path/'hypotheses/H-0042.yaml',{
        'id':'H-0042','title':'Secret Scaling Project Main Theorem','status':'SPEC_FROZEN',
        'statement':{'frozen_sha256':'abc','informal':'For every n, n = n.','lean_declaration':'Secret.MainTheorem','lean_module':'Secret'},
        'definitions':[{'name':'SecretObject','description':'an arbitrary object'}],
        'assumptions':['n is a natural number'],
    })
    (tmp_path/'reports/statements/H-0042.lean').write_text('theorem Secret.MainTheorem (n : Nat) : n = n\n',encoding='utf-8')
    (tmp_path/'agents/common/SYSTEM.md').write_text('global project workflow hidden',encoding='utf-8')
    (tmp_path/'agents/common/OUTPUT_CONTRACT.md').write_text('contract',encoding='utf-8')
    (tmp_path/'agents/skeptic/SYSTEM.md').write_text('skeptic system',encoding='utf-8')
    (tmp_path/'agents/skeptic/TASK.md').write_text('skeptic task',encoding='utf-8')
    (tmp_path/'agents/skeptic/OUTPUT_SCHEMA.yaml').write_text('type: object\n',encoding='utf-8')
    dump_yaml(tmp_path/'agents/profiles/skeptic-blind.yaml',{
        'name':'skeptic-blind','roles':['skeptic'],'prompt_mode':'blind',
        'include':['frozen_statement','definitions','assumptions'],
        'exclude':['project_goal','existing_proof'],
        'task':'Try to falsify the supplied claim without assuming it is true.',
        'sanitize':{'hide_hypothesis_id':True,'neutralize_identifiers':True},
        'leakage':{'forbid_project_title':True,'forbid_hypothesis_id':True,'forbid_global_stage_terms':True},
    })
    return Repo(tmp_path)


def test_blind_context_hides_hid_title_and_role_workflow(tmp_path: Path):
    repo=_blind_repo(tmp_path)
    p=build_context(repo,'H-0042','skeptic','skeptic-blind','RUN1')
    visible=p/'agent-visible'; audit=p/'audit-only'
    assert visible.is_dir() and audit.is_dir()
    all_text='\n'.join(x.read_text(encoding='utf-8') for x in visible.iterdir() if x.is_file())
    assert 'H-0042' not in all_text
    assert 'Secret Scaling Project Main Theorem' not in all_text
    assert 'global project workflow hidden' not in all_text
    assert 'Secret.MainTheorem' not in all_text
    assert not (visible/'INPUT_MANIFEST.json').exists()
    assert not (visible/'ALIASES.json').exists()
    assert (audit/'INPUT_MANIFEST.json').exists()
    assert (audit/'ALIASES.json').exists()
    m=json.loads((audit/'INPUT_MANIFEST.json').read_text(encoding='utf-8'))
    assert m['leakage_scan']=='PASS'
    assert m['visibility_profile']=='skeptic-blind'
    assert len(m['context_packet_sha256'])==64


def test_context_export_contains_only_agent_visible_payload(tmp_path: Path):
    repo=_blind_repo(tmp_path)
    p=build_context(repo,'H-0042','skeptic','skeptic-blind','RUN3')
    dest=tmp_path/'exported'
    export_context(repo,'H-0042','RUN3',dest)
    names={x.name for x in dest.rglob('*') if x.is_file()}
    assert 'STATEMENT.md' in names and 'TASK.md' in names
    assert 'INPUT_MANIFEST.json' not in names
    assert 'ALIASES.json' not in names
    text='\n'.join(x.read_text(encoding='utf-8') for x in dest.rglob('*') if x.is_file())
    assert 'H-0042' not in text
    assert 'Secret Scaling Project Main Theorem' not in text


def test_context_audit_rejects_audit_metadata_in_visible_tree(tmp_path: Path):
    repo=_blind_repo(tmp_path)
    p=build_context(repo,'H-0042','skeptic','skeptic-blind','RUN4')
    (p/'agent-visible'/'ALIASES.json').write_text('{"H-0042":"CLAIM"}',encoding='utf-8')
    errs=audit_packet_dir(p,['H-0042'])
    assert any('audit-only metadata present' in e for e in errs)


def test_blind_context_rejects_profile_for_wrong_role(tmp_path: Path):
    repo=_blind_repo(tmp_path)
    import pytest
    with pytest.raises(ValueError):
        build_context(repo,'H-0042','formalizer','skeptic-blind','RUN2')


def test_context_leakage_scanner_detects_forbidden_marker(tmp_path: Path):
    p=tmp_path/'packet'; p.mkdir(); (p/'TASK.md').write_text('VERIFIED_RESULT',encoding='utf-8')
    errs=audit_packet_dir(p,['VERIFIED_RESULT'])
    assert errs
