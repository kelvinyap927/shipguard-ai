"""
Advanced JSON exporter for Member B.

Produces:
    - human-readable field values
    - normalized comparison keys
    - confidence
    - validation status
    - provenance
    - review flags
    - document metadata
"""

import json
import os

from modules.schema import FIELDS


_DETAIL_KEYS = (
    "address",
    "port_name",
    "country",
    "locode",
    "container_type",
    "ocr_value",
    "source",
)


def doc_to_clean(doc: dict) -> dict:

    evidence = (
        doc.get("evidence")
        or {}
    )

    details = {}

    for field in FIELDS:

        ev = evidence.get(
            field
        ) or {}

        d = {
            key: ev[key]
            for key in _DETAIL_KEYS
            if ev.get(key)
            not in (None, "")
        }

        if d:
            details[field] = d

    quality = (
        doc.get("quality")
        or {}
    )

    return {

        "source": doc.get(
            "source"
        ),

        "document_type": (
            doc.get("detected_type")
            or doc.get(
                "expected_type"
            )
        ),

        "read_method": doc.get(
            "read_method"
        ),

        "status": doc.get(
            "status"
        ),

        "review_reason": doc.get(
            "review_reason"
        ),

        # -----------------------------------------------------------
        # Required seven fields
        # -----------------------------------------------------------

        "fields": {
            field:
            (
                doc.get("fields")
                or {}
            ).get(field)
            for field in FIELDS
        },

        # Normalized values used by Member C.
        "keys": {
            field:
            (
                doc.get("keys")
                or {}
            ).get(field)
            for field in FIELDS
        },

        # -----------------------------------------------------------
        # Confidence
        # -----------------------------------------------------------

        "confidence": {
            field:
            (
                evidence.get(field)
                or {}
            ).get(
                "confidence",
                0.0,
            )
            for field in FIELDS
        },

        # -----------------------------------------------------------
        # Advanced quality
        # -----------------------------------------------------------

        "quality_score": quality.get(
            "quality_score",
            0.0,
        ),

        "validation_status": quality.get(
            "validation_status",
            "UNKNOWN",
        ),

        "validation_flags": quality.get(
            "flags",
            [],
        ),

        "field_quality": quality.get(
            "field_quality",
            {},
        ),

        "provenance": quality.get(
            "provenance",
            {},
        ),

        "conflicts": quality.get(
            "conflicts",
            {},
        ),

        "candidate_analysis": doc.get(
            "candidate_analysis",
            {}
        ),

        "completeness": quality.get(
            "completeness",
            0.0,
        ),

        "candidate_conflicts": quality.get(
            "candidate_conflicts",
            {}
        ),

        "suspicious_instructions": quality.get(
            "suspicious_instructions",
            []
        ),

        # -----------------------------------------------------------
        # Review information
        # -----------------------------------------------------------

        "needs_verification": doc.get(
            "low_confidence_fields",
            [],
        ),

        "missing_fields": doc.get(
            "missing_fields",
            [],
        ),

        "details": details,

        "notes": doc.get(
            "review_notes",
            [],
        ),

        # -----------------------------------------------------------
        # Structural intelligence
        # -----------------------------------------------------------

        "port_candidates": doc.get(
            "port_candidates",
            [],
        ),

        "container_types": doc.get(
            "container_types",
            [],
        ),

        "container_rows_detected": doc.get(
            "container_rows_detected",
            0,
        ),

        "derived_weight_kg": doc.get(
            "derived_weight_kg"
        ),
    }


def email_to_clean(
    email_id: str,
    result: dict,
):

    if result.get(
        "category"
    ) != "document_comparison":

        return None

    extraction = (
        result.get(
            "extraction"
        )
        or {}
    )

    return {

        "email_id": email_id,

        "status": result.get(
            "status"
        ),

        "review_reason": result.get(
            "review_reason"
        ),

        "ocr_used": extraction.get(
            "ocr_used",
            False,
        ),

        "si": (
            doc_to_clean(
                extraction["si"]
            )
            if extraction.get("si")
            else None
        ),

        "bl": (
            doc_to_clean(
                extraction["bl"]
            )
            if extraction.get("bl")
            else None
        ),

        "review_notes": extraction.get(
            "review_notes",
            [],
        ),
    }


def write_json_exports(
    results: dict,
    out_dir: str = "out",
) -> int:

    folder = os.path.join(
        out_dir,
        "extracted",
    )

    os.makedirs(
        folder,
        exist_ok=True,
    )

    everything = {}

    for email_id, result in results.items():

        clean = email_to_clean(
            email_id,
            result,
        )

        if clean is None:
            continue

        everything[
            email_id
        ] = clean

        with open(
            os.path.join(
                folder,
                f"{email_id}.json",
            ),
            "w",
            encoding="utf-8",
        ) as fh:

            json.dump(
                clean,
                fh,
                indent=2,
                ensure_ascii=False,
            )

    with open(
        os.path.join(
            out_dir,
            "extracted_all.json",
        ),
        "w",
        encoding="utf-8",
    ) as fh:

        json.dump(
            everything,
            fh,
            indent=2,
            ensure_ascii=False,
        )

    return len(everything)