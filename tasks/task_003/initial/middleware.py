def prepare(request):
    result = dict(request)
    metadata = request.get("metadata")
    if not metadata:
        metadata = {"client": "unknown"}
    result["metadata"] = dict(metadata)
    return result
