"""
modules/json_export.py  --  turn extraction results into CLEAN, stable, documented JSON.

The pipeline's internal result is big (audit log, raw evidence, tracebacks...).
This file makes the small version other people actually want to read or hand over:

    doc_to_clean(doc)                    one document (SI or BL)   -> dict
    email_to_clean(email_id, result)     one email                 -> dict   (SI + BL + status)
    write_json_exports(results, folder)  writes  <folder>/extracted/email_XXX.json
                                                 <folder>/extracted_all.json

One document looks like this:

    {
      "source":         "attachments/email_004_SI.txt",
      "document_type":  "SI",
      "read_method":    "text",                 # text | pdf_text | ocr | docx | xlsx
      "status":         "ok",                   # ok | partial | unreadable | wrong_doc_type
      "review_reason":  null,                   # or unreadable | wrong_doc_type | missing_value
      "fields": {                               # the 7 required fields, readable values
        "shipper": "VITAL SOLUTIONS PTE LTD",
        "consignee": "...", "notify_party": "...",
        "port_of_loading": "NANTONG, CHINA", "port_of_discharge": "KARACHI, PAKISTAN",
        "container_count": 6, "gross_weight_kg": 131058
      },
      "keys":       {...same 7 fields, normalised - equal keys = same value...},
      "confidence": {"shipper": 0.98, ...},     # 0..1 ; 0 = nothing found
      "needs_verification": ["port_of_loading"],   # found, but confidence below 0.75
      "missing_fields": [],                        # nothing usable found
      "details": {                                 # extra information found next to the value
        "shipper":         {"address": "12 MAIN ROAD; SINGAPORE"},
        "port_of_loading": {"port_name": "NANTONG", "country": "CHINA", "locode": "CNNTG"},
        "container_count": {"container_type": "40'HC"}
      },
      "notes": ["plain-English remarks for a human reviewer"]
    }
"""
import json
import os

from modules.schema import FIELDS

# extra evidence keys worth showing (they only exist for some fields)
_DETAIL_KEYS = ("address", "port_name", "country", "locode", "container_type", "ocr_value", "source")


def doc_to_clean(doc: dict) -> dict:
    evidence = doc.get("evidence") or {}
    details = {}
    for f in FIELDS:
        ev = evidence.get(f) or {}
        d = {k: ev[k] for k in _DETAIL_KEYS if ev.get(k) not in (None, "")}
        if d:
            details[f] = d
    return {
        "source": doc.get("source"),
        "document_type": doc.get("detected_type") or doc.get("expected_type"),
        "read_method": doc.get("read_method"),
        "status": doc.get("status"),
        "review_reason": doc.get("review_reason"),
        "fields": {f: (doc.get("fields") or {}).get(f) for f in FIELDS},
        "keys": {f: (doc.get("keys") or {}).get(f) for f in FIELDS},
        "confidence": {f: (evidence.get(f) or {}).get("confidence", 0.0) for f in FIELDS},
        "needs_verification": doc.get("low_confidence_fields", []),
        "missing_fields": doc.get("missing_fields", []),
        "details": details,
        "notes": doc.get("review_notes", []),
    }


def email_to_clean(email_id: str, result: dict):
    """One email -> clean dict, or None if the email never needed document extraction."""
    if result.get("category") != "document_comparison":
        return None
    ext = result.get("extraction") or {}
    return {
        "email_id": email_id,
        "status": result.get("status"),                  # extracted | human_review
        "review_reason": result.get("review_reason"),
        "ocr_used": ext.get("ocr_used", False),
        "si": doc_to_clean(ext["si"]) if ext.get("si") else None,
        "bl": doc_to_clean(ext["bl"]) if ext.get("bl") else None,
        "review_notes": ext.get("review_notes", []),
    }


def write_json_exports(results: dict, out_dir: str = "out") -> int:
    """Write one file per comparison email + one combined file. Returns how many emails were exported."""
    folder = os.path.join(out_dir, "extracted")
    os.makedirs(folder, exist_ok=True)
    everything = {}
    for email_id, result in results.items():
        clean = email_to_clean(email_id, result)
        if clean is None:
            continue
        everything[email_id] = clean
        with open(os.path.join(folder, f"{email_id}.json"), "w", encoding="utf-8") as fh:
            json.dump(clean, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "extracted_all.json"), "w", encoding="utf-8") as fh:
        json.dump(everything, fh, indent=2, ensure_ascii=False)
    return len(everything)