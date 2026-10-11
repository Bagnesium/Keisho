"""Author six controlled development cases. Refuses to replace existing cases."""

import json
from pathlib import Path
import textwrap

ROOT=Path(__file__).resolve().parents[1]/"tasks/development"

def code(value):return textwrap.dedent(value).lstrip()

JOBS={
"storage.py":code('''
import json
import sqlite3

class Store:
    def __init__(self, path):
        self.c = sqlite3.connect(path)
        self.c.row_factory = sqlite3.Row
        self.c.executescript("""
        CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, payload TEXT NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, not_before INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS deliveries(seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, acked INTEGER NOT NULL DEFAULT 0, due INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS effects(seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL, recipient TEXT NOT NULL, amount INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS results(job_id TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
    def ensure(self, job_id, payload):
        if not isinstance(job_id, str) or not job_id or not isinstance(payload.get('recipient'), str) or not payload['recipient']:
            raise ValueError('invalid job identity')
        if type(payload.get('amount')) is not int or payload['amount'] <= 0 or type(payload.get('failures',0)) is not int or payload.get('failures',0) < 0:
            raise ValueError('invalid job payload')
        encoded = json.dumps(payload, sort_keys=True)
        old = self.c.execute('SELECT payload FROM jobs WHERE id=?', (job_id,)).fetchone()
        if old and old['payload'] != encoded: raise ValueError('job ID reused with different payload')
        with self.c: self.c.execute("INSERT OR IGNORE INTO jobs(id,payload,state) VALUES(?,?,'queued')", (job_id, encoded))
    def job(self, job_id):
        row = dict(self.c.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone())
        row['payload'] = json.loads(row['payload']); return row
    def result(self, job_id):
        row = self.c.execute('SELECT value FROM results WHERE job_id=?',(job_id,)).fetchone()
        return json.loads(row['value']) if row else None
    def summary(self):
        return {'balances': {row['recipient']: row['amount'] for row in self.c.execute('SELECT recipient,SUM(amount) amount FROM effects GROUP BY recipient ORDER BY recipient')},
                'completed': self.c.execute('SELECT COUNT(*) FROM results').fetchone()[0],
                'effects': self.c.execute('SELECT COUNT(*) FROM effects').fetchone()[0],
                'pending': self.c.execute('SELECT COUNT(*) FROM deliveries WHERE acked=0').fetchone()[0],
                'states': {row['id']:row['state'] for row in self.c.execute('SELECT id,state FROM jobs ORDER BY id')},
                'attempts': {row['id']:row['attempts'] for row in self.c.execute('SELECT id,attempts FROM jobs ORDER BY id')}}
'''),
"queue.py":code('''
class Queue:
    def __init__(self, store): self.store = store
    def enqueue(self, job_id, payload):
        self.store.ensure(job_id, payload)
        with self.store.c: self.store.c.execute('INSERT INTO deliveries(job_id) VALUES(?)', (job_id,))
    def pending(self, now):
        row = self.store.c.execute('SELECT d.* FROM deliveries d JOIN jobs j ON j.id=d.job_id WHERE d.acked=0 AND d.due<=? AND j.not_before<=? ORDER BY d.seq LIMIT 1',(now,now)).fetchone()
        return dict(row) if row else None
    def ack(self, sequence):
        with self.store.c: self.store.c.execute('UPDATE deliveries SET acked=1 WHERE seq=?',(sequence,))
    def defer(self, delivery, now, delay):
        with self.store.c:
            self.store.c.execute('UPDATE deliveries SET due=? WHERE seq=?',(now+delay,delivery['seq']))
            self.store.c.execute('UPDATE jobs SET not_before=? WHERE id=?',(now+delay,delivery['job_id']))
'''),
"retry.py":code('''
MAX_ATTEMPTS = 3
def delay(attempt): return min(8, 2 ** attempt)
def can_retry(attempt): return attempt < MAX_ATTEMPTS
'''),
"effects.py":code('''
def apply(store, job):
    payload = job['payload']
    store.c.execute('INSERT INTO effects(job_id,recipient,amount) VALUES(?,?,?)', (job['id'],payload['recipient'],payload['amount']))
'''),
"results.py":code('''
import json
from effects import apply

class Crash(RuntimeError): pass

def commit(store, job, crash=None):
    with store.c:
        existing = store.result(job['id'])
        if existing is not None: return existing
        apply(store, job)
        if crash == 'after_effect': raise Crash('interruption inside result transaction')
        value = {'job_id':job['id'], 'amount':job['payload']['amount']}
        store.c.execute('INSERT OR REPLACE INTO results(job_id,value) VALUES(?,?)',(job['id'],json.dumps(value,sort_keys=True)))
        store.c.execute("UPDATE jobs SET state='done' WHERE id=?",(job['id'],))
    return value
'''),
"worker.py":code('''
from results import commit, Crash
from retry import can_retry, delay

class Worker:
    def __init__(self, store, queue): self.store, self.queue = store, queue
    def step(self, now, crash=None):
        delivery = self.queue.pending(now)
        if delivery is None: return None
        job = self.store.job(delivery['job_id'])
        cached = self.store.result(job['id'])
        if job['state'] == 'failed': self.queue.ack(delivery['seq']); return {'error':'terminal'}
        if cached is None:
            with self.store.c: self.store.c.execute("UPDATE jobs SET attempts=attempts+1,state='running' WHERE id=?",(job['id'],))
            job = self.store.job(job['id'])
            if job['attempts'] <= job['payload'].get('failures',0):
                if can_retry(job['attempts']): self.queue.defer(delivery,now,delay(job['attempts']))
                else:
                    with self.store.c: self.store.c.execute("UPDATE jobs SET state='failed' WHERE id=?",(job['id'],))
                    self.queue.ack(delivery['seq'])
                return {'retry':job['attempts']}
        value = commit(self.store,job,crash)
        if crash == 'after_result': raise Crash('result committed; delivery unacknowledged')
        self.queue.ack(delivery['seq'])
        return value
'''),
"diagnostics.py":code('''
import hashlib
import json
from pathlib import Path
from storage import Store
from queue import Queue
from worker import Worker
from results import Crash

def run_scenario(scenario):
    name = hashlib.sha256(json.dumps(scenario,sort_keys=True).encode()).hexdigest()
    path = Path('.runtime') / (name + '.sqlite')
    if path.exists(): path.unlink()
    store = Store(path); queue = Queue(store); worker = Worker(store,queue)
    crashes, errors = 0, 0
    for op in scenario['ops']:
        try:
            if op['op']=='enqueue': queue.enqueue(op['id'],op['payload'])
            elif op['op']=='restart':
                store.c.close(); store=Store(path); queue=Queue(store); worker=Worker(store,queue)
            elif op['op']=='step': worker.step(op.get('now',0),op.get('crash'))
            elif op['op']=='drain':
                for tick in range(op.get('start',0),op.get('start',0)+100): worker.step(tick)
            else: raise ValueError('unknown diagnostic operation')
        except Crash: crashes += 1
        except ValueError: errors += 1
    result = store.summary(); result.update(crashes=crashes,errors=errors); store.c.close()
    return {key:result[key] for key in scenario['select']}
''')}

