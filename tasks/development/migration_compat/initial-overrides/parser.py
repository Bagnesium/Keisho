from validation import Settings, old_seconds

def parse(raw):
    if not isinstance(raw,dict): raise ValueError('config must be an object')
    if raw.get('version',1)==1:
        if set(raw)!={'endpoint','timeout','retries'}: raise ValueError('legacy fields or mixed representation')
        if type(raw['retries']) is not int: raise ValueError('legacy retries')
        return Settings(raw['endpoint'],raw['timeout'],raw['retries']+1)
    if raw.get('version')!=2 or set(raw)!={'version','endpoint','request'}: raise ValueError('version or fields')
    request=raw['request']
    if not isinstance(request,dict) or set(request)!={'timeout_ms','max_attempts'}: raise ValueError('request')
    return Settings(raw['endpoint'],request['timeout_ms'],request['max_attempts'])

def serialize(settings):
    return {'version':2,'endpoint':settings.endpoint,'request':{'timeout_ms':settings.timeout_ms,'max_attempts':settings.max_attempts}}
