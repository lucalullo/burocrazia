"""Record read-only visual inspection scope; never alter frozen evaluation."""
import hashlib,json
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'benchmarks/results/round8'
prepared=json.loads((out/'evaluation_prepared.json').read_bytes())
rows=[r for r in prepared['generation_audit'] if '-filled_' in r['case_id']]
proof=dict(inspected_at=datetime.now(UTC).isoformat(),stage='after preparation, before recognition',attempted=len(rows),generated=sum(r['generated'] for r in rows),reopened=sum(r['reopened'] for r in rows),synthetic_verified=sum(r['synthetic_verified'] for r in rows),first_page_template_ids=sorted({r['document_id'] for r in rows}),variant=1,full_size_inspected=[360,1133],renderer='Local Poppler pdftoppm, 1700-pixel maximum dimension',contact_sha256=hashlib.sha256((ROOT/'tmp-build/round8-evaluation-filled-contact.png').read_bytes()).hexdigest(),observations='All ten sampled first pages preserve headings, codes and issuer marks; synthetic text is visible and not clipped in the inspected views. This is a visual sample, not all pages of all 50 files.',limitations='Mechanical validity means reopened persistent synthetic fields, not complete or semantically correct administrative filling. For template 1133 the generator puts a date in the adjacent birthplace field as well as the birth-date field; generic municipality/address fields may repeat a fictitious street. These limits are recorded without changing the frozen generator, cases, labels or denominators. Unknown fields and unsupported radio controls may remain blank; no administrative validity is claimed.')
target=out/'evaluation_filled_visual_qa.json'
assert not target.exists()
target.write_bytes((json.dumps(proof,ensure_ascii=False,indent=2)+'\n').encode())
print('Read-only filled QA evidence saved; inputs unchanged')