MIGRATION={
"validation.py":code('''
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    endpoint: str
    timeout_ms: int
    max_attempts: int
    def __post_init__(self):
        if not isinstance(self.endpoint,str) or not self.endpoint: raise ValueError('endpoint')
        if type(self.timeout_ms) is not int or not 1<=self.timeout_ms<=120000: raise ValueError('timeout')
        if type(self.max_attempts) is not int or not 1<=self.max_attempts<=5: raise ValueError('attempts')

def old_seconds(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0: raise ValueError('old timeout')
    return int(value*1000)
'''),
"parser.py":code('''
from validation import Settings, old_seconds

def parse(raw):
    if not isinstance(raw,dict): raise ValueError('config must be an object')
    if raw.get('version',1)==1:
        if set(raw)!={'endpoint','timeout','retries'}: raise ValueError('legacy fields or mixed representation')
        if type(raw['retries']) is not int: raise ValueError('legacy retries')
        return Settings(raw['endpoint'],old_seconds(raw['timeout']),raw['retries']+1)
    if raw.get('version')!=2 or set(raw)!={'version','endpoint','request'}: raise ValueError('version or fields')
    request=raw['request']
    if not isinstance(request,dict) or set(request)!={'timeout_ms','max_attempts'}: raise ValueError('request')
    return Settings(raw['endpoint'],request['timeout_ms'],request['max_attempts'])

def serialize(settings):
    return {'version':2,'endpoint':settings.endpoint,'request':{'timeout_ms':settings.timeout_ms,'max_attempts':settings.max_attempts}}
'''),
"cache.py":code('''
from copy import deepcopy

class Cache:
    def __init__(self): self.values={}
    def key(self,settings): return (settings.endpoint,settings.timeout_ms,settings.max_attempts)
    def get_or_build(self,settings,build):
        key=self.key(settings)
        if key not in self.values: self.values[key]=build(settings)
        return deepcopy(self.values[key])
'''),
"policy.py":code('''
def build(settings):
    return {'endpoint':settings.endpoint,'timeout_ms':settings.timeout_ms,'max_attempts':settings.max_attempts,
            'attempt_deadlines_ms':[settings.timeout_ms*(index+1) for index in range(settings.max_attempts)]}
'''),
"service.py":code('''
from parser import parse
from cache import Cache
from policy import build

class Service:
    def __init__(self): self.cache=Cache()
    def configure(self,raw): return self.cache.get_or_build(parse(raw),build)
'''),
"callers.py":code('''
def legacy_options(plan):
    return {'endpoint':plan['endpoint'],'timeout':plan['timeout_ms']/1000,'retries':plan['max_attempts']-1}
def modern_options(plan):
    return {'endpoint':plan['endpoint'],'timeout_ms':plan['timeout_ms'],'max_attempts':plan['max_attempts']}
'''),
"diagnostics.py":code('''
from service import Service
from callers import legacy_options, modern_options
from parser import parse, serialize

def run_scenario(scenario):
    service=Service(); plans=[]; old=[]; modern=[]; errors=0; roundtrips=[]
    for index,raw in enumerate(scenario['configs']):
        try:
            plan=service.configure(raw);plans.append(plan);old.append(legacy_options(plan));modern.append(modern_options(plan))
            roundtrips.append(serialize(parse(serialize(parse(raw)))))
            if index==0 and scenario.get('mutate_after_first'): plan['attempt_deadlines_ms'][0]=999
        except (ValueError,TypeError,KeyError): errors+=1
    result={'plans':plans,'legacy':old,'modern':modern,'errors':errors,'cache_entries':len(service.cache.values),'roundtrips':roundtrips,'last_deadlines':plans[-1]['attempt_deadlines_ms'] if plans else []}
    return {key:result[key] for key in scenario['select']}
''')}

