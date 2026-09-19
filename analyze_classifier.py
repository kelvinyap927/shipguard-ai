from modules.inbox import load_inbox
from modules.classifier import classify_email

inbox = load_inbox()

category_counts = {
    "document_comparison": 0,
    "new_si_request": 0,
    "invoice_query": 0,
    "general": 0,
    "spam": 0
}

confidence_counts = {
    "HIGH": 0,
    "MEDIUM": 0,
    "LOW": 0
}

review_emails = []

total = 0

for email in inbox:
    result = classify_email(email)

    category = result["category"]
    confidence = result["confidence"]

    category_counts[category] += 1
    confidence_counts[confidence] += 1

    total += 1

    if confidence != "HIGH":
        review_emails.append({
            "email_id": email["email_id"],
            "subject": email["subject"],
            "category": category,
            "confidence": confidence,
            "scores": result["scores"]
        })


print("TOTAL EMAILS:", total)

print("\nCATEGORY COUNTS")
print(category_counts)

print("\nCONFIDENCE COUNTS")
print(confidence_counts)

print("\nMEDIUM / LOW CONFIDENCE EMAILS")

for email in review_emails:
    print("-" * 70)
    print("Email ID:", email["email_id"])
    print("Subject:", email["subject"])
    print("Category:", email["category"])
    print("Confidence:", email["confidence"])
    print("Scores:", email["scores"])