from app.services.extractors.ead import EADExtractor
from app.services.extractors.i20 import I20Extractor
from app.services.extractors.offer_letter import OfferLetterExtractor


EXTRACTORS = {
    "i20": I20Extractor,
    "ead": EADExtractor,
    "offer_letter": OfferLetterExtractor,
}


def get_extractor(document_type: str):
    try:
        return EXTRACTORS[document_type]()
    except KeyError as exc:
        raise ValueError(f"Unsupported document type: {document_type}") from exc
