"""Behavioral safety examples for conditional v7 decisions."""
from dataclasses import replace
import pytest
from src.models import AdministrativeDocument
from src.fingerprint_decision_v7 import conditional_tier,exclusive_heading,evidence_states,profile,entity_evidence

def doc(**kw):
    values=dict(id=90001,ente='INPS',titolo_ufficiale='Domanda pensione superstiti accordo internazionale Italia Giappone',categoria=None,descrizione_ufficiale=None,significato_semplice=None,versione=None,data_rilevazione='2026-10-14',stato_verifica='da_verificare');values.update(kw);return AdministrativeDocument(**values)

@pytest.mark.parametrize('changes,rank,accepted',[
    ({},True,True),({},False,False),({'chars':.65},True,False),({'ocr':.5},True,False),({'anchors':.2},True,False),({'overlap':8},True,False),
])
def test_scan_needs_rank1_and_strong_independent_channels(changes,rank,accepted):
    r=dict(digital=.5,ocr=.9,chars=.9,visual=0.,anchors=.7,overlap=30);r.update(changes)
    assert bool(conditional_tier(r,'image',profile()['thresholds'],rank1=rank))==accepted
    assert conditional_tier(r,'unknown',profile()['thresholds'],rank1=True) is None

def test_visual_alone_and_generic_short_heading_cannot_accept():
    r=dict(digital=.2,ocr=.2,chars=.3,visual=1.,anchors=.6,overlap=30)
    assert conditional_tier(r,'image',profile()['thresholds'],rank1=True) is None
    assert conditional_tier(r,'image',profile()['thresholds'],rank1=True,heading_terms=3) is None
    assert conditional_tier(r,'image',profile()['thresholds'],rank1=True,heading_terms=6)=='B_complete_heading_layout'

def test_complete_title_is_bounded_and_does_not_choose_version_siblings():
    a=doc(versione='1.0');b=replace(a,id=90002,versione='2.0');text=a.titolo_ufficiale
    assert set(exclusive_heading(text,[a,b]))=={a.id,b.id}
    assert not exclusive_heading('riferimenti e dati sintetici '*100+'\n'+text,[a,b])

@pytest.mark.parametrize('text,entity',[
    ('Modulo senza intestazione leggibile','entity_unknown'),('INPS\nModulo','entity_confirmed'),('INAIL\nModulo','entity_conflict'),
])
def test_unknown_issuer_is_not_a_conflict_and_explicit_other_issuer_remains_veto(text,entity):
    d=doc();e=entity_evidence(text,['INPS','INAIL']);state,_,reason=evidence_states(text,d,[d],e)
    assert state==entity
    if entity=='entity_conflict':assert reason=='explicit_entity_conflict'

@pytest.mark.parametrize('text,state',[
    ('INPS\nVersione 1.0\nRichiesta','version_confirmed'),('INPS\nVersione 2.0\nRichiesta','version_conflict'),('INPS\nVersione illeggibile\nRichiesta','version_unknown'),
])
def test_revision_confirmed_unknown_and_conflict(text,state):
    d=doc(versione='1.0');assert evidence_states(text,d,[d],frozenset({'inps'}))[1]==state

@pytest.mark.parametrize('text,state',[
    ('Agenzia delle Entrate\nModello CU 2024\nAnno di imposta 2023','version_confirmed'),
    ('Agenzia delle Entrate\nModello CU 2023','version_conflict'),
    ('Agenzia delle Entrate\nModello CU anno non leggibile','version_unknown'),
])
def test_model_year_is_distinct_from_tax_year_and_missing_scan_year(text,state):
    d=doc(ente='Agenzia delle Entrate',titolo_ufficiale='Certificazione Unica CU',codice='CU',versione='2024');assert evidence_states(text,d,[d],frozenset({'agenzia delle entrate'}))[1]==state

def test_original_v6_and_round20_results_are_immutable():
    from scripts.round21_common import preserved
    assert preserved()['baseline_status']=='passed'

def test_role_in_heading_cannot_be_replaced_by_later_recipient_role():
    a=doc(titolo_ufficiale='Amministratore di Sostegno-Acquisto immobili')
    b=replace(a,id=90002,titolo_ufficiale='Tutela-Autorizzazione acquisto immobili')
    text='AMMINISTRAZIONE DI SOSTEGNO\nDOMANDA DI AUTORIZZAZIONE ACQUISTO IMMOBILI\nAl Giudice Tutelare'
    assert set(exclusive_heading(text,[a,b]))=={a.id}

def test_ordered_country_relation_distinguishes_same_bag_of_title_words():
    a=doc(titolo_ufficiale='Domanda pensione superstiti assicurazione italiana accordo Giappone Repubblica Italiana')
    b=replace(a,id=90002,titolo_ufficiale='Domanda pensione superstiti assicurazione giapponese accordo Italia Repubblica Italiana')
    assert set(exclusive_heading(a.titolo_ufficiale,[a,b]))=={a.id}
