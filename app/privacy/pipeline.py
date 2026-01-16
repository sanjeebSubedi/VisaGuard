"""
Privacy Pipeline - PII Scrubbing Service

Uses Microsoft Presidio to detect and redact sensitive information from documents
BEFORE they are sent to any LLM or stored in the vector database.

Key principle: Scrub ONCE on upload, store the scrubbed text.
"""

from typing import Optional

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from app.core.config import PII_ENTITIES_TO_DETECT


class PrivacyPipeline:
    """
    Centralized PII detection and anonymization service.
    
    Usage:
        pipeline = PrivacyPipeline()
        scrubbed_text = pipeline.scrub(raw_text)
    """
    
    def __init__(
        self,
        entities_to_detect: Optional[list[str]] = None,
        language: str = "en"
    ):
        """
        Initialize the privacy pipeline.
        
        Args:
            entities_to_detect: List of PII entity types to detect and redact.
                              Defaults to config.PII_ENTITIES_TO_DETECT.
            language: Language code for NLP processing.
        """
        self.entities = entities_to_detect or PII_ENTITIES_TO_DETECT
        self.language = language
        
        # Initialize Presidio engines
        self._init_analyzer()
        self._init_anonymizer()
    
    def _init_analyzer(self) -> None:
        """Initialize the Presidio Analyzer with NLP engine and custom recognizers."""
        # Use spaCy as the NLP engine
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": self.language, "model_name": "en_core_web_sm"}],
        }
        
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers(nlp_engine=nlp_engine)
        
        # --- CUSTOM F-1 SPECIFIC RECOGNIZERS ---
        
        # 1. SEVIS ID (Format: N followed by 10 digits, e.g., N0012345678)
        sevis_pattern = Pattern(name="sevis_pattern", regex=r"N\d{10}", score=0.95)
        sevis_recognizer = PatternRecognizer(
            supported_entity="SEVIS_ID",
            patterns=[sevis_pattern],
            supported_language=self.language,
        )
        registry.add_recognizer(sevis_recognizer)
        
        # 2. USCIS Case Number (Format: 3 letters + 10 digits, e.g., YSC1234567890)
        uscis_pattern = Pattern(name="uscis_pattern", regex=r"[A-Z]{3}\d{10}", score=0.95)
        uscis_recognizer = PatternRecognizer(
            supported_entity="USCIS_CASE_NO",
            patterns=[uscis_pattern],
            supported_language=self.language,
        )
        registry.add_recognizer(uscis_recognizer)
        
        # 3. Alien Registration Number / A-Number (Format: A followed by 8-9 digits)
        a_number_pattern = Pattern(name="a_number_pattern", regex=r"A\d{8,9}", score=0.95)
        a_number_recognizer = PatternRecognizer(
            supported_entity="A_NUMBER",
            patterns=[a_number_pattern],
            supported_language=self.language,
        )
        registry.add_recognizer(a_number_recognizer)
        
        self.analyzer = AnalyzerEngine(
            nlp_engine=nlp_engine,
            registry=registry
        )
    
    def _init_anonymizer(self) -> None:
        """Initialize the Presidio Anonymizer with F-1 specific operators."""
        self.anonymizer = AnonymizerEngine()
        
        # Define how each entity type should be replaced
        self.operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "[PERSON_NAME]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL]"}),
            "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE]"}),
            "US_SSN": OperatorConfig("replace", {"new_value": "[SSN_REDACTED]"}),
            "US_PASSPORT": OperatorConfig("replace", {"new_value": "[PASSPORT_REDACTED]"}),
            "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[CREDIT_CARD]"}),
            # F-1 specific entities
            "SEVIS_ID": OperatorConfig("replace", {"new_value": "[SEVIS_ID]"}),
            "USCIS_CASE_NO": OperatorConfig("replace", {"new_value": "[USCIS_CASE]"}),
            "A_NUMBER": OperatorConfig("replace", {"new_value": "[A_NUMBER]"}),
            # Fallback
            "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
        }
    
    def analyze(self, text: str) -> list[dict]:
        """
        Analyze text for PII entities without redacting.
        
        Returns a list of detected entities with their locations.
        """
        results = self.analyzer.analyze(
            text=text,
            entities=self.entities,
            language=self.language
        )
        
        return [
            {
                "entity_type": r.entity_type,
                "start": r.start,
                "end": r.end,
                "score": r.score,
                "text": text[r.start:r.end]
            }
            for r in results
        ]
    
    def scrub(self, text: str) -> str:
        """
        Detect and redact all PII from the given text.
        
        This is the main method to use before sending text to LLMs.
        
        Args:
            text: Raw text that may contain PII.
            
        Returns:
            Text with all detected PII replaced with placeholders.
        """
        # Analyze for PII
        analyzer_results = self.analyzer.analyze(
            text=text,
            entities=self.entities,
            language=self.language
        )
        
        if not analyzer_results:
            return text
        
        # Anonymize detected entities
        anonymized = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analyzer_results,
            operators=self.operators
        )
        
        return anonymized.text
    
    def scrub_with_report(self, text: str) -> tuple[str, list[dict]]:
        """
        Scrub text and return both the scrubbed text and a report of what was redacted.
        
        Useful for audit logging.
        
        Returns:
            Tuple of (scrubbed_text, list of redaction details)
        """
        detected = self.analyze(text)
        scrubbed = self.scrub(text)
        
        return scrubbed, detected


# Singleton instance for convenience
_pipeline: Optional[PrivacyPipeline] = None


def get_privacy_pipeline() -> PrivacyPipeline:
    """Get or create the global privacy pipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = PrivacyPipeline()
    return _pipeline


def scrub_pii(text: str) -> str:
    """Convenience function to scrub PII from text."""
    return get_privacy_pipeline().scrub(text)
