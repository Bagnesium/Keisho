from normalize import document_id, content
from chunking import chunks
from lookup import search
from metadata import snapshot

class Index:
    def __init__(self,store): self.store=store
    def update(self,doc_id,text):
        return self.store.put(document_id(doc_id),content(text),chunks(content(text)))
    def delete(self,doc_id): self.store.delete(doc_id)
    def search(self,query): return search(self.store,query)
    def metadata(self): return snapshot(self.store)
