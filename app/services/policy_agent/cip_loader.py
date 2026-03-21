from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class CIPNotFoundError(KeyError):
    pass


@dataclass(frozen=True)
class CIPEntry:
    cip_code: str
    title: str
    description: str


class CIPDataset:
    def __init__(self, entries: dict[str, CIPEntry]) -> None:
        self._entries = entries

    @classmethod
    def load(cls, path: Path) -> "CIPDataset":
        payload = json.loads(path.read_text())
        entries = {
            item["cip_code"]: CIPEntry(
                cip_code=item["cip_code"],
                title=item["title"],
                description=item["description"],
            )
            for item in payload
        }
        return cls(entries)

    def get(self, cip_code: str) -> CIPEntry:
        try:
            return self._entries[cip_code]
        except KeyError as exc:
            raise CIPNotFoundError(f"Unknown CIP code: {cip_code}") from exc
