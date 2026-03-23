from __future__ import annotations

import json
from pathlib import Path


class SchoolResolver:
    def __init__(self, aliases: dict[str, str]) -> None:
        self._aliases = {key.casefold(): value for key, value in aliases.items()}

    @classmethod
    def load(cls, path: Path) -> 'SchoolResolver':
        return cls(json.loads(path.read_text()))

    def resolve(self, school_name: str | None) -> str | None:
        if not school_name:
            return None
        return self._aliases.get(school_name.casefold())
