from modules.hybrid_classifier import classify_email_hybrid


# Test 1: clear document comparison
high_email = {
    "email_id": "test_high",
    "from": "docs@example.com",
    "subject": "Confirm docs",
    "body": "Please verify the BL matches the SI and confirm.",
    "attachments": [
        "test_SI.pdf",
        "test_BL.pdf"
    ]
}


# Test 2: unclear email
unclear_email = {
    "email_id": "test_unclear",
    "from": "operations@example.com",
    "subject": "Update",
    "body": "Please advise.",
    "attachments": []
}


print("TEST 1 - HIGH CONFIDENCE RULE")
result1 = classify_email_hybrid(high_email)

for key, value in result1.items():
    print(key, ":", value)


print("\nTEST 2 - UNCERTAIN EMAIL")
result2 = classify_email_hybrid(unclear_email)

for key, value in result2.items():
    print(key, ":", value)