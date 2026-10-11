from keisho.state.schema import KeishoState
from .serializer import serialize

COMPILER_VERSION = "fixed-json/0.1.0"


def compile_fixed(state: KeishoState) -> str:
    """The exact same canonical serialization for every successor."""
    return serialize(state)
