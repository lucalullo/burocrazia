"""Truth qualification and independent pre-optimization algorithm checks."""
import ast
import re
import subprocess
import unicodedata
from pathlib import Path
import pytest
from PIL import Image,ImageOps
from benchmarks.release_truth import select_release,load_release
from src.document_fingerprints import streams
from src.fingerprint_v2 import h
from src.fingerprint_v3 import features,char_hash,PARAMETERS
from src.fingerprint_pages import image_signature

ROOT=Path(__file__).resolve().parents[1]

def test_confirmed_cannot_be_silently_excluded():
    case=dict(case_id='C',confidence='confirmed',release_gate_eligible=True,evidence={'source':'fixture'})
    assert select_release([case])==[case]
    with pytest.raises(ValueError):select_release([dict(case,release_gate_eligible=False)])
    with pytest.raises(ValueError):select_release([dict(case,evidence={})])

@pytest.mark.parametrize('state',['ambiguous','insufficient','historical_only','obsolete'])
def test_uncertain_truth_is_visible_but_not_release_truth(state):
    c=dict(case_id='A',confidence=state,release_gate_eligible=False,historical_expected='DOCUMENT_MATCH')
    assert not select_release([c])
    assert c['historical_expected']=='DOCUMENT_MATCH'
    with pytest.raises(ValueError):select_release([dict(c,release_gate_eligible=True)])

def test_round16_truth_has_hashes_and_correct_inps_inail_scope():
    from scripts.round16_common import read,sha,TRUTH
    policy,registry,selected=load_release()
    assert policy['base_reference_truth_v3_sha256']==sha(TRUTH)
    assert len(selected)==1258
    for ident in ['EX02','EX03']:
        c=next(c for c in registry['cases'] if c['case_id']=='development_regression:'+ident)
        assert c['confidence']=='ambiguous' and not c['release_gate_eligible']
        original=next(c for c in read('benchmarks/corpora/development_regression.json')['cases'] if c['id']==ident)
        assert 'INPS' in original['text'] and original['expected']['document_id']==c['historical_expected']['document_id']
    inail=[c for c in read(TRUTH)['cases'] if c['confidence']=='ambiguous']
    assert {c['case_id'] for c in inail}=={'U14-5f0c017c3d56e6c5','U14-c1fc4765c01dcd62'}
    assert not any(c['release_gate_eligible'] for c in inail)

@pytest.mark.parametrize('text',['','A','abcd','àéì 世界 Straße ＡＢＣ\nModulo prova testo\n',('codice modulo campo '*650)+'AFTER_LIMIT'])
def test_feature_sets_identical_to_original_hash_algorithm(text):
    normalized=unicodedata.normalize('NFKC',text[:PARAMETERS['max_page_chars']]).casefold()
    words,_=streams(normalized);compact=re.sub(r'[^\w]','',normalized)
    old_tokens=frozenset(h(' '.join(words[i:i+3]),'token') for i in range(max(0,len(words)-2)))
    old_chars={str(n):frozenset(char_hash(compact[i:i+n],n) for i in range(max(0,len(compact)-n+1))) for n in (3,4,5)}
    actual=features(text)
    assert actual['tokens']==old_tokens and actual['chars']==old_chars

def original_image_signature(image):
    out=[]
    for angle in (0,90,180,270):
        with image.rotate(angle,expand=True) as rotated,ImageOps.grayscale(rotated) as gray:
            w,h=gray.size
            boxes=[(0,0,w,h),(w*.06,h*.06,w*.94,h*.94),*((x*w/2,y*h/2,(x+1)*w/2,(y+1)*h/2) for y in (0,1) for x in (0,1))]
            for box in boxes:
                with gray.crop(box) as crop,crop.resize((9,8),Image.Resampling.LANCZOS) as small:
                    pixels=list(small.getdata());bits=0
                    for y in range(8):
                        for x in range(8):bits=(bits<<1)|int(pixels[y*9+x]>pixels[y*9+x+1])
                    out.append(format(bits,'016x'))
    return tuple(out)

@pytest.mark.parametrize('mode',['RGB','RGBA','L','P'])
@pytest.mark.parametrize('size',[(23,17),(28,36),(1,1)])
def test_grayscale_rotation_commutes_with_original_signature(mode,size):
    with Image.new('RGB',size) as base:
        base.putdata([((i*23)%256,(i*101)%256,(i*53)%256) for i in range(size[0]*size[1])])
        with base.convert(mode) as image:
            before=image.tobytes()
            assert image_signature(image)==original_image_signature(image)
            assert image.tobytes()==before

