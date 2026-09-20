from member_c_verifier import to_submission_record


CATEGORY_MAP = {
    "document_comparison": "BL_COMPARISON",
    "new_si_request": "SI_REQUEST",
    "invoice_query": "INVOICE_QUERY",
    "general": "GENERAL",
    "spam": "SPAM",
}


def build_submission_record(result):

    verification = result.get("verification")

    if verification is not None:
        return to_submission_record(verification)

    category = CATEGORY_MAP.get(
        result.get("category"),
        "GENERAL"
    )

    if result.get("status") == "human_review":
        return {
            "category": category,
            "status": "NEEDS_REVIEW",
            "review_reason": result.get("review_reason") or "unreadable",
            "defect_fields": [],
            "has_defect": False,
        }

    if result.get("status") == "failed":
        return {
            "category": category,
            "status": "NEEDS_REVIEW",
            "review_reason": "unreadable",
            "defect_fields": [],
            "has_defect": False,
        }

    return {
        "category": category,
        "status": "OK",
        "review_reason": None,
        "defect_fields": [],
        "has_defect": False,
    }


def build_submission(results):

    submission = {}

    for result in results:
        email_id = result["email_id"]
        submission[email_id] = build_submission_record(result)

    return submission
