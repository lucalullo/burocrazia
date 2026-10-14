"""General v6 safety/representation rules and immutable historical evidence."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from src.fingerprint_decision_v6 import entity_evidence,tier,profile,corroborated_margin,corroborated_content
from src.models import AdministrativeDocument,RecognitionResult

@pytest.mark.parametrize('text,expected',[
    ('INAIL\nModulo di esempio',frozenset({'inail'})),
    ('Dipartimento per le politiche amministrative\nModulo',frozenset()),
    ('Tribunale\nModulo di esempio',frozenset()),
    ('Tribunale di Vene\nModulo di esempio',frozenset()),
    ('Tribunale di Milano\nModulo di esempio',frozenset({'tribunale di milano'})),
    ('Ministero degli Affari Esteri\nModulo',frozenset({'ministero degli affari esteri'})),
])
def test_weak_entities_do_not_invent_issuer_or_remove_explicit_conflicts(text,expected):
    assert entity_evidence(text,['INPS','INAIL','Tribunale di Venezia'])==expected

def test_known_subordinate_department_remains_explicit():
    name='Dipartimento per le politiche amministrative'
    assert entity_evidence(name,[name,'INPS'])==frozenset({name.casefold()})

@pytest.mark.parametrize('changes,accepted',[
    ({},True),({'visual':.90},False),({'chars':.70},False),({'ocr':.30},False),({'anchors':.10},False),({'overlap':10},False),
])
def test_scan_requires_corroborating_channels(changes,accepted):
    row=dict(overlap=30,digital=.40,ocr=.60,chars=.90,anchors=.50,visual=.97);row.update(changes)
    assert (tier(row,'image',profile()['thresholds']) is not None)==accepted
    assert tier(row,'unknown',profile()['thresholds']) is None

def test_two_distinct_pages_can_resolve_a_shared_attachment():
    best=dict(score=.96,top2_average=.94,alignment=[(0,1),(1,2)])
    peers=[dict(score=.94,top2_average=.80)]
    margin,used=corroborated_margin(best,peers,2,profile()['thresholds']);assert used and margin>.08
    assert not corroborated_margin(best,peers,1,profile()['thresholds'])[1]
    assert not corroborated_margin(best,[dict(score=.94,top2_average=.93)],2,profile()['thresholds'])[1]

def test_ambiguous_fingerprint_cannot_be_overruled_by_metadata(monkeypatch):
    import src.recognize as r
    import src.fingerprint_v3 as index
    import src.fingerprint_decision_v7 as decision
    doc=AdministrativeDocument(ente='Ente di esempio',titolo_ufficiale='Modulo di esempio',categoria=None,descrizione_ufficiale=None,significato_semplice=None,versione=None,data_rilevazione='2026-10-14',stato_verifica='da_verificare',id=42)
    monkeypatch.setattr(index,'public_index',lambda:SimpleNamespace(records=[object()]))
    def refuse(*args,**kwargs):kwargs['diagnostics'].update(tier='D_ambiguous',reason_code='margin');return None
    monkeypatch.setattr(decision,'match',refuse)
    monkeypatch.setattr(r,'recognize_document',lambda *a,**k:RecognitionResult(True,95,doc,('title',),'metadata accepted',score_margin=10))
    monkeypatch.setattr(r,'recognize_document_family',lambda *a,**k:SimpleNamespace(recognized=False,confidence=0,score_margin=0,conflicts=(),candidate_ids=(),matched_signals=(),reason='',family=None))
    diag={};result=r.recognize_catalog('Modulo amministrativo di esempio con campi e testo sufficientemente leggibile',[doc],[],fingerprint_diagnostics=diag)
    assert result.match_type=='NO_MATCH' and diag['metadata_veto']=='fingerprint_ambiguity'

def test_round20_preserves_catalog_data_and_all_historical_v5_bytes():
    from scripts.round20_common import preserved
    assert preserved()['v5']['actual_count']==665

@pytest.mark.parametrize('changes,runner,expected',[
    ({},.50,True),({'chars':.40},.50,False),({'anchors':.10},.50,False),
    ({'overlap':8},.50,False),({'digital':.30,'ocr':.30},.50,False),({},.74,False),
])
def test_corroborated_body_can_only_veto_contrary_metadata(changes,runner,expected):
    row=dict(score=.75,chars=.75,digital=.70,ocr=.60,anchors=.60,overlap=32);row.update(changes)
    assert corroborated_content(row,runner,profile()['thresholds'])==expected
