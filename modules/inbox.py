from loader import Inbox


def load_inbox():
    inbox = Inbox(".")
    return inbox


def show_emails(inbox):
    for email in inbox:
        print("Email ID:", email["email_id"])
        print("From:", email["from"])
        print("Subject:", email["subject"])
        print("Attachments:", email["attachments"])
        print("-" * 50)