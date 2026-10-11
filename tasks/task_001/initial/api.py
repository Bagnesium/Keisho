from ledger import replay

def availability(capacity, events):
    state = replay(capacity, events)
    return state["available"]
