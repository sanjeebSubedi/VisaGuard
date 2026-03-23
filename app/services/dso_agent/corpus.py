from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DSOSource:
    source_id: str
    title: str
    citation: str
    source_type: str
    text: str
    school_key: str | None = None
    source_path: str | None = None


def load_dso_sources(*, federal_sources_dir: Path, university_sources_root: Path) -> list[DSOSource]:
    sources: list[DSOSource] = []
    if federal_sources_dir.exists():
        for path in sorted(federal_sources_dir.rglob('*.md')):
            sources.append(_load_markdown_source(path=path, source_type='federal', school_key=None))
    if university_sources_root.exists():
        for school_dir in sorted(p for p in university_sources_root.iterdir() if p.is_dir()):
            for path in sorted(school_dir.rglob('*.md')):
                sources.append(_load_markdown_source(path=path, source_type='university', school_key=school_dir.name))
    return sources


def _load_markdown_source(*, path: Path, source_type: str, school_key: str | None) -> DSOSource:
    text = path.read_text().strip()
    title = _extract_title(text, fallback=path.stem.replace('_', ' ').title())
    citation = path.stem.replace('_', ' ').title()
    source_id = f'{source_type}-{school_key or "global"}-{path.stem}'
    return DSOSource(
        source_id=source_id,
        title=title,
        citation=citation,
        source_type=source_type,
        text=text,
        school_key=school_key,
        source_path=str(path),
    )


def _extract_title(text: str, *, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            return stripped.lstrip('#').strip() or fallback
    return fallback
