def legacy_options(plan):
    return {'endpoint':plan['endpoint'],'timeout':plan['timeout_ms'],'retries':plan['max_attempts']-1}
def modern_options(plan):
    return {'endpoint':plan['endpoint'],'timeout_ms':plan['timeout_ms'],'max_attempts':plan['max_attempts']}
