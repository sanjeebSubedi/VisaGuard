from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from langgraph.checkpoint.sqlite import SqliteSaver

from app.core.config import Settings


@contextmanager
def build_checkpointer(settings: Settings | None = None) -> Iterator[SqliteSaver]:
    runtime_settings = settings or Settings()
    with SqliteSaver.from_conn_string(runtime_settings.langgraph_checkpointer_path) as saver:
        yield saver
