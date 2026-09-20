from modules.json_export import email_to_clean


def aggregate_result(email, pipeline_result, verification=None):

    email_id = email.get("email_id")

    result = {
        "email_id": email_id,
        "category": pipeline_result.get("category"),
        "status": pipeline_result.get("status"),
        "reason": pipeline_result.get("reason"),
        "review_reason": pipeline_result.get("review_reason"),

        "classification": {
            "confidence": pipeline_result.get("classification_confidence"),
            "scores": pipeline_result.get("classification_scores", {}),
            "source": pipeline_result.get("classification_source"),
            "reason": pipeline_result.get("classification_reason"),
        },

        "documents": None,
        "verification": (
            verification
            if verification is not None
            else pipeline_result.get("verification")
        ),

        "audit_log": pipeline_result.get("audit_log", []),
        "errors": pipeline_result.get("errors", []),
    }

    clean_documents = email_to_clean(email_id, pipeline_result)

    if clean_documents is not None:
        result["documents"] = clean_documents

    return result
