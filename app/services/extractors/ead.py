import re

from app.services.extractors.base import ExtractedFact


class EADExtractor:
    def extract(self, text: str) -> list[ExtractedFact]:
        facts: list[ExtractedFact] = []
        if match := re.search(r"Card Expires:\s*([0-9-]+)", text):
            facts.append(ExtractedFact("employment_authorized_until", match.group(1), 0.95, "ead:employment_authorized_until"))
        if match := re.search(r"Category:\s*([A-Z0-9]+)", text):
            facts.append(ExtractedFact("ead_category", match.group(1), 0.9, "ead:ead_category"))
        return facts
