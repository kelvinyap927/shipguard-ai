"""
modules/extraction_job.py  --  MEMBER B's entry point inside the pipeline.

Position in the flow:

    classifier -> attachment_router -> document_job  ->  [ extraction_job ]  ->  (comparison: Member C)
                                       "ready_for_extraction"                     needs the 7 fields

It takes the document_job built by modules/document_job.py (which already
found the SI file, the BL file and chose a reader name) and returns the
7 fields of each document, plus a review reason when a human must look.

    from modules.extraction_job import run_extraction
    extraction = run_extraction(document_job)

extraction = {
    "status":        "extracted" | "human_review",
    "review_reason": None | "unreadable" | "wrong_doc_type" | "missing_value" | "missing_attachment",
    "review_notes":  ["plain-English explanation for the human reviewer", ...],
    "ocr_used":      True/False   # True => values came from a scan; small typos are NOT real defects
    "si": {...}, "bl": {...},     # see field_extractor.extract_document()
    "audit": [{"step": ..., "message": ...}, ...]   # appended to the pipeline audit log
}

Member C (comparison): compare  extraction["si"]["keys"][field]  with
extraction["bl"]["keys"][field]   -- "keys" are the normalised values
(no punctuation / port codes / thousands separators), so equal keys = same value.
"""
import traceback

from modules.field_extractor import extract_document
from modules.schema import FIELDS

# If several problems exist, the first one in this list is reported.
REASON_PRIORITY = ["missing_attachment", "unreadable", "wrong_doc_type", "missing_value"]

_inbox = None


def _get_inbox():
    """Same Inbox the rest of the project uses (reads from the project folder)."""
    global _inbox
    if _inbox is None:
        from modules.inbox import load_inbox
        _inbox = load_inbox()
    return _inbox


def _failed_doc(path, expected, error):
    """A crash inside extraction becomes a visible, retryable review case - never a silent failure."""
    return {
        "source": path, "expected_type": expected, "detected_type": None,
        "read_method": None, "ocr_confidence": None,
        "status": "error", "review_reason": "unreadable",
        "review_notes": [f"processing error: {type(error).__name__}: {error}"],
        "traceback": traceback.format_exc(),
        "missing_fields": [], "low_confidence_fields": [],
        "fields": {f: None for f in FIELDS}, "keys": {f: None for f in FIELDS}, "evidence": {},
    }


def _audit_line(kind, reader_name, doc):
    """One readable sentence per document for the audit trail."""
    status = doc["status"]
    if status == "ok":
        return f"{kind} read with {reader_name} ({doc['read_method']}): all 7 fields extracted"
    if status == "partial":
        got = len(FIELDS) - len(doc["missing_fields"])
        return f"{kind} read with {reader_name} ({doc['read_method']}): {got}/7 fields, missing {', '.join(doc['missing_fields'])}"
    return f"{kind} could not be used ({status}): {doc['review_notes'][-1] if doc['review_notes'] else 'unknown problem'}"


def run_extraction(document_job: dict, inbox=None) -> dict:
    """document_job must have status 'ready_for_extraction' (both SI and BL present)."""
    inbox = inbox or _get_inbox()
    out = {"status": "extracted", "review_reason": None, "review_notes": [],
           "ocr_used": False, "si": None, "bl": None, "audit": []}
    reasons = []

    for kind in ("SI", "BL"):
        part = document_job[kind.lower()]              # {"path", "type", "reader"} from document_job.py
        path = part["path"]
        try:
            doc = extract_document(inbox.read_bytes(path), path, expected_type=kind)
        except Exception as e:
            error = e
            doc = _failed_doc(path, kind, error)

        out[kind.lower()] = doc
        out["audit"].append({"step": "extraction", "message": _audit_line(kind, part["reader"], doc)})

        if doc["read_method"] == "ocr" and doc["status"] in ("ok", "partial"):
            out["ocr_used"] = True
            out["audit"].append({"step": "extraction",
                                 "message": f"{kind} is a scan: values came from OCR and may contain reading errors"})
        if doc["review_reason"]:
            reasons.append(doc["review_reason"])
            out["review_notes"].append(f"{kind}: " + "; ".join(doc["review_notes"]))

    if reasons:
        out["status"] = "human_review"
        out["review_reason"] = next(r for r in REASON_PRIORITY if r in reasons)
        out["audit"].append({"step": "routing",
                             "message": f"Sent to human review ({out['review_reason']})"})
    else:
        out["audit"].append({"step": "routing", "message": "Extraction complete, ready for comparison"})
    return out