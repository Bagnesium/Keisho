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