INDEX={
"normalize.py":code('''
import unicodedata

def document_id(value):
    if not isinstance(value,str) or not value.strip(): raise ValueError('document identity')
    return unicodedata.normalize('NFC',value.strip())
def content(value):
    if not isinstance(value,str): raise ValueError('document content')
    return ' '.join(unicodedata.normalize('NFC',value).split())
def terms(value): return content(value).casefold().split()
'''),
"chunking.py":code('''
def chunks(text, size=2):
    words=text.split()
    return [' '.join(words[index:index+size]) for index in range(0,len(words),size)]
'''),
"storage.py":code('''
import sqlite3

class Store:
    def __init__(self,path):
        self.c=sqlite3.connect(path); self.c.row_factory=sqlite3.Row
        self.c.executescript('CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,content TEXT NOT NULL,version INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY,doc_id TEXT NOT NULL,ordinal INTEGER NOT NULL,text TEXT NOT NULL,version INTEGER NOT NULL);')
    def put(self,doc_id,text,parts):
        row=self.c.execute('SELECT * FROM documents WHERE id=?',(doc_id,)).fetchone()
        if row and row['content']==text: return False
        version=row['version']+1 if row else 1
        with self.c:
            self.c.execute('DELETE FROM chunks WHERE doc_id=?',(doc_id,))
            self.c.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',(doc_id,text,version))
            for ordinal,part in enumerate(parts):
                self.c.execute('INSERT INTO chunks VALUES(?,?,?,?,?)',(f'{doc_id}:{version}:{ordinal}',doc_id,ordinal,part,version))
        return True
    def delete(self,doc_id):
        with self.c:
            self.c.execute('DELETE FROM chunks WHERE doc_id=?',(doc_id,))
            self.c.execute('DELETE FROM documents WHERE id=?',(doc_id,))
'''),
"lookup.py":code('''
from normalize import terms

def search(store,query):
    wanted=set(terms(query))
    if not wanted: return []
    rows=store.c.execute('SELECT * FROM chunks ORDER BY doc_id,ordinal,id').fetchall()
    return [{'doc_id':row['doc_id'],'text':row['text']} for row in rows if wanted <= set(terms(row['text']))]
'''),
"metadata.py":code('''
def snapshot(store):
    return {'documents':{row['id']:{'version':row['version'],'chunks':row['n']} for row in store.c.execute('SELECT d.id,d.version,COUNT(c.id) n FROM documents d LEFT JOIN chunks c ON d.id=c.doc_id GROUP BY d.id ORDER BY d.id')},
            'stored_chunks':store.c.execute('SELECT COUNT(*) FROM chunks').fetchone()[0],
            'orphans':store.c.execute('SELECT COUNT(*) FROM chunks c LEFT JOIN documents d ON d.id=c.doc_id WHERE d.id IS NULL').fetchone()[0]}
'''),
"ingest.py":code('''
from normalize import document_id, content
from chunking import chunks
from lookup import search
from metadata import snapshot

class Index:
    def __init__(self,store): self.store=store
    def update(self,doc_id,text):
        return self.store.put(document_id(doc_id),content(text),chunks(content(text)))
    def delete(self,doc_id): self.store.delete(document_id(doc_id))
    def search(self,query): return search(self.store,query)
    def metadata(self): return snapshot(self.store)
'''),
"diagnostics.py":code('''
import hashlib
import json
from pathlib import Path
from storage import Store
from ingest import Index

def run_scenario(scenario):
    path=Path('.runtime')/(hashlib.sha256(json.dumps(scenario,sort_keys=True).encode()).hexdigest()+'.sqlite')
    if path.exists(): path.unlink()
    store=Store(path); index=Index(store); searches=[];changes=[];errors=0
    for op in scenario['ops']:
        try:
            if op['op']=='update': changes.append(index.update(op['id'],op['text']))
            elif op['op']=='delete': index.delete(op['id'])
            elif op['op']=='search': searches.append(index.search(op['query']))
            elif op['op']=='restart': store.c.close();store=Store(path);index=Index(store)
            else: raise ValueError('operation')
        except (ValueError,TypeError): errors+=1
    result=index.metadata();result.update(searches=searches,changes=changes,errors=errors);store.c.close()
    return {key:result[key] for key in scenario['select']}
''')}

