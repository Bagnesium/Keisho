import json

def canonical(request):
    return json.dumps({"payload": request["payload"], "metadata": request.get("metadata", {})}, sort_keys=True, separators=(",", ":"))
