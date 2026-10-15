import copy,json,subprocess,zipfile
from io import BytesIO
from pathlib import Path
import pytest
from maintenance.legacy_convert import preflight,convert_official,profile_xml
from maintenance.round10_unknown_acquire import attachment_links
from benchmarks.unknown_v2 import validate

def archive(name,raw):
 out=BytesIO()
 with zipfile.ZipFile(out,'w') as z:z.writestr(name,raw)
 return out.getvalue()

@pytest.mark.parametrize('raw,suffix',[(b'{\\rtf1 \\object active}', '.rtf'),(b'\xd0\xcf\x11\xe0'+b'_VBA_PROJECT','.doc'),(archive('xl/externalLinks/link.xml',b'<x/>'),'.xlsx'),(archive('word/../evil.xml',b'<x/>'),'.odt'),(archive('xl/r.xml',b'<Relationship TargetMode="External" Target="https://example.net/a"/>'),'.xlsx'),(archive('content.xml',b'<!DOCTYPE x SYSTEM "https://example.net/a"><x/>'),'.odt')])
def test_legacy_preflight_rejects_active_external_and_traversal(raw,suffix):
 with pytest.raises(ValueError):preflight(raw,suffix)

def test_legacy_conversion_provenance_and_hidden_profile(tmp_path):
 import pymupdf
 exe=tmp_path/'converter';exe.write_bytes(b'fixture')
 with pymupdf.open() as doc:
  doc.new_page().insert_text((50,50),'Official inert fixture');pdf=doc.tobytes()
 def runner(args,**kw):
  assert '--headless' in args and '--norestore' in args and kw['timeout']<=60
  assert 'MacroSecurityLevel' in profile_xml() and '<value>3</value>' in profile_xml()
  from lxml import etree
  root=etree.fromstring(profile_xml().encode());ns='{http://openoffice.org/2001/registry}'
  values={(i.get(ns+'path'),p.get(ns+'name')):p.findtext('value') for i in root for p in i}
  assert values[('/org.openoffice.Office.Writer/Content/Update','Link')]=='0'
  assert values[('/org.openoffice.Office.Calc/Content/Update','Link')]=='1'
  for flag in ['DisableMacrosExecution','DisableActiveContent','BlockUntrustedRefererLinks','DisablePythonRuntime']:
   assert values[('/org.openoffice.Office.Common/Security/Scripting',flag)]=='true'
  (Path(args[args.index('--outdir')+1])/'official.pdf').write_bytes(pdf)
  return subprocess.CompletedProcess(args,0,b'',b'')
 derived,meta=convert_official(b'{\\rtf1 official inert fixture}', '.rtf',tmp_path/'work',runner=runner,converter=exe)
 assert derived==pdf and meta['original_sha256']!=meta['derived_sha256'] and meta['pages']==1
 assert not list((tmp_path/'work').iterdir())
 def timeout(*args,**kw):raise subprocess.TimeoutExpired(args,1)
 with pytest.raises(ValueError,match='timeout'):convert_official(b'{\\rtf1 fixture}', '.rtf',tmp_path/'work',runner=timeout,converter=exe)
 assert not list((tmp_path/'work').iterdir())

def test_unknown_discovery_links_are_inert_and_official():
 raw=b'<a href="/files/a.pdf">Circolare distinta</a><a href="https://example.net/a.pdf">Guida</a><script>ignored()</script>'
 assert attachment_links(raw,'https://www.agid.gov.it/it/linee-guida','agid')==[('https://www.agid.gov.it/files/a.pdf','Circolare distinta',True)]

def test_unknown_v2_refuses_missing_evidence_and_historical_eval():
 from scripts.round10_truth import document_metadata
 assert document_metadata('Legge 7 marzo 2020, n. 15. Disposizioni generali.')==('','')
 assert document_metadata('Circolare n. 24\nVersione 1.2\nLegge 2020')==('24','1.2')
 old=json.loads(Path('benchmarks/manifests/official_unknown_v1.json').read_bytes())['cases'][0]
 c=dict(case_id=old['case_id'],source=old['source_key'],entity=old['entity'],title=old['title'],official_url=old['url'],acquisition_date=old['evidence_date'],SHA256=old['sha256'],mime='application/pdf',classification_reason='Preserved supported official truth',reference_truth_status='confirmed_unknown',expected_result='NO_MATCH',receipt=old['receipt'],audit_evidence=old['audit_evidence'],split='unknown_dev',historically_seen=True)
 value=dict(schema_version=2,manifest_id='official-unknown-v2',cases=[c]);validate(value)
 for mutation in ['split','sha','url','duplicate','truth','group']:
  v=copy.deepcopy(value)
  if mutation=='split':v['cases'][0]['split']='unknown_eval'
  elif mutation=='sha':v['cases'][0]['SHA256']='a'*64
  elif mutation=='url':v['cases'][0]['official_url']='https://example.net/a.pdf'
  elif mutation=='duplicate':v['cases'].append(v['cases'][0])
  elif mutation=='group':
   v['cases'][0]['resource_group']='fixture-group'
   second=copy.deepcopy(v['cases'][0]);second.update(case_id='NEW',SHA256='b'*64,split='unknown_eval',historically_seen=False);second['receipt']['sha256']='b'*64;v['cases'].append(second)
  else:v['cases'][0]['reference_truth_status']='ambiguous'
  with pytest.raises(ValueError):validate(v)
