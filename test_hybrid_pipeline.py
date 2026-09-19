from modules.inbox import load_inbox
from modules.pipeline import process_email


inbox = load_inbox()

for email in inbox:

    if email["email_id"] == "email_006":

        result = process_email(email)

        print("Email ID:", result["email_id"])
        print("Category:", result["category"])
        print("Confidence:", result["classification_confidence"])
        print("Source:", result["classification_source"])
        print("Reason:", result["classification_reason"])
        print("Status:", result["status"])

        print("\nAudit Trail:")

        for item in result["audit_log"]:
            print("-", item["step"], ":", item["message"])

        break