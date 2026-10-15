"""Durable per-case benchmark journal; one serial coordinator or concurrent writers.

SQLite is authoritative until all expected IDs exist. JSON is an atomic export,
never a resume source. Run identity binds engine AND inputs, not just a filename.
Only public numeric benchmark evidence belongs here; no uploaded personal text.
"""
import hashlib,json,os,sqlite3,tempfile,time
from pathlib import Path
from contextlib import contextmanager

def encoded(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')

def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if any(p.is_symlink() or p.is_junction() for p in [path,*path.parents]):raise ValueError('Linked evidence destination')
    raw=encoded(value);fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.partial',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
        for attempt in range(5):
            try:os.replace(name,path);break
            except PermissionError:
                if attempt==4:raise
                time.sleep(.02*(attempt+1))
        if path.read_bytes()!=raw:raise ValueError('Evidence export verification failed')
        return hashlib.sha256(raw).hexdigest()
    finally:
        if os.path.exists(name):os.unlink(name)

class CaseJournal:
    def __init__(self,path,*,identity,expected_ids):
        self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
        if any(p.is_symlink() or p.is_junction() for p in [self.path,*self.path.parents]):raise ValueError('Linked journal destination')
        ids=list(expected_ids)
        if any(not isinstance(i,str) or not i or len(i)>256 for i in ids) or len(ids)!=len(set(ids)):raise ValueError('Invalid or duplicate expected IDs')
        self.expected=set(ids);self.identity=identity
        manifest=encoded(dict(identity=identity,expected_ids=sorted(ids)))
        try:
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('CREATE TABLE IF NOT EXISTS manifest (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, payload BLOB NOT NULL, sha256 TEXT NOT NULL)')
                db.execute('INSERT OR IGNORE INTO manifest VALUES (1,?)',(manifest,))
                if db.execute('SELECT payload FROM manifest').fetchone()[0]!=manifest:raise ValueError('Resume engine/input identity mismatch')
            self.rows() # fail closed on corrupted persisted payloads
        except sqlite3.DatabaseError as exc:raise ValueError('Corrupted case journal') from exc

    @contextmanager
    def connect(self):
        db=sqlite3.connect(self.path,timeout=10)
        try:
            db.execute('PRAGMA synchronous=FULL')
            with db:yield db
        finally:db.close()

    def append(self,row):
        key=row.get('id')
        if key not in self.expected:raise ValueError('Unexpected case ID')
        raw=encoded(row);sha=hashlib.sha256(raw).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous=db.execute('SELECT payload,sha256 FROM cases WHERE id=?',(key,)).fetchone()
            if previous:
                if previous!=(raw,sha):raise ValueError('Conflicting duplicate case')
                return False
            db.execute('INSERT INTO cases VALUES (?,?,?)',(key,raw,sha))
        return True

    def rows(self):
        with self.connect() as db:values=db.execute('SELECT id,payload,sha256 FROM cases ORDER BY id').fetchall()
        result=[]
        for key,raw,sha in values:
            if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('Corrupted case payload')
            row=json.loads(raw)
            if key not in self.expected or row.get('id')!=key:raise ValueError('Corrupted case identity')
            result.append(row)
        return result

    def pending(self):return sorted(self.expected-{r['id'] for r in self.rows()})

    def export(self,path,*,complete=False):
        rows=self.rows()
        if complete and len(rows)!=len(self.expected):raise ValueError('Expected count mismatch')
        value=dict(schema_version=1,identity=self.identity,expected_count=len(self.expected),completed=len(rows),complete=len(rows)==len(self.expected),cases=rows)
        return atomic_json(path,value)
