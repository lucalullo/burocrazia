import json
from pathlib import Path
import pytest
from src.recognize import _informational_heading,recognize_catalog

@pytest.mark.parametrize('wrapper',['Bozza di','Schema di','Proposta di','Bozza'])
def test_draft_wrapper_preserves_explicit_informational_heading(wrapper):
    assert _informational_heading('Autorità pubblica\n'+wrapper+' “Regolamento sui procedimenti”\nAccesso ai documenti amministrativi')

def test_reference_to_draft_in_form_body_does_not_change_heading_role():
    assert not _informational_heading('Richiesta di accesso ai documenti amministrativi\nIl sottoscritto richiede accesso alla bozza di regolamento comunale.')
    assert not _informational_heading('Schema di domanda di accesso ai documenti amministrativi\nIl sottoscritto richiede accesso.')
    assert not _informational_heading('Modulo di domanda\n'+('campo\n'*7)+'Bozza di regolamento')

def test_confirmed_round14_anac_false_accept_is_rejected():
    from benchmarks.round3_audit import catalog
    case=json.loads((Path(__file__).parent/'fixtures/round15_confirmed_false_accept.json').read_bytes())
    docs,families=catalog()
    result=recognize_catalog(case['official_opening'],docs,families)
    reference=recognize_catalog(case['official_opening'],docs,families,reference_full_scan=True)
    assert result.match_type==reference.match_type=='NO_MATCH'

def test_round15_adjudication_preserves_two_unresolved_annual_identities():
    root=Path(__file__).resolve().parents[1]
    cases=json.loads((root/'benchmarks/reference/round15_truth_adjudication.json').read_bytes())['cases']
    assert sum(c['adjudicated_status']=='confirmed_unknown' for c in cases)==1
    assert sum(c['adjudicated_status']=='ambiguous_truth' for c in cases)==2
    assert not any(c['release_gate_eligible'] for c in cases)

def test_ambiguous_reference_cannot_be_promoted_to_release_eligible_by_schema():
    import jsonschema
    root=Path(__file__).resolve().parents[1]
    value=json.loads((root/'benchmarks/reference/reference_truth_v3.json').read_bytes())
    schema=json.loads((root/'benchmarks/schemas/reference_truth_v3.schema.json').read_bytes())
    jsonschema.validate(value,schema)
    ambiguous=next(c for c in value['cases'] if c['adjudicated_status']=='ambiguous_truth')
    ambiguous['release_gate_eligible']=True
    with pytest.raises(jsonschema.ValidationError):jsonschema.validate(value,schema)

def test_authorized_heading_fix_preserves_other_recognition_semantics():
    import ast,subprocess
    root=Path(__file__).resolve().parents[1]
    if not (root/'.git').exists():pytest.skip('Historical Git checkout required; package verification includes the source contract')
    baseline='425fa010063692d5d8ed090431068ad014d86ee6'
    def old(path):return subprocess.check_output(['git','show',baseline+':'+path],cwd=root)
    before=ast.parse(old('src/recognize.py'));after=ast.parse((root/'src/recognize.py').read_bytes())
    def other_nodes(tree):
        return [ast.dump(n,include_attributes=False) for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name!='_informational_heading']
    assert other_nodes(before)==other_nodes(after)
    for path in ['src/extract.py','src/fingerprint_v3.py','src/fingerprint_decision_v5.py','src/fingerprint_decision_v4.py','src/fingerprint_match_v2.py','src/title_evidence.py','src/fingerprint_pages.py','data/recognition_profiles/fingerprint_decision_v5.json','data/recognition_features.json']:
        assert (root/path).read_bytes()==old(path),path
