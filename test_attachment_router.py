from modules.inbox import load_inbox
from modules.classifier import classify_email
from modules.attachment_router import route_attachments

inbox = load_inbox()

for email in inbox:
    category = classify_email(email)

    if category == "document_comparison":
        result = route_attachments(email)

        print("Email ID:", email["email_id"])
        print("SI:", result["si_file"])
        print("BL:", result["bl_file"])
        print("Status:", result["status"])
        print("-" * 50)