from __future__ import annotations

import json
import math
import re
from pathlib import Path

from app.services.policy_agent.cip_loader import CIPDataset
from app.services.policy_agent.corpus import load_policy_sources

TOKEN_RE = re.compile(r"[a-z0-9]+")


def build_policy_index(*, cip_dataset_path: Path, policy_sources_dir: Path, output_path: Path) -> Path:
    cip_dataset = CIPDataset.load(cip_dataset_path)
    documents = []

    for entry in cip_dataset._entries.values():
        text = f"{entry.title}\n\n{entry.description}"
        documents.append(_index_document(
            source_id=f"cip-{entry.cip_code}",
            title=entry.title,
            citation=f"CIP {entry.cip_code}",
            source_type="cip",
            text=text,
        ))

    for source in load_policy_sources(policy_sources_dir):
        documents.append(_index_document(
            source_id=source.source_id,
            title=source.title,
            citation=source.citation,
            source_type=source.source_type,
            text=source.text,
        ))

    payload = {"documents": documents}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2))
    return output_path


def _index_document(*, source_id: str, title: str, citation: str, source_type: str, text: str) -> dict[str, object]:
    tokens = _tokenize(text)
    term_freqs: dict[str, int] = {}
    for token in tokens:
        term_freqs[token] = term_freqs.get(token, 0) + 1
    norm = math.sqrt(sum(count * count for count in term_freqs.values())) or 1.0
    return {
        "source_id": source_id,
        "title": title,
        "citation": citation,
        "source_type": source_type,
        "text": text,
        "term_freqs": term_freqs,
        "token_count": len(tokens),
        "norm": norm,
    }


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())
