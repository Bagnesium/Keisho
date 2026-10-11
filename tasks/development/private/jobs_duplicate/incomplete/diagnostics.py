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
