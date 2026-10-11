import sqlite3

class Store:
    def __init__(self,path):
        self.c=sqlite3.connect(path); self.c.row_factory=sqlite3.Row
        self.c.executescript('CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY,content TEXT NOT NULL,version INTEGER NOT NULL); CREATE TABLE IF NOT EXISTS chunks(id TEXT PRIMARY KEY,doc_id TEXT NOT NULL,ordinal INTEGER NOT NULL,text TEXT NOT NULL,version INTEGER NOT NULL);')
    def put(self,doc_id,text,parts):
        row=self.c.execute('SELECT * FROM documents WHERE id=?',(doc_id,)).fetchone()
        if row and row['content']==text: return False
        version=row['version']+1 if row else 1
        with self.c:
            self.c.execute('INSERT OR REPLACE INTO documents VALUES(?,?,?)',(doc_id,text,version))
            for ordinal,part in enumerate(parts):
                self.c.execute('INSERT INTO chunks VALUES(?,?,?,?,?)',(f'{doc_id}:{version}:{ordinal}',doc_id,ordinal,part,version))
        return True
    def delete(self,doc_id):
        with self.c:
            self.c.execute('DELETE FROM chunks WHERE doc_id=?',(doc_id,))
            self.c.execute('DELETE FROM documents WHERE id=?',(doc_id,))
