"""Test table redaction pattern"""

import re

text = """| **SURNAME/PRIMARY NAME** | **GIVEN NAME** | **Class of Admission** |
| ------------------------ | -------------- | ---------------------- |
| Subedi                   | Sanjeeb        | F-1                    |

SOME OTHER TEXT"""

print("Original:")
print(text)
print("\n" + "="*60 + "\n")

# Test pattern - need to capture the full row and replace name cells
pattern = r'(\| \*\*SURNAME/PRIMARY NAME\*\*.*\n\|.*\n)\|\s*(\w+)\s*\|\s*(\w+)\s*\|(.+)'

result = re.sub(
    pattern,
    r'\1| [SURNAME] | [GIVEN_NAME] |\4',
    text,
    flags=re.IGNORECASE
)

print("After redaction:")
print(result)

# Check if it worked
if "Subedi" in result or "Sanjeeb" in result:
    print("\n❌ FAILED: Names still present")
else:
    print("\n✅ SUCCESS: Names redacted")
