"""
Privacy pipeline for PII detection and redaction.

Local-only regex redaction with optional local LLM pass for extra coverage.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Iterable

from langchain_ollama import ChatOllama
from pydantic import BaseModel


@dataclass(frozen=True)
class DetectedEntity:
    entity_type: str
    text: str
    start: int
    end: int


class PrivacyPipeline:
    """Detect and scrub PII from text."""

    def __init__(
        self,
        use_llm: bool = False,
        llm_model: str | None = None,
        max_chunk_chars: int = 4000,
    ) -> None:
        self._patterns: list[tuple[str, re.Pattern[str]]] = [
            ("SEVIS_ID", re.compile(r"\bN\d{10}\b")),
            ("USCIS_CASE", re.compile(r"\b[A-Z]{3}\d{10}\b")),
            ("A_NUMBER", re.compile(r"\bA\d{8,9}\b")),
            ("US_SSN", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
            (
                "EMAIL",
                re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            ),
            (
                "PHONE",
                re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
            ),
            ("PERSON_NAME", re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b")),
        ]

        self._redaction_tokens = {
            "US_SSN": "[SSN_REDACTED]",
            "EMAIL": "[EMAIL]",
            "PHONE": "[PHONE]",
            "PERSON_NAME": "[PERSON_NAME]",
            "SEVIS_ID": "[SEVIS_ID]",
            "USCIS_CASE": "[USCIS_CASE]",
            "A_NUMBER": "[A_NUMBER]",
        }
        self._use_llm = use_llm
        self._llm_model = llm_model or os.getenv(
            "VISAGUARD_OLLAMA_MODEL", "qwen3:4b-instruct"
        )
        self._max_chunk_chars = max_chunk_chars

    def analyze(self, text: str) -> list[dict]:
        """Return detected entities with type and text."""
        entities = list(self._detect(text))
        entities.sort(key=lambda e: e.start)
        return [
            {
                "entity_type": e.entity_type,
                "text": e.text,
                "start": e.start,
                "end": e.end,
            }
            for e in entities
        ]

    def scrub(self, text: str) -> str:
        """Return text with PII redacted."""
        scrubbed = text
        for entity_type, pattern in self._patterns:
            token = self._redaction_tokens.get(entity_type, "[REDACTED]")
            scrubbed = pattern.sub(token, scrubbed)
        if self._use_llm:
            scrubbed = self._llm_scrub(scrubbed)
        return scrubbed

    def scrub_with_report(self, text: str) -> tuple[str, list[dict]]:
        """Return scrubbed text and entity report."""
        return self.scrub(text), self.analyze(text)

    def _detect(self, text: str) -> Iterable[DetectedEntity]:
        for entity_type, pattern in self._patterns:
            for match in pattern.finditer(text):
                yield DetectedEntity(
                    entity_type=entity_type,
                    text=match.group(0),
                    start=match.start(),
                    end=match.end(),
                )

    def _llm_scrub(self, text: str) -> str:
        """Best-effort local LLM pass to find missed PII."""
        if not text.strip():
            return text

        class LLMEntity(BaseModel):
            entity_type: str
            text: str

        class LLMEntities(BaseModel):
            entities: list[LLMEntity]

        prompt_template = (
            "Identify any remaining PII in the text. "
            "Return JSON with a single key 'entities' which is a list of objects "
            "with 'entity_type' and 'text'. "
            "Allowed entity_type values: SEVIS_ID, USCIS_CASE, A_NUMBER, US_SSN, "
            "EMAIL, PHONE, PERSON_NAME. "
            'If none, return {"entities": []}. '
            "Do not include code fences.\n\nTEXT:\n{chunk}"
        )

        llm = ChatOllama(model=self._llm_model, temperature=0)
        structured_llm = llm.with_structured_output(LLMEntities)

        chunks: list[str] = []
        for i in range(0, len(text), self._max_chunk_chars):
            chunks.append(text[i : i + self._max_chunk_chars])

        redacted_chunks: list[str] = []
        for chunk in chunks:
            try:
                result = structured_llm.invoke(prompt_template.format(chunk=chunk))
                redacted_chunk = chunk
                for entity in result.entities:
                    token = self._redaction_tokens.get(entity.entity_type, "[REDACTED]")
                    if entity.text:
                        redacted_chunk = re.sub(
                            re.escape(entity.text),
                            token,
                            redacted_chunk,
                        )
                redacted_chunks.append(redacted_chunk)
            except Exception:
                redacted_chunks.append(chunk)

        return "".join(redacted_chunks)
