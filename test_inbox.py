from loader import Inbox

inbox = Inbox(".")

for email in inbox:
    print("Email ID:", email["email_id"])
    print("Subject:", email["subject"])
    print()

    for attachment in email["attachments"]:
        print("Attachment:", attachment)
        print("-" * 50)

        text = inbox.read_text(attachment)
        print(text)

        print("=" * 50)

    break

from modules.inbox import load_inbox, show_emails

inbox = load_inbox()

show_emails(inbox)