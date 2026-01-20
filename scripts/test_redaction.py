"""
Test script to debug context-aware redaction
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.privacy.pipeline import PrivacyPipeline

# Test text with technical terms and addresses
test_text = """
Mr. John Smith has been offered a position.

The role involves:
- Developing RESTful APIs using Python and FastAPI
- Working with PostgreSQL databases
- Located at 1234 Innovation Drive

Supervisor: Jane Doe
Email: jane@example.com
"""

print("Testing context-aware redaction:")
print("=" * 60)

pipeline = PrivacyPipeline()

# First, analyze to see what's detected
detected = pipeline.analyze(test_text)
print("\n🔍 Detected entities:")
for entity in detected:
    print(f"  - {entity['entity_type']}: '{entity['text']}' (score: {entity['score']:.2f})")

# Now scrub with filtering
scrubbed = pipeline.scrub(test_text)

print("\n✅ Scrubbed text:")
print(scrubbed)

print("\n📊 Comparison:")
print(f"Original length: {len(test_text)}")
print(f"Scrubbed length: {len(scrubbed)}")
print(f"Characters changed: {abs(len(scrubbed) - len(test_text))}")
