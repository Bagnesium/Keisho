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
