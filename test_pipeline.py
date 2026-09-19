from modules.inbox import load_inbox
from modules.pipeline import process_email

inbox = load_inbox()

for i, email in enumerate(inbox):
    result = process_email(email)

    print("Email ID:", result["email_id"])
    print("Category:", result["category"])
    print("Confidence:", result["classification_confidence"])
    print("Scores:", result["classification_scores"])
    print("Status:", result["status"])

    print("Audit Trail:")

    for log in result["audit_log"]:
        print("-", log["step"], ":", log["message"])

    if "document_job" in result:
        print("Document Job:", result["document_job"])

    print("-" * 70)

    if i == 9:
        break