def encode(text):
    header = str(len(text)).encode("ascii") + b":"
    return header + text.encode("utf-8")

def encode_many(messages):
    return b"".join(encode(text) for text in messages)
