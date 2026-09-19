from modules.inbox import load_inbox
from modules.classifier import classify_email
from modules.attachment_router import route_attachments
from modules.format_router import get_file_type, choose_reader

inbox = load_inbox()

count = 0

for email in inbox:
    category = classify_email(email)

    if category == "document_comparison":
        result = route_attachments(email)

        if result["status"] == "ready":
            si_file = result["si_file"]
            bl_file = result["bl_file"]

            print("Email ID:", email["email_id"])

            print(
                "SI:",
                si_file,
                "| Type:",
                get_file_type(si_file),
                "| Reader:",
                choose_reader(si_file)
            )

            print(
                "BL:",
                bl_file,
                "| Type:",
                get_file_type(bl_file),
                "| Reader:",
                choose_reader(bl_file)
            )

            print("-" * 60)

            count += 1

            if count == 10:
                break