def scenario(id,family,args,expected):
    return {'id':id,'module':'diagnostics','function':'run_scenario','args':[args],'expected':expected}
def en(id,amount=3,recipient='team',failures=0):return {'op':'enqueue','id':id,'payload':{'amount':amount,'recipient':recipient,'failures':failures}}
def old(timeout=2,retries=1):return {'endpoint':'local-service','timeout':timeout,'retries':retries}
def modern(timeout=2000,attempts=2):return {'version':2,'endpoint':'local-service','request':{'timeout_ms':timeout,'max_attempts':attempts}}
def configcase(id,configs,expected,select):return scenario(id,'migration',{'configs':configs,'select':select},expected)
def idxcase(id,ops,expected,select):return scenario(id,'index',{'ops':ops,'select':select},expected)

# Acceptance contracts and diagnostics are declared before any execution.
cases={
'jobs_duplicate':{'family':'jobs','description':'Make durable result handling idempotent under duplicate delivery while preserving distinct jobs, bounded retries and atomic effects/results across interruption.',
    'acceptance':['Each unique job has exactly one stored effect; distinct job IDs remain legitimate work even for the same recipient','A committed result is reused and every delivery can be acknowledged; invalid job-ID reuse is rejected','Retry deadlines, terminal failure and restart/crash recovery preserve the ledger and existing payload/result API'],
    'public':[scenario('duplicate_delivery','jobs',{'ops':[en('a'),en('a'),en('b',5),{'op':'drain'}],'select':['balances','completed','effects','pending']},{'balances':{'team':8},'completed':2,'effects':2,'pending':0}),scenario('retry_compatibility','jobs',{'ops':[en('r',4,failures=2),{'op':'drain'}],'select':['balances','attempts','pending']},{'balances':{'team':4},'attempts':{'r':3},'pending':0})]},
'jobs_recovery':{'family':'jobs','description':'Recover delivery progress after a worker dies between durable result commit and acknowledgment; cached results must not block later work or lose interrupted jobs.',
    'acceptance':['Restart after result commit acknowledges the original delivery without repeating its effect','Later jobs and duplicates progress; interruption inside the transaction leaves retryable work, not acknowledged loss','Respect retry scheduling, terminal transitions, immutable job payloads and persistent result API'],
    'public':[scenario('result_ack_crash_then_next','jobs',{'ops':[en('a'),{'op':'step','crash':'after_result'},{'op':'restart'},en('b',5),{'op':'drain'}],'select':['balances','completed','pending','crashes']},{'balances':{'team':8},'completed':2,'pending':0,'crashes':1}),scenario('persistent_restart','jobs',{'ops':[en('a'),{'op':'drain'},{'op':'restart'},en('b',5),{'op':'drain'}],'select':['balances','completed','pending']},{'balances':{'team':8},'completed':2,'pending':0})]},
'migration_compat':{'family':'migration','description':'Complete the legacy seconds/retries to version-2 milliseconds/max-attempts migration across parser, validation, policy, cache and both caller APIs. Check caller units and every attempt deadline; a local parser-only fix is insufficient.',
    'acceptance':['Legacy timeout seconds convert to milliseconds; retries count additional attempts','Equivalent old/new configs yield equivalent plans and old/modern caller options; roundtrips preserve policy','Reject invalid or mixed representations, preserve valid fractional legacy timeouts and validate before using cache'],
    'public':[configcase('mixed_callers',[old(),modern()],{'modern':[{'endpoint':'local-service','timeout_ms':2000,'max_attempts':2}]*2,'legacy':[{'endpoint':'local-service','timeout':2,'retries':1}]*2,'cache_entries':1,'last_deadlines':[2000,4000]},['modern','legacy','cache_entries','last_deadlines']),configcase('invalid_inputs',[modern(0),{**old(),'request':{'timeout_ms':2000,'max_attempts':2}},modern(2000,True)],{'errors':3},['errors'])]},
'migration_cache':{'family':'migration','description':'Make normalized configuration changes invalidate only the relevant cached service policy while keeping equivalent legacy/modern representations compatible.',
    'acceptance':['Changed timeout or attempt policy yields fresh behavior at the same endpoint','Equivalent old/new representations share a normalized cache entry; previously returned plans are not mutated','Validation happens before cache access; old callers, modern callers and serialization agree on the current policy'],
    'public':[configcase('timeout_change',[modern(),modern(500,2)],{'modern':[{'endpoint':'local-service','timeout_ms':2000,'max_attempts':2},{'endpoint':'local-service','timeout_ms':500,'max_attempts':2}]},['modern']),configcase('equivalent_representations',[old(),modern()],{'cache_entries':1,'errors':0},['cache_entries','errors'])]},
'index_update':{'family':'index','description':'Replace stale chunks on document updates while preserving persistent metadata, unrelated documents, idempotent unchanged updates and identifier/encoding normalization.',
    'acceptance':['Search after update returns current chunks only; metadata counts and versions describe that same generation','Other documents survive an update, including after reopening storage','Unchanged normalized content is idempotent; UTF-8/NFC identifiers, whitespace normalization, empty content and invalid inputs remain consistent'],
    'public':[idxcase('replace_stale_chunks',[{'op':'update','id':'a','text':'old alpha token'},{'op':'update','id':'a','text':'new beta token'},{'op':'search','query':'old'},{'op':'search','query':'new'}],{'searches':[[],[{'doc_id':'a','text':'new beta'}]],'stored_chunks':2},['searches','stored_chunks']),idxcase('unchanged_update',[{'op':'update','id':'a','text':'same content'},{'op':'update','id':'a','text':'same  content'}],{'changes':[True,False],'documents':{'a':{'version':1,'chunks':1}}},['changes','documents'])]},
'index_delete':{'family':'index','description':'Propagate deletion through document identity normalization, chunk storage, metadata and lookup, including persistence, re-addition and unaffected documents.',
    'acceptance':['Deleted normalized IDs disappear from lookup and persistent metadata; orphan chunks are removed','Other documents remain searchable and may still be updated','Deleting unknown IDs is safe; deletion via equivalent Unicode ID, restart and re-addition remain consistent'],
    'public':[idxcase('delete_lookup',[{'op':'update','id':'a','text':'old alpha'},{'op':'delete','id':'a'},{'op':'search','query':'old'}],{'searches':[[]],'documents':{}},['searches','documents']),idxcase('unknown_delete',[{'op':'update','id':'a','text':'keep me'},{'op':'delete','id':'missing'},{'op':'search','query':'keep'}],{'searches':[[{'doc_id':'a','text':'keep me'}]],'orphans':0},['searches','orphans'])]}}

