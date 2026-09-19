def clean_body(body):
    # Remove quoted email history
    if "______________________________" in body:
        body = body.split("______________________________")[0]

    return body.lower()


def classify_email(email):
    subject = email["subject"].lower()
    body = clean_body(email["body"])
    attachments = " ".join(email["attachments"]).lower()

    scores = {
        "document_comparison": 0,
        "new_si_request": 0,
        "invoice_query": 0,
        "spam": 0
    }

    # -------------------------
    # Document Comparison
    # -------------------------

    if "confirm docs" in subject:
        scores["document_comparison"] += 6

    if "check the details" in body:
        scores["document_comparison"] += 5

    if "verify the bl matches the si" in body:
        scores["document_comparison"] += 6

    if "draft bl" in body and "for checking" in body:
        scores["document_comparison"] += 4

    if (
        "compare" in body
        and "si" in body
        and "draft bl" in body
    ):
        scores["document_comparison"] += 6

    if "_si." in attachments and "_bl." in attachments:
        scores["document_comparison"] += 3

    # -------------------------
    # New SI Request
    # -------------------------

    if "request si" in subject:
        scores["new_si_request"] += 7

    if "si needed" in subject:
        scores["new_si_request"] += 7

    if "please find shipping instruction" in body:
        scores["new_si_request"] += 5

    if "please revert with draft bl once available" in body:
        scores["new_si_request"] += 3    

    # -------------------------
    # Invoice Query
    # -------------------------
    if "local charges fob" in subject:
        scores["invoice_query"] += 7

    if "invoice" in subject:
        scores["invoice_query"] += 7

    if "billing" in subject:
        scores["invoice_query"] += 6

    if "total freight" in subject:
        scores["invoice_query"] += 6

    if "query on invoice" in body:
        scores["invoice_query"] += 6

    if "cancel invoice" in body:
        scores["invoice_query"] += 6

    if "invoice payment" in body:
        scores["invoice_query"] += 5

    if "local charge" in body:
        scores["invoice_query"] += 4

    if "billed separately" in body:
        scores["invoice_query"] += 4

    # -------------------------
    # Spam
    # -------------------------

    spam_subjects = [
        "increase your shipping revenue",
        "dear valued customer, update your account",
        "undelivered messages",
        "hot singles",
        "bitcoin investment",
        "gift card"
    ]

    for phrase in spam_subjects:
        if phrase in subject:
            scores["spam"] += 7


    spam_words = [
        "bitcoin",
        "gift card",
        "90% off",
        "guaranteed 300%",
        "claim now",
        "verify account immediately"
    ]

    for word in spam_words:
        if word in subject:
            scores["spam"] += 6
        elif word in body:
            scores["spam"] += 4

    # -------------------------
    # Choose best category
    # -------------------------

    best_category = max(scores, key=scores.get)

    sorted_scores = sorted(scores.values(), reverse=True)

    best_score = sorted_scores[0]
    second_score = sorted_scores[1]

    # No clear signal
    if best_score == 0:
        return {
            "category": "general",
            "confidence": "LOW",
            "scores": scores
        }

    difference = best_score - second_score

    # Confidence
    if best_score >= 5 and difference >= 3:
        confidence = "HIGH"

    elif best_score >= 3 and difference >= 1:
        confidence = "MEDIUM"

    else:
        confidence = "LOW"

    return {
        "category": best_category,
        "confidence": confidence,
        "scores": scores
    }