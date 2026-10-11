def snapshot(store):
    return {'documents':{row['id']:{'version':row['version'],'chunks':row['n']} for row in store.c.execute('SELECT d.id,d.version,COUNT(c.id) n FROM documents d LEFT JOIN chunks c ON d.id=c.doc_id GROUP BY d.id ORDER BY d.id')},
            'stored_chunks':store.c.execute('SELECT COUNT(*) FROM chunks').fetchone()[0],
            'orphans':store.c.execute('SELECT COUNT(*) FROM chunks c LEFT JOIN documents d ON d.id=c.doc_id WHERE d.id IS NULL').fetchone()[0]}
