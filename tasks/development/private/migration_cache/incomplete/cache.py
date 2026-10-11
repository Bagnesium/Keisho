from copy import deepcopy

class Cache:
    def __init__(self): self.values={}
    def key(self,settings): return (settings.endpoint,settings.timeout_ms)
    def get_or_build(self,settings,build):
        key=self.key(settings)
        if key not in self.values: self.values[key]=build(settings)
        return deepcopy(self.values[key])
