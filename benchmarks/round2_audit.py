"""Reproduce the read-only Round 1 audit before changing recognition rules."""
from __future__ import annotations
import cProfile
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import pstats
import sqlite3
import subprocess

from benchmarks.evaluate import verify_locks
from maintenance.build_catalog import verify_continuity
from scripts.verify_catalog import verify
from src.database import list_documents
from src.families import list_document_families
from src import recognize as engine

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'benchmarks/results/round2'

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = ROOT/'data/catalog_seed.sqlite3'
    with sqlite3.connect(catalog.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        docs, families=list_documents(db),list_document_families(db)
        verify_continuity(db,json.loads((ROOT/'data/baseline_v061_rows.json').read_text(encoding='utf-8')))
        schema=db.execute('PRAGMA user_version').fetchone()[0]
    verify_locks()
    byid={d.id:d for d in docs}
    corpus=json.loads((ROOT/'benchmarks/corpora/release_locked_v1.json').read_text(encoding='utf-8'))
    old=json.loads((ROOT/'benchmarks/results/candidate/release_locked_v1.json').read_text(encoding='utf-8'))
    cards=[]
    evidence={
      143:'https://www.ispettorato.gov.it/servizio/richiesta-di-intervento-ispettivo/',
      167:'https://www.garanteprivacy.it/home/modulistica-e-servizi-online',
      165:'https://www.garanteprivacy.it/home/modulistica-e-servizi-online',
      166:'https://www.garanteprivacy.it/home/modulistica-e-servizi-online',
    }
    for row in old['cases']:
        if row['correct']: continue
        case=next(c for c in corpus['cases'] if c['id']==row['id'])
        text=case['text']; norm=engine.normalize_text(text)
        names=[d.ente for d in docs]+[f.ente for f in families]+list(engine.DISTINCT_ENTITY_NAMES)
        entities=engine._heading_entities(text,names) or engine._detect_entities(norm,names)
        scores=sorted([engine._score_candidate(text,norm,d,entities) for d in docs if d.stato_verifica!='demo'],key=lambda c:(c.evidence_rank,c.score),reverse=True)
        actual=engine.recognize_catalog(text,docs,families)
        expected=case['expected']; did=expected.get('document_id') or row['observed'].get('document_id')
        cause=('titolo di una sola parola: non distingue modulo, categoria o servizio' if expected.get('document_id') else
               'fixture di famiglia contiene identità specifica presente nel catalogo' if row['observed']['match_type']=='DOCUMENT_MATCH' else
               'due frasi anche annidate non raggiungono soglia; ente creditore e riscossore confusi nel catalogo/fixture')
        cards.append(dict(fixture=case,round1=row,current=asdict(actual),detected_entities=sorted(entities),
            top_candidates=[dict(id=c.document.id,title=c.document.titolo_ufficiale,score=c.score,rank=c.evidence_rank,signals=c.signals,conflicts=c.conflicts) for c in scores[:2]],
            root_cause=cause,classification='fixture ambigua' if expected.get('document_id') else 'expected probabilmente errato',
            proposed_action='Conservare rifiuto e v1; nuova etichetta documentata in v2' if expected.get('document_id') or did else 'Conservare rifiuto: non attribuire automaticamente una verifica alla famiglia',
            official_evidence=evidence.get(did,byid[did].fonte_url if did else 'https://www.agenziaentrateriscossione.gov.it/it/Per-saperne-di-piu/documenti-della-riscossione/accertamento-esecutivo-e-avviso-di-addebito-inps/index.html')))
    save(OUT/'locked_failure_details.json',cards)
    md='# Dieci fallimenti locked Round 1\n\nV1 resta immutato. Queste schede riproducono il motore Round 1 prima delle modifiche. Score = punti di evidenza, non probabilità.\n\n'
    for c in cards:
        md+=f"## {c['fixture']['id']}\n\n```text\n{c['fixture']['text']}\n```\n\nFonte: {c['fixture']['source']}. Expected: `{c['fixture']['expected']}`. Actual: `{c['round1']['observed']}`.\n\n"
        md+=f"Primi due candidati (rank, score, segnali): `{c['top_candidates']}`. Margine: {c['current']['document_score_margin']}; ente: {c['detected_entities']}; versione/anno e famiglia: vedere expected/actual.\n\n"
        md+=f"Causa: {c['root_cause']}. Classificazione: {c['classification']}. Azione: {c['proposed_action']}. [Evidenza ufficiale]({c['official_evidence']}).\n\n"
    (ROOT/'benchmarks/results/locked_failures_round2.md').write_text(md,encoding='utf-8')
    canonical=json.loads((ROOT/'benchmarks/results/candidate/catalog_coverage.json').read_text(encoding='utf-8'))
    rejects=[]
    for row in canonical['cases']:
        if row['correct']:continue
        d=byid[row['expected']['document_id']]
        title=engine.normalize_text(d.titolo_ufficiale)
        peers=[x.id for x in docs if x.id!=d.id and x.ente==d.ente and (engine.normalize_text(x.titolo_ufficiale)==title or (d.codice and x.codice==d.codice))]
        cause=('near duplicate' if peers else 'titolo troppo generico' if not engine._is_distinctive_title(title) else 'conflitto annualità' if any('annualità' in c for c in row['conflicts']) else 'recognition threshold')
        rejects.append(dict(document_id=d.id,source=d.source_id,entity=d.ente,title=d.titolo_ufficiale,code=d.codice,version=d.versione,category=d.categoria,current_result=row['observed']['match_type'],root_cause=cause,safe_fix_possible='no' if peers or cause=='titolo troppo generico' else 'da dimostrare',proposed_action='Conservare rifiuto; revisione metadati/identità senza sovrascrivere storia',related_ids=' '.join(map(str,peers))))
    with (ROOT/'benchmarks/results/canonical_rejections_round2.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rejects[0]));writer.writeheader();writer.writerows(rejects)
    census=json.loads((ROOT/'docs/source_census.json').read_text(encoding='utf-8'))
    reconciled=[]
    for s in census['sources']:
        # Counts are observation dispositions, not mutually exclusive metadata flags.
        excluded=len(s['excluded'])
        parts=dict(already_present=s.get('existing',0),new_identity=s['new'],updated_existing=s['updated'],duplicate_resource=s['duplicates'],excluded_non_document=excluded,excluded_untrusted=0,excluded_other=0)
        delta=s['discovered']-sum(parts.values())
        if delta<0:raise ValueError('Overlapping source counters: '+s['source_key'])
        parts['excluded_other']=delta
        reconciled.append(dict(source_key=s['source_key'],entity=s['ente'],discovered_total=s['discovered'],**parts,final_active_identities=sum(d.ente==s['ente'] and d.stato_verifica not in {'demo','rifiutato'} for d in docs),coverage_status=s['coverage_status'],partition_valid=sum(parts.values())==s['discovered']))
    save(ROOT/'docs/source_reconciliation_round2.json',dict(schema_version=1,definition='Partition of observed listing entries. final_active_identities is a separate stock, not a partition term. excluded_other is the explicitly reported unreconciled disposition, not evidence of trust failure.',sources=reconciled))
    verification=verify(catalog)
    quality=dict(code=sum(bool(d.codice) for d in docs if d.stato_verifica!='demo'),version=sum(bool(d.versione) for d in docs if d.stato_verifica!='demo'),dates=sum(bool(d.data_pubblicazione) for d in docs if d.stato_verifica!='demo'),downloads=sum(bool(d.download_url) for d in docs if d.stato_verifica!='demo'))
    audit=dict(commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),schema=schema,verification=verification,quality=quality,corpus_locks_verified=True,baseline_rows_unchanged=True,canonical_rejections=len(rejects),locked_failures=len(cards),record_identity_review='Technical metadata checks only; 827 additions not individually editor-reviewed.')
    save(OUT/'baseline_audit.json',audit)
    md='# Audit iniziale Round 2\n\nStato di ingresso verificato prima di modificare il motore.\n\n```json\n'+json.dumps(audit,ensure_ascii=False,indent=2)+'\n```\n\n'
    md+='I report raw Round 1 restano in `benchmarks/results/candidate/`: 35/35 regressione, 59/69 locked, 30/30 negativi, 1146/1216 canonici. Il report suite storico registra 488 passati e 3 skip; la suite viene rieseguita separatamente nel Round 2. Hash catalogo/lock e continuità di tutte le righe v0.6.1 verificati in sola lettura.\n\nLe 143 identità Venezia pesano 11,76% del catalogo reale; derivano da 159 osservazioni, 14 risorse duplicate e 2 esclusioni. Questo controllo tecnico non certifica tutti i contenuti dei file. Il campione ufficiale Round 1 contiene un solo Venezia. Provenienza e URL non equivalgono a revisione umana. Nessuna nuova fonte o identità viene importata durante la chiusura dei gate.\n'
    (ROOT/'docs/ROUND2_BASELINE_AUDIT.md').write_text(md,encoding='utf-8')
    profiler=cProfile.Profile();profiler.enable()
    for case in corpus['cases'][:20]:engine.recognize_catalog(case['text'],docs,families)
    profiler.disable();stats=pstats.Stats(profiler)
    functions=[dict(function=name,line=line,calls=value[1],self_seconds=value[2],cumulative_seconds=value[3]) for (filename,line,name),value in stats.stats.items() if 'recognize.py' in filename]
    save(OUT/'profile_before.json',dict(cases=20,functions=sorted(functions,key=lambda f:f['cumulative_seconds'],reverse=True)))
    print(json.dumps(audit,ensure_ascii=False))

if __name__=='__main__':main()
