def apply(store, job):
    payload = job['payload']
    if store.c.execute('SELECT 1 FROM effects WHERE recipient=?',(payload['recipient'],)).fetchone(): return
    store.c.execute('INSERT INTO effects(job_id,recipient,amount) VALUES(?,?,?)', (job['id'],payload['recipient'],payload['amount']))
