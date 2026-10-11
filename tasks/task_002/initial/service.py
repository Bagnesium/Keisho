from writer import encode_many
from reader import decode_stream

def round_trip(messages):
    return decode_stream(encode_many(messages))

def chunked_round_trip(messages, split):
    data = encode_many(messages)
    chunks = [data[:split], data[split:]]
    return decode_stream(b"".join(chunks))
