MAX_ATTEMPTS = 3
def delay(attempt): return min(8, 2 ** attempt)
def can_retry(attempt): return attempt < MAX_ATTEMPTS
