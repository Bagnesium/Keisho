def decode_stream(data):
    messages = []
    offset = 0
    while offset < len(data):
        separator = data.index(b":", offset)
        size = int(data[offset:separator])
        start = separator + 1
        stop = start + size
        body = data[start:stop]
        if len(body) != size:
            raise ValueError("incomplete frame")
        messages.append(body.decode("utf-8"))
        offset = stop
    return messages
