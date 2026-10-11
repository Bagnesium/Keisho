import json
from effects import apply

class Crash(RuntimeError): pass

def commit(store, job, crash=None):
    with store.c:
        apply(store, job)
        if crash == 'after_effect': raise Crash('interruption inside result transaction')
        value = {'job_id':job['id'], 'amount':job['payload']['amount']}
        store.c.execute('INSERT OR REPLACE INTO results(job_id,value) VALUES(?,?)',(job['id'],json.dumps(value,sort_keys=True)))
        store.c.execute("UPDATE jobs SET state='done' WHERE id=?",(job['id'],))
    return value
