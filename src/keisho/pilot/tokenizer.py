"""Pinned public BPE asset; constructing a counter never downloads implicitly."""

import hashlib
import importlib.metadata
import os
from pathlib import Path
import shutil

from keisho.agents.base import TokenCount
from keisho.core import require
from .tasks import REPO

VOCAB_URL = "https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken"
VOCAB_SHA256 = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"


class NativeTokenizer:
    def __init__(self, asset: Path = REPO / ".cache/tokenizers/o200k_base.tiktoken"):
        require(asset.is_file(), "tokenizer asset missing; run explicit prepare-tokenizer command")
        require(hashlib.sha256(asset.read_bytes()).hexdigest() == VOCAB_SHA256, "tokenizer asset hash mismatch")
        cached = asset.parent / hashlib.sha1(VOCAB_URL.encode()).hexdigest()
        if not cached.exists():
            shutil.copyfile(asset, cached)
        require(hashlib.sha256(cached.read_bytes()).hexdigest() == VOCAB_SHA256, "tokenizer cache corrupted")
        import tiktoken
        require(importlib.metadata.version("tiktoken") == "0.12.0", "tiktoken version differs from locked pilot")
        # Library cache is explicitly scoped, prepopulated and hash-checked.
        old = os.environ.get("TIKTOKEN_CACHE_DIR")
        os.environ["TIKTOKEN_CACHE_DIR"] = str(asset.parent)
        try:
            self.encoding = tiktoken.get_encoding("o200k_base")
        finally:
            if old is None:
                os.environ.pop("TIKTOKEN_CACHE_DIR", None)
            else:
                os.environ["TIKTOKEN_CACHE_DIR"] = old

    def count(self, text: str) -> TokenCount:
        return TokenCount(len(self.encoding.encode(text, disallowed_special=())), "tiktoken/0.12.0:o200k_base:isolated-text", True)
