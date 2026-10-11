import math
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    endpoint: str
    timeout_ms: int
    max_attempts: int
    def __post_init__(self):
        if not isinstance(self.endpoint,str) or not self.endpoint: raise ValueError('endpoint')
        if type(self.timeout_ms) is not int or not 1<=self.timeout_ms<=120000: raise ValueError('timeout')
        if type(self.max_attempts) is not int or not 1<=self.max_attempts<=5: raise ValueError('attempts')

def old_seconds(value):
    if type(value) not in (int,float) or not math.isfinite(value) or value<=0: raise ValueError('old timeout')
    return int(value*1000)
