from modules.inbox import load_inbox
from modules.classifier import classify_email

inbox = load_inbox()

for i, email in enumerate(inbox):
    result = classify_email(email)

    print("Email ID:", email["email_id"])
    print("Subject:", email["subject"])
    print("Category:", result["category"])
    print("Confidence:", result["confidence"])
    print("Scores:", result["scores"])
    print("-" * 50)

    if i == 9:
        break