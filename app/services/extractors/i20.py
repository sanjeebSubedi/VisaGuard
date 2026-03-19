import re

from app.services.extractors.base import ExtractedFact


class I20Extractor:
    def extract(self, text: str) -> list[ExtractedFact]:
        facts: list[ExtractedFact] = []
        if match := re.search(r"Program Start Date:\s*([0-9-]+)", text):
            facts.append(ExtractedFact("program_start_date", match.group(1), 0.95, "i20:program_start_date"))
        if match := re.search(r"CIP Code:\s*([0-9.]+)", text):
            facts.append(ExtractedFact("cip_code", match.group(1), 0.95, "i20:cip_code"))
        if match := re.search(r"School Name:\s*(.+)", text):
            facts.append(ExtractedFact("school_name", match.group(1).strip(), 0.9, "i20:school_name"))
        return facts