hidden={
'jobs':[scenario('rollback_and_restart','jobs',{'ops':[en('a'),{'op':'step','crash':'after_effect'},{'op':'restart'},en('b',5),{'op':'drain'}],'select':['balances','completed','effects','pending','crashes']},{'balances':{'team':8},'completed':2,'effects':2,'pending':0,'crashes':1}),scenario('payload_collision','jobs',{'ops':[en('a'),en('a',9),{'op':'drain'}],'select':['balances','errors','pending']},{'balances':{'team':3},'errors':1,'pending':0}),scenario('terminal_failure','jobs',{'ops':[en('r',4,failures=9),{'op':'drain'}],'select':['balances','states','attempts','pending']},{'balances':{},'states':{'r':'failed'},'attempts':{'r':3},'pending':0})],
'migration':[configcase('attempt_change',[modern(1000,1),modern(1000,4)],{'modern':[{'endpoint':'local-service','timeout_ms':1000,'max_attempts':1},{'endpoint':'local-service','timeout_ms':1000,'max_attempts':4}]},['modern']),configcase('legacy_fraction_and_zero_retries',[old(.25,0)],{'legacy':[{'endpoint':'local-service','timeout':.25,'retries':0}],'errors':0},['legacy','errors']),configcase('invalid_after_cached_valid',[modern(),modern(2000,0),{**old(),'timeout':True}],{'errors':2,'cache_entries':1},['errors','cache_entries'])],
'index':[idxcase('unaffected_and_restart',[{'op':'update','id':'a','text':'old alpha'},{'op':'update','id':'b','text':'keep beta'},{'op':'update','id':'a','text':'new gamma'},{'op':'restart'},{'op':'search','query':'keep'},{'op':'search','query':'old'}],{'searches':[[{'doc_id':'b','text':'keep beta'}],[]],'documents':{'a':{'version':2,'chunks':1},'b':{'version':1,'chunks':1}},'stored_chunks':2,'orphans':0},['searches','documents','stored_chunks','orphans']),idxcase('unicode_delete_readd',[{'op':'update','id':'e\u0301','text':'CAFÉ old'},{'op':'delete','id':'é'},{'op':'restart'},{'op':'search','query':'old'},{'op':'update','id':'é','text':'new café'},{'op':'search','query':'CAFÉ'}],{'searches':[[],[{'doc_id':'é','text':'new café'}]],'stored_chunks':1,'orphans':0},['searches','stored_chunks','orphans']),idxcase('delete_storage_cleanup',[{'op':'update','id':'a','text':'one two three'},{'op':'update','id':'b','text':'keep me'},{'op':'delete','id':'a'},{'op':'restart'}],{'documents':{'b':{'version':1,'chunks':1}},'stored_chunks':1,'orphans':0},['documents','stored_chunks','orphans']),idxcase('empty_and_invalid',[{'op':'update','id':'a','text':'words before'},{'op':'update','id':'a','text':''},{'op':'update','id':'','text':'bad'}],{'documents':{'a':{'version':2,'chunks':0}},'stored_chunks':0,'errors':1},['documents','stored_chunks','errors'])]}

