from types import SimpleNamespace
import pytest
from maintenance.round11_resolver import resolve_detail_links
from maintenance.round11_unknown_acquire import links_with_context
from benchmarks.unknown_release import select,balance

def test_garante_document_hop_requires_correlated_official_title():
 d=SimpleNamespace(titolo_ufficiale='CONCESSIONE DEL PATROCINIO',codice=None,download_url='https://www.garanteprivacy.it/garante/document?ID=7219673',detail_url=None)
 raw=b'<a href="/garante/document?ID=9100210">Modulo concessione del patrocinio</a><a href="/garante/document?ID=9999">Convegni ed eventi</a><a href="https://example.net/garante/document?ID=42">Concessione del patrocinio</a>'
 assert resolve_detail_links(raw,d.download_url,'garante_privacy',d)==['https://www.garanteprivacy.it/garante/document?ID=9100210']

def test_unknown_generic_attachment_keeps_actual_detail_heading():
 raw=b'<title>Circolare 4 agosto 2026: iniziative per la conoscenza della tragedia delle foibe</title><a href="/files/documento.pdf">La circolare</a><a href="https://example.net/file.pdf">La circolare</a>'
 rows=links_with_context(raw,'https://www.interno.gov.it/it/dettaglio','interno')
 assert len(rows)==1 and rows[0]['label']=='La circolare' and 'foibe' in rows[0]['context_heading'] and rows[0]['is_file']
 from scripts.round11_truth import attachment_role
 title,kind=attachment_role('all. 2\nSCUOLE SICURE 2025/2026\nDOMANDA DI CONTRIBUTO\nAlla Prefettura\nCircolare n.7','Circolare del2025','circolare')
 assert kind=='domanda' and 'DOMANDA DI CONTRIBUTO' in title and 'Circolare' not in title

def test_release_selection_is_order_invariant_quota_only_and_group_disjoint():
 cases=[dict(case_id=f'{source}-{i}',SHA256=f'{source}-{i}',source=source,entity=source,document_type='circolare' if i%2 else 'guida',resource_group=f'{source}-{i//2}',score=1-i,observed='NO_MATCH') for source in ['dominant','other','new'] for i in range(46 if source=='dominant' else 24)]
 selected=select(cases,seed=51,source_cap=25)
 shuffled=[dict(c,score=999,observed='DOCUMENT_MATCH') for c in reversed(cases)]
 assert [c['case_id'] for c in selected]==[c['case_id'] for c in select(shuffled,seed=51,source_cap=25)]
 assert max(balance(selected)['counts_per_source'].values())<=25
 kept={c['case_id'] for c in selected};assert not {c['resource_group'] for c in selected}&{c['resource_group'] for c in cases if c['case_id'] not in kept}

def test_benchmark_domain_policy_does_not_trust_lookalikes():
 from maintenance.policy import validate_url
 assert validate_url('https://bandi.regione.piemonte.it/form.pdf','regione_piemonte')
 with pytest.raises(ValueError):validate_url('https://regione.piemonte.it.example.net/form.pdf','regione_piemonte')
 import copy,json
 from pathlib import Path
 from benchmarks.unknown_release import validate
 release=json.loads(Path('benchmarks/manifests/official_unknown_release_v1.json').read_bytes());validate(release)
 for mutation in ['unconfirmed','duplicate','receipt']:
  bad=copy.deepcopy(release)
  if mutation=='unconfirmed':bad['cases'][0]['reference_truth_status']='ambiguous'
  elif mutation=='duplicate':bad['cases'].append(bad['cases'][0])
  else:bad['cases'][0]['receipt']['sha256']='a'*64
  with pytest.raises(ValueError):validate(bad)
