import hashlib
from canonical import canonical
from keys import get_key, clear_cache
from middleware import prepare

def signature(request, key):
    return hashlib.sha256((key + "|" + canonical(request)).encode("utf-8")).hexdigest()

def signed_request(payload, metadata=None, omit=False):
    request = {"payload": payload, "key_id": "demo"}
    if not omit:
        request["metadata"] = {} if metadata is None else metadata
    request["signature"] = signature(request, get_key("demo"))
    return request

def authenticate(payload, metadata=None, omit=False):
    request = signed_request(payload, metadata, omit)
    prepared = prepare(request)
    valid = signature(prepared, get_key(prepared["key_id"])) == request["signature"]
    return {"ok": valid, "error": None if valid else "cached key mismatch"}

def authenticate_after_clear(payload):
    request = signed_request(payload, {})
    clear_cache()
    prepared = prepare(request)
    return signature(prepared, get_key("demo")) == request["signature"]