initial={
'jobs_duplicate':{'results.py':JOBS['results.py'].replace("        existing = store.result(job['id'])\n        if existing is not None: return existing\n",'')},
'jobs_recovery':{'worker.py':JOBS['worker.py'].replace("        cached = self.store.result(job['id'])\n","        cached = self.store.result(job['id'])\n        if cached is not None: return cached\n")},
'migration_compat':{'parser.py':MIGRATION['parser.py'].replace("old_seconds(raw['timeout'])","raw['timeout']"),
                    'callers.py':MIGRATION['callers.py'].replace("plan['timeout_ms']/1000","plan['timeout_ms']"),
                    'policy.py':MIGRATION['policy.py'].replace('range(settings.max_attempts)','range(settings.max_attempts-1)')},
'migration_cache':{'cache.py':MIGRATION['cache.py'].replace("(settings.endpoint,settings.timeout_ms,settings.max_attempts)","settings.endpoint").replace('deepcopy(self.values[key])','dict(self.values[key])')},
'index_update':{'storage.py':INDEX['storage.py'].replace("            self.c.execute('DELETE FROM chunks WHERE doc_id=?',(doc_id,))\n",'',1)},
'index_delete':{'storage.py':INDEX['storage.py'].replace("    def delete(self,doc_id):\n        with self.c:\n            self.c.execute('DELETE FROM chunks WHERE doc_id=?',(doc_id,))\n","    def delete(self,doc_id):\n        with self.c:\n"), 'ingest.py':INDEX['ingest.py'].replace('self.store.delete(document_id(doc_id))','self.store.delete(doc_id)')}}
incomplete={
'jobs_duplicate':{'effects.py':JOBS['effects.py'].replace("    payload = job['payload']\n","    payload = job['payload']\n    if store.c.execute('SELECT 1 FROM effects WHERE recipient=?',(payload['recipient'],)).fetchone(): return\n")},
'jobs_recovery':{'worker.py':JOBS['worker.py'].replace("        value = commit(self.store,job,crash)","        self.queue.ack(delivery['seq'])\n        value = commit(self.store,job,crash)")},
'migration_compat':{'parser.py':MIGRATION['parser.py'].replace("raw['retries']+1","raw['retries']")},
'migration_cache':{'cache.py':MIGRATION['cache.py'].replace("(settings.endpoint,settings.timeout_ms,settings.max_attempts)","(settings.endpoint,settings.timeout_ms)")},
'index_update':{'storage.py':INDEX['storage.py'].replace("self.c.execute('DELETE FROM chunks WHERE doc_id=?',(doc_id,))","self.c.execute('DELETE FROM chunks')",1)},
'index_delete':{'lookup.py':INDEX['lookup.py'].replace("SELECT * FROM chunks ORDER BY doc_id,ordinal,id","SELECT * FROM chunks WHERE doc_id IN (SELECT id FROM documents) ORDER BY doc_id,ordinal,id")}}

