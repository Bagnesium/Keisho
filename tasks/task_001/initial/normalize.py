def normalize(events):
    result = []
    for event in events:
        kind = event["kind"]
        if kind not in ("reserve", "release"):
            raise ValueError("unsupported event")
        amount = int(event.get("units", 0))
        if amount < 0:
            raise ValueError("negative units")
        result.append({"kind": kind, "id": str(event["id"]), "units": amount})
    return result

def normalized_count(events):
    return len(normalize(events))