def test_only_two_performance_functions_differ_from_round15():
    if not (ROOT/'.git').exists():pytest.skip('Historical Git source required')
    from scripts.round16_common import BASE
    freeze=__import__('json').loads((ROOT/'benchmarks/results/round16/freeze_manifest.json').read_bytes())['freeze_git_commit']
    for path,allowed in [('src/fingerprint_v3.py','features'),('src/fingerprint_pages.py','image_signature')]:
        old=ast.parse(subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT));new=ast.parse(subprocess.check_output(['git','show',freeze+':'+path],cwd=ROOT))
        def other(tree):return [ast.dump(n,include_attributes=False) for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name!=allowed]
        assert other(old)==other(new)
    for path in ['src/recognize.py','src/extract.py','src/fingerprint_decision_v5.py','src/fingerprint_decision_v4.py','src/title_evidence.py','data/recognition_profiles/fingerprint_decision_v5.json','data/recognition_features.json','benchmarks/reference/reference_truth_v3.json']:
        assert subprocess.check_output(['git','show',freeze+':'+path],cwd=ROOT)==subprocess.check_output(['git','show',BASE+':'+path],cwd=ROOT)

def test_seven_run_median_gate_does_not_promote_preferences_to_blockers():
    from benchmarks.round16_performance import stability
    rows=[dict(latency_ms=dict(p95=v)) for v in [100,200,220,249,270,280,350]]
    result=stability(rows)
    assert result['required_pass'] and result['median_p95']==249
    assert not result['preferred_stability_pass'] and not result['preferred_latency_pass']
    assert not stability(rows[:6])['required_pass']

def test_round16_unknown_exposure_cannot_be_hidden_by_a_new_case_id(monkeypatch):
    import benchmarks.round16_unknown as u
    monkeypatch.setattr(u,'sealed',lambda:dict(freeze_git_commit='f'))
    monkeypatch.setattr(u,'validate_old_contract',lambda m:m)
    monkeypatch.setattr(u,'excluded',lambda:{'a'*64})
    monkeypatch.setattr(u,'read',lambda p:dict(cases=[]))
    with pytest.raises(AssertionError):u.validate_release(dict(manifest_id='official-unknown-release-v3',freeze_commit='f',cases=[dict(case_id='U16-new',SHA256='a'*64)]))

def test_fresh_v5_is_blocked_without_a_passing_unknown_gate(monkeypatch):
    import benchmarks.round16_evaluation as e
    monkeypatch.setattr(e,'sealed',lambda:{})
    monkeypatch.setattr(e,'read',lambda p:dict(passed=False))
    with pytest.raises(AssertionError,match='Unknown gate'):e.plan()

@pytest.mark.parametrize('safe',[True,False])
def test_release_gate_keeps_forbidden_entity_constraints_distinct_from_observed_fields(monkeypatch,safe):
    import benchmarks.round16_gates as g
    expected=dict(match_type='NO_MATCH',forbidden_entities=['Ente incompatibile'])
    contract=dict(case_id='AV',input_key='AV',confidence='confirmed',release_gate_eligible=True,truth_domain='synthetic_safety_contract',expected=expected)
    row=dict(id='AV',expected=expected,observed=dict(match_type='NO_MATCH' if safe else 'DOCUMENT_MATCH',entity=None if safe else 'Ente incompatibile'),correct=safe)
    monkeypatch.setattr(g,'load_release',lambda:({}, {}, [contract]));monkeypatch.setattr(g,'observations',lambda:[row]);monkeypatch.setattr(g,'read',lambda p:dict(cases=[]));monkeypatch.setattr(g,'sha',lambda p:'fixture-hash');monkeypatch.setattr(g,'runtime_hash',lambda:'fixture-runtime')
    saved=[];monkeypatch.setattr(g,'save',lambda name,value:saved.append(value))
    assert g.release()==(0 if safe else 1)
    assert saved[0]['passed']==safe

@pytest.mark.parametrize('kind,did,safe',[('NO_MATCH',None,True),('DOCUMENT_MATCH',428,True),('DOCUMENT_MATCH',429,False),('FAMILY_MATCH',None,False)])
def test_former_false_accept_safety_preserves_abstention_contract(kind,did,safe):
    from scripts.round16_validate import former_false_accept_safe
    assert former_false_accept_safe(dict(expected=dict(match_type='DOCUMENT_MATCH',document_id=428),observed=dict(match_type=kind,document_id=did)))==safe
