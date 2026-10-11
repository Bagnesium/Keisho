def apply(store, job):
    payload = job['payload']
    store.c.execute('INSERT INTO effects(job_id,recipient,amount) VALUES(?,?,?)', (job['id'],payload['recipient'],payload['amount']))
