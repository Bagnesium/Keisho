from normalize import terms

def search(store,query):
    wanted=set(terms(query))
    if not wanted: return []
    rows=store.c.execute('SELECT * FROM chunks ORDER BY doc_id,ordinal,id').fetchall()
    return [{'doc_id':row['doc_id'],'text':row['text']} for row in rows if wanted <= set(terms(row['text']))]
