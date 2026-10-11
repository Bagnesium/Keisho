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
