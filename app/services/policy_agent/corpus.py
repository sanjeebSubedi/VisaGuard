from __future__ import annotations

from pathlib import Path

from app.services.policy_agent.types import RetrievedSource


def load_policy_sources(directory: Path) -> list[RetrievedSource]:
    sources: list[RetrievedSource] = []
    for path in sorted(directory.glob('*.md')):
        raw = path.read_text().strip()
        metadata, body = _split_front_matter(raw)
        sources.append(
            RetrievedSource(
                source_id=metadata['source_id'],
                title=metadata['title'],
                citation=metadata['citation'],
                source_type=metadata.get('source_type', 'policy'),
                text=body.strip(),
                score=1.0,
            )
        )
    return sources


def _split_front_matter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith('---\n'):
        raise ValueError('Policy source is missing front matter')
    _, front_matter, body = raw.split('---\n', 2)
    metadata = {}
    for line in front_matter.strip().splitlines():
        key, value = line.split(':', 1)
        metadata[key.strip()] = value.strip()
    return metadata, body
