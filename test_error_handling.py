from modules.pipeline import process_email


bad_email = {
    "email_id": "test_bad_email"
}


result = process_email(bad_email)

print("Email ID:", result["email_id"])
print("Status:", result["status"])
print("Reason:", result["reason"])
print("Errors:", result["errors"])

print("Audit Trail:")

for log in result["audit_log"]:
    print("-", log["step"], ":", log["message"])