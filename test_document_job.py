from modules.inbox import load_inbox
from modules.classifier import classify_email
from modules.document_job import build_document_job

inbox = load_inbox()

count = 0

for email in inbox:
    category = classify_email(email)

    if category == "document_comparison":
        job = build_document_job(email)

        print(job)
        print("-" * 70)

        count += 1

        if count == 6:
            break