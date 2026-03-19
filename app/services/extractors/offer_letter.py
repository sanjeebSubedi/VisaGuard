import re

from app.services.extractors.base import ExtractedFact


class OfferLetterExtractor:
    def extract(self, text: str) -> list[ExtractedFact]:
        facts: list[ExtractedFact] = []
        if match := re.search(r"Employer:\s*(.+)", text):
            facts.append(ExtractedFact("employer_name", match.group(1).strip(), 0.95, "offer_letter:employer_name"))
        if match := re.search(r"Title:\s*(.+)", text):
            facts.append(ExtractedFact("job_title", match.group(1).strip(), 0.9, "offer_letter:job_title"))
        if match := re.search(r"Start Date:\s*([0-9-]+)", text):
            facts.append(ExtractedFact("employment_start_date", match.group(1), 0.95, "offer_letter:employment_start_date"))
        return facts
