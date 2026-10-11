from parser import parse
from cache import Cache
from policy import build

class Service:
    def __init__(self): self.cache=Cache()
    def configure(self,raw): return self.cache.get_or_build(parse(raw),build)
