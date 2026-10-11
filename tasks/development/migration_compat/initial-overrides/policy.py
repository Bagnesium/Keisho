def build(settings):
    return {'endpoint':settings.endpoint,'timeout_ms':settings.timeout_ms,'max_attempts':settings.max_attempts,
            'attempt_deadlines_ms':[settings.timeout_ms*(index+1) for index in range(settings.max_attempts-1)]}
