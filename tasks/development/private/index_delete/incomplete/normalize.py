import unicodedata

def document_id(value):
    if not isinstance(value,str) or not value.strip(): raise ValueError('document identity')
    return unicodedata.normalize('NFC',value.strip())
def content(value):
    if not isinstance(value,str): raise ValueError('document content')
    return ' '.join(unicodedata.normalize('NFC',value).split())
def terms(value): return content(value).casefold().split()
