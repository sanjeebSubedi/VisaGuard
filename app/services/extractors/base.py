from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ExtractedFact:
    field_name: str
    value: str
    confidence: float
    source_location: str
    status: str = "provisional"


class Extractor(Protocol):
    def extract(self, text: str) -> list[ExtractedFact]: ...
