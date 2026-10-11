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
