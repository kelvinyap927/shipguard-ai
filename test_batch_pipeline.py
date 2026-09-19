from modules.inbox import load_inbox
from modules.pipeline import process_email


inbox = load_inbox()

results = []

status_counts = {
    "classified": 0,
    "ready_for_extraction": 0,
    "extracted": 0,
    "human_review": 0,
    "failed": 0
}

for email in inbox:
    result = process_email(email)

    results.append(result)

    status = result["status"]

    if status in status_counts:
        status_counts[status] += 1


print("TOTAL EMAILS:", len(results))

print("\nSTATUS COUNTS")

for status, count in status_counts.items():
    print(status, ":", count)


print("\nFAILED EMAILS")

for result in results:
    if result["status"] == "failed":
        print("Email ID:", result["email_id"])
        print("Errors:", result["errors"])
        print("-" * 50)