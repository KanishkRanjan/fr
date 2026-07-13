"""Strategy pattern: one interface, interchangeable isomorphism backends.

Swapping algorithms is a single string: get_engine("bliss") / get_engine("saucy"),
driven by the API's `algorithm` field or the VALIDATOR_ALGORITHM env var.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


class EngineError(RuntimeError):
    """Native binary missing, crashed, or produced unparseable output."""


@dataclass
class EngineResult:
    isomorphic: bool
    engine_ms: float = 0.0
    generators: int = 0


class IsomorphismEngine(ABC):
    name = 'abstract'

    @abstractmethod
    def are_isomorphic(self, g1, g2) -> EngineResult:
        """Decide colored-graph isomorphism of two ColoredGraphs."""


def get_engine(name):
    key = (name or '').strip().lower()
    if key not in ENGINES:
        raise EngineError(
            f'unknown algorithm "{name}" — expected one of: {", ".join(sorted(ENGINES))}')
    return ENGINES[key]()


# populated at the bottom to avoid circular imports
from .bliss_engine import BlissEngine   # noqa: E402
from .saucy_engine import SaucyEngine   # noqa: E402

ENGINES = {
    'bliss': BlissEngine,
    'saucy': SaucyEngine,
}
