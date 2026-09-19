"""
show_extraction.py  --  look at ONE email going through the full pipeline.

    python show_extraction.py email_004
    python show_extraction.py email_512

Shows the audit trail and, if both documents were read, SI and BL side by side.
(The real comparison + report is Member C's job; the "differs" marker is only for eyeballing.)
"""
import sys

from modules.inbox import load_inbox
from modules.pipeline import process_email
from modules.schema import FIELDS

email_id = sys.argv[1] if len(sys.argv) > 1 else "email_004"

email = next((e for e in load_inbox() if e["email_id"] == email_id), None)
if email is None:
    sys.exit(f"{email_id} not found")

result = process_email(email)
print(f"\n{email_id} | {email['subject'][:80]}")
print(f"category: {result['category']}   status: {result['status']}   review_reason: {result.get('review_reason')}")
print("\nAudit trail:")
for log in result["audit_log"]:
    print(f"  - {log['step']}: {log['message']}")

ext = result.get("extraction")
if not ext or not (ext["si"] and ext["bl"]):
    sys.exit()
for note in ext["review_notes"]:
    print("  note:", note)

si, bl = ext["si"], ext["bl"]
print(f"\n{'field':<19}{'SI':<42}{'BL':<42}")
print("-" * 105)
for f in FIELDS:
    s, b = si["fields"].get(f), bl["fields"].get(f)
    mark = "" if s is None or b is None else ("  ok" if si["keys"][f] == bl["keys"][f] else "  <-- differs")
    print(f"{f:<19}{str(s)[:40]:<42}{str(b)[:40]:<42}{mark}")