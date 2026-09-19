"""
Uses the existing rule-based classifier first.
Only uses Claude AI when the rule classifier is uncertain.
"""

from modules.classifier import classify_email
from modules.ai_classifier import classify_with_ai


def detect_si_bl(email):
    """
    Check whether the email has SI / BL attachments.
    """

    attachments = email.get("attachments", [])

    has_si = False
    has_bl = False

    for attachment in attachments:
        filename = attachment.lower()

        if "_si." in filename:
            has_si = True

        if "_bl." in filename:
            has_bl = True

    return has_si, has_bl


def classify_email_hybrid(email):
    """
    Hybrid classification:

    1. Run rule-based classifier.
    2. If HIGH confidence, accept rule result.
    3. If MEDIUM or LOW, ask Claude AI.
    4. If AI fails, return a safe review result.
    """

    # Step 1: Rule-based classification
    rule_result = classify_email(email)

    # Step 2: High confidence → trust rules
    if rule_result["confidence"] == "HIGH":

        return {
            "category": rule_result["category"],
            "confidence": rule_result["confidence"],
            "scores": rule_result["scores"],
            "source": "rule",
            "reason": "High-confidence rule-based classification.",
            "status": "ok"
        }

    # Step 3: Detect SI / BL attachments
    has_si, has_bl = detect_si_bl(email)

    # Step 4: Ask Claude for uncertain cases
    ai_result = classify_with_ai(
        email,
        has_si=has_si,
        has_bl=has_bl
    )

    # Step 5: Claude failed
    if ai_result["status"] == "failed":

        return {
            "category": None,
            "confidence": "LOW",
            "scores": rule_result["scores"],
            "source": "human_review",
            "reason": ai_result["reason"],
            "status": "needs_review"
        }

    # Step 6: Claude answered, but is still uncertain
    if ai_result["confidence"] != "HIGH":

        return {
            "category": ai_result["category"],
            "confidence": ai_result["confidence"],
            "scores": rule_result["scores"],
            "source": "ai",
            "reason": ai_result["reason"],
            "status": "needs_review"
        }

    # Step 7: Claude is confident
    return {
        "category": ai_result["category"],
        "confidence": ai_result["confidence"],
        "confidence_score": ai_result["confidence_score"],
        "scores": rule_result["scores"],
        "source": "ai",
        "reason": ai_result["reason"],
        "status": "ok"
    }