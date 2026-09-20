from modules.document_job import build_document_job
from modules.hybrid_classifier import classify_email_hybrid
from modules.extraction_job import run_extraction
from modules.verification_adapter import build_verification_payload
from member_c_verifier import verify


def process_email(email):

    audit_log = []
    errors = []

    result = {
        "email_id": email.get("email_id"),
        "category": None,
        "classification_confidence": None,
        "classification_scores": {},
        "classification_source": None,
        "classification_reason": None,
        "status": "processing",
        "reason": None,
        "review_reason": None,
        "document_job": None,
        "audit_log": audit_log,
        "errors": errors
    }

    try:
        # Step 1: Classify email
        classification = classify_email_hybrid(email)

        category = classification["category"]
        confidence = classification["confidence"]
        classification_status = classification.get("status", "ok")
        classification_source = classification.get("source", "rule")
        classification_reason = classification.get("reason")

        result["category"] = category
        result["classification_confidence"] = confidence
        result["classification_scores"] = classification.get("scores", {})
        result["classification_source"] = classification_source
        result["classification_reason"] = classification_reason

        audit_log.append({
            "step": "classification",
            "message": (
                f"Classified as {category} with {confidence} confidence "
                f"using {classification_source}"
            )
        })

        if classification_status == "needs_review":
            result["status"] = "human_review"
            result["reason"] = classification_reason

            audit_log.append({
                "step": "classification_review",
                "message": "Classification requires human review"
            })

            return result

        # Step 2: Other email categories
        if category != "document_comparison":

            result["status"] = "classified"

            audit_log.append({
                "step": "routing",
                "message": "No SI/BL comparison required"
            })

            return result

        # Step 3: Build document job
        document_job = build_document_job(email)

        result["document_job"] = document_job
        result["status"] = document_job["status"]

        # Step 4: Human review
        if document_job["status"] == "human_review":

            result["reason"] = document_job["reason"]
            result["review_reason"] = document_job.get("review_reason")

            audit_log.append({
                "step": "attachment_check",
                "message": document_job["reason"]
            })

            audit_log.append({
                "step": "routing",
                "message": "Sent to human review"
            })

            return result

        # Step 5: Documents ready
        audit_log.append({
            "step": "attachment_check",
            "message": "SI and BL attachments found"
        })

        si_type = document_job["si"]["type"]
        bl_type = document_job["bl"]["type"]

        audit_log.append({
            "step": "format_detection",
            "message": f"SI={si_type}, BL={bl_type}"
        })

        audit_log.append({
            "step": "routing",
            "message": "Ready for extraction"
        })

        # Step 6: Extract the 7 fields from the SI and the BL  (Member B)
        extraction = run_extraction(document_job)

        audit_log.extend(extraction.pop("audit"))

        result["extraction"] = extraction

        # Step 7: Verify extracted SI and BL fields
        verification_payload = build_verification_payload(extraction)

        verification = verify(
            verification_payload,
            email_id=email.get("email_id"),
            category="BL_COMPARISON"
        )

        result["verification"] = verification

        audit_log.append({
            "step": "verification",
            "message": verification.get("message", "Verification completed")
        })

        if verification["status"] == "NEEDS_REVIEW":
            result["status"] = "human_review"
            result["review_reason"] = verification.get("review_reason")
            result["reason"] = verification.get("message")

        elif verification["status"] == "MISMATCH":
            result["status"] = "mismatch"
            result["reason"] = verification.get("message")

        else:
            result["status"] = "verified"
            result["reason"] = verification.get("message")

        return result

    except Exception as error:

        result["status"] = "failed"
        result["reason"] = "Pipeline processing failed"

        errors.append(str(error))

        audit_log.append({
            "step": "error",
            "message": str(error)
        })

        return result