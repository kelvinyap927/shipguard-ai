from modules.inbox import load_inbox

inbox = load_inbox()

check_ids = [
    "email_506",
    "email_508",
    "email_509"
]


for email in inbox:
    if email["email_id"] in check_ids:
        print("Email ID:", email["email_id"])
        print("Subject:", email["subject"])
        print("Body:")
        print(email["body"])
        print("Attachments:", email["attachments"])
        print("=" * 70)