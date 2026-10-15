import hashlib,json,os,sqlite3
import subprocess,sys
from concurrent.futures import ThreadPoolExecutor
import pytest
from benchmarks.transactional_writer import CaseJournal,atomic_json

def journal(path,ids=('a','b'),identity='engine-and-inputs'):
    return CaseJournal(path,identity=identity,expected_ids=ids)

def test_interruption_resume_dedupe_and_expected_count(tmp_path,monkeypatch):
    db=tmp_path/'journal.sqlite';out=tmp_path/'export.json';j=journal(db)
    j.append(dict(id='a',score=1));j.export(out);old=out.read_bytes()
    j=journal(db);assert j.pending()==['b'];assert not j.append(dict(id='a',score=1))
    with pytest.raises(ValueError,match='Conflicting'):j.append(dict(id='a',score=2))
    with pytest.raises(ValueError,match='Expected count'):j.export(out,complete=True)
    j.append(dict(id='b',score=3))
    with monkeypatch.context() as m:
        m.setattr(os,'replace',lambda *a:(_ for _ in ()).throw(OSError('forced interruption before rename')))
        with pytest.raises(OSError):j.export(out,complete=True)
    assert out.read_bytes()==old and not list(tmp_path.glob('*.partial'))
    sha=journal(db).export(out,complete=True)
    assert sha==hashlib.sha256(out.read_bytes()).hexdigest()
    assert len(json.loads(out.read_bytes())['cases'])==2

def test_corrupt_export_is_not_resume_source(tmp_path):
    db=tmp_path/'journal.sqlite';out=tmp_path/'export.json';j=journal(db,('a',));j.append(dict(id='a'))
    out.write_bytes(b'{broken partial');j=journal(db,('a',));j.export(out,complete=True)
    assert json.loads(out.read_bytes())['complete']
    with sqlite3.connect(db) as con:con.execute("UPDATE cases SET payload=x'00'")
    with pytest.raises(ValueError,match='Corrupted'):journal(db,('a',))

def test_corrupt_journal_and_identity_or_duplicate_plan_rejected(tmp_path):
    db=tmp_path/'journal.sqlite';journal(db)
    with pytest.raises(ValueError,match='identity'):journal(db,identity='different engine')
    with pytest.raises(ValueError,match='duplicate'):journal(tmp_path/'bad.sqlite',('a','a'))
    (tmp_path/'corrupt.sqlite').write_bytes(b'corrupted sqlite')
    with pytest.raises(ValueError,match='Corrupted'):journal(tmp_path/'corrupt.sqlite')

def test_concurrent_windows_writers_are_serialized(tmp_path):
    db=tmp_path/'journal.sqlite';ids=tuple(str(i) for i in range(30));journal(db,ids)
    def append(i):return journal(db,ids).append(dict(id=str(i)))
    with ThreadPoolExecutor(max_workers=4) as pool:assert all(pool.map(append,range(30)))
    j=journal(db,ids);assert not j.pending();assert len(j.rows())==30

def test_atomic_writer_retries_transient_windows_sharing_violation(tmp_path,monkeypatch):
    original=os.replace;calls=[]
    def replace(a,b):
        calls.append(1)
        if len(calls)<3:raise PermissionError('sharing violation')
        original(a,b)
    monkeypatch.setattr(os,'replace',replace)
    atomic_json(tmp_path/'report.json',{'value':1});assert len(calls)==3

def test_forced_process_exit_after_commit_is_resumable(tmp_path):
    db=tmp_path/'journal.sqlite'
    code="import os,sys; from benchmarks.transactional_writer import CaseJournal; j=CaseJournal(sys.argv[1],identity='crash-test',expected_ids=['a','b']); j.append(dict(id='a')); os._exit(77)"
    p=subprocess.run([sys.executable,'-c',code,str(db)])
    assert p.returncode==77
    j=journal(db,identity='crash-test');assert j.pending()==['b'];j.append(dict(id='b'))
    j.export(tmp_path/'complete.json',complete=True)
