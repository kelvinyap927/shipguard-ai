from modules.classifier import classify_email
from modules.document_job import build_document_job
from modules.extraction_job import run_extraction      # Member B


def process_email(email):

    audit_log = []

    # Step 1: Classify email
    classification = classify_email(email)

    category = classification["category"]
    confidence = classification["confidence"]

    audit_log.append({
        "step": "classification",
        "message": f"Classified as {category} with {confidence} confidence"
    })

    result = {
        "email_id": email["email_id"],
        "category": category,
        "classification_confidence": confidence,
        "classification_scores": classification["scores"],
        "audit_log": audit_log
    }

    # Step 2: Other email categories
    if category != "document_comparison":

        result["status"] = "classified"

        audit_log.append({
            "step": "routing",
            "message": "No SI/BL comparison required"
        })

        return result

    # Step 3: Check documents
    document_job = build_document_job(email)

    result["status"] = document_job["status"]
    result["document_job"] = document_job

    # Step 4: Human review
    if document_job["status"] == "human_review":

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

    # Step 5: SI and BL found
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
    result["status"] = extraction["status"]           # "extracted" or "human_review"

    if extraction["status"] == "human_review":
        result["review_reason"] = extraction["review_reason"]

    return result