KEYS = {"demo": "public-test-key"}
CACHE = {}

def get_key(key_id):
    if key_id not in CACHE:
        CACHE[key_id] = KEYS[key_id]
    return CACHE[key_id]

def clear_cache():
    CACHE.clear()

def cache_identity():
    clear_cache()
    return get_key("demo") == KEYS["demo"]