hidden['migration'].append(configcase('returned_schedule_ownership',[modern(),modern()],{'last_deadlines':[2000,4000]},['last_deadlines']))
hidden['migration'][-1]['args'][0]['mutate_after_first']=True

if __name__=='__main__':
    ROOT.mkdir(exist_ok=False)
    families={'jobs':JOBS,'migration':MIGRATION,'index':INDEX}
    for family,files in families.items():
        path=ROOT/'applications'/family;path.mkdir(parents=True)
        for name,content in files.items():(path/name).write_text(content)
    for id,spec in cases.items():
        path=ROOT/id;path.mkdir()
        public={'task_id':id,'version':'development/1.0','origin':'authored controlled development application; not historical or real-world benchmark evidence',
                'family':spec['family'],'description':spec['description'],'acceptance':spec['acceptance'],
                'constraints':['Preserve module/public API contracts; source-only fixes','Do not modify diagnostics or read evaluator materials; no test-specific hardcoding'],
                'editable_files':[name for name in families[spec['family']] if name!='diagnostics.py'],'cases':spec['public']}
        (path/'public.json').write_text(json.dumps(public,indent=2,ensure_ascii=False)+'\n')
        for name,content in initial[id].items():
            (path/'initial-overrides').mkdir(exist_ok=True);(path/'initial-overrides'/name).write_text(content)
        private=ROOT/'private'/id;private.mkdir(parents=True)
        (private/'evaluator.json').write_text(json.dumps({'cases':hidden[spec['family']],'property_seeds':[17,29,43]},indent=2,ensure_ascii=False)+'\n')
        (private/'reference').mkdir()
        for name,content in families[spec['family']].items():(private/'reference'/name).write_text(content)
        (private/'incomplete').mkdir()
        candidate=dict(families[spec['family']])
        if id=='index_delete':candidate.update(initial[id])
        candidate.update(incomplete[id])
        for name,content in candidate.items():(private/'incomplete'/name).write_text(content)
    print('Authored six development cases with public contracts, private acceptance fixtures, references and incomplete candidates. No execution or inference.')
