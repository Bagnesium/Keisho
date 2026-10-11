from normalize import normalize

def replay(capacity, events):
    state = {"active": {}, "reserved": 0, "releases": 0}
    for event in normalize(events):
        key = event["id"]
        if event["kind"] == "reserve":
            units = event["units"]
            state["active"][key] = units
            state["reserved"] += units
        else:
            previous = state["active"].pop(key, None)
            if previous is not None:
                state["reserved"] -= previous
                state["releases"] += 1
    return {"available": capacity - state["reserved"], "active": state["active"], "releases": state["releases"]}
