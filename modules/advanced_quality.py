"""
advanced_quality.py
-------------------

Advanced validation and confidence engine for Member B.

This module does NOT extract values itself.
Instead, it independently evaluates the values produced by the
rule-based / OCR / AI extraction layer.

It provides:

    - field plausibility checks
    - OCR-risk detection
    - duplicate/conflicting candidate detection
    - shipping-domain sanity checks
    - cross-field consistency checks
    - confidence adjustments
    - machine-readable validation flags
    - provenance information

The goal is to avoid blindly trusting the first value a parser finds.

Pipeline:

    raw document
        ↓
    field_extractor
        ↓
    advanced_quality
        ↓
    final structured result
"""

import re
from difflib import SequenceMatcher

from modules.schema import FIELDS


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_WEIGHT_KG = 100
MAX_WEIGHT_KG = 2_000_000

MIN_CONTAINER_COUNT = 1
MAX_CONTAINER_COUNT = 500

CONFIDENCE_CAP_OCR = 0.70
CONFIDENCE_HIGH = 0.90
CONFIDENCE_MEDIUM = 0.75
CONFIDENCE_LOW = 0.50


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _normalise_text(value):
    if value is None:
        return ""

    return re.sub(
        r"[^A-Z0-9]+",
        " ",
        str(value).upper()
    ).strip()


def _compact(value):
    return re.sub(
        r"[^A-Z0-9]",
        "",
        str(value or "").upper()
    )


def _similarity(a, b):
    a = _compact(a)
    b = _compact(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio()


def _is_company_like(value):
    if not value:
        return False

    text = str(value).upper()

    company_tokens = (
        "LTD",
        "LIMITED",
        "PTE",
        "PTY",
        "INC",
        "CORP",
        "CORPORATION",
        "LLC",
        "SDN",
        "BHD",
        "CO.",
        "COMPANY",
        "GMBH",
        "PLC",
        "SA",
    )

    return any(token in text for token in company_tokens)


def _contains_instruction(value):
    """
    Detect suspicious prompt-injection-like text inside documents.

    Shipping documents are treated as untrusted data.
    """

    if not value:
        return False

    text = str(value).lower()

    suspicious = (
        "ignore previous instructions",
        "ignore all instructions",
        "system message",
        "assistant",
        "developer message",
        "chatgpt",
        "prompt injection",
        "do not follow",
        "follow these instructions",
    )

    return any(x in text for x in suspicious)


# ---------------------------------------------------------------------------
# Field-level validation
# ---------------------------------------------------------------------------

def validate_shipper(value):
    flags = []

    if not value:
        return flags

    if len(str(value)) < 2:
        flags.append("party_value_too_short")

    if len(str(value)) > 180:
        flags.append("party_value_too_long")

    if _contains_instruction(value):
        flags.append("suspicious_document_instruction")

    return flags


def validate_consignee(value):
    flags = []

    if not value:
        return flags

    if len(str(value)) < 2:
        flags.append("party_value_too_short")

    if len(str(value)) > 180:
        flags.append("party_value_too_long")

    if _contains_instruction(value):
        flags.append("suspicious_document_instruction")

    return flags


def validate_notify_party(value):
    flags = []

    if not value:
        return flags

    if len(str(value)) < 2:
        flags.append("party_value_too_short")

    if len(str(value)) > 180:
        flags.append("party_value_too_long")

    if _contains_instruction(value):
        flags.append("suspicious_document_instruction")

    return flags


def validate_port(value):
    flags = []

    if not value:
        return flags

    text = str(value).upper()

    if len(text) < 3:
        flags.append("port_value_too_short")

    if len(text) > 120:
        flags.append("port_value_too_long")

    # A port should normally contain alphabetic characters.
    if not re.search(r"[A-Z]", text):
        flags.append("port_contains_no_letters")

    # Strong indication that the parser captured a full sentence.
    if len(text.split()) > 15:
        flags.append("possible_wrong_capture")

    if _contains_instruction(value):
        flags.append("suspicious_document_instruction")

    return flags


def validate_container_count(value):
    flags = []

    if value is None:
        return flags

    try:
        n = int(value)
    except (ValueError, TypeError):
        flags.append("container_count_not_integer")
        return flags

    if n < MIN_CONTAINER_COUNT:
        flags.append("container_count_too_small")

    if n > MAX_CONTAINER_COUNT:
        flags.append("container_count_implausibly_large")

    return flags


def validate_weight(value):
    flags = []

    if value is None:
        return flags

    try:
        weight = float(value)
    except (ValueError, TypeError):
        flags.append("weight_not_numeric")
        return flags

    if weight < MIN_WEIGHT_KG:
        flags.append("weight_implausibly_small")

    if weight > MAX_WEIGHT_KG:
        flags.append("weight_implausibly_large")

    return flags


# ---------------------------------------------------------------------------
# Cross-field validation
# ---------------------------------------------------------------------------

def cross_field_validation(fields, evidence):
    """
    Look for relationships between fields.

    Returns a list of machine-readable validation flags.
    """

    flags = []

    container_count = fields.get("container_count")
    gross_weight = fields.get("gross_weight_kg")

    # ------------------------------------------------------------------
    # Weight/container sanity
    # ------------------------------------------------------------------

    if container_count and gross_weight:

        try:
            avg_weight = float(gross_weight) / int(container_count)

            # Extremely low average shipment weight.
            if avg_weight < 50:
                flags.append("weight_container_ratio_too_low")

            # Extremely high average weight.
            if avg_weight > 50_000:
                flags.append("weight_container_ratio_too_high")

        except (ValueError, TypeError, ZeroDivisionError):
            pass

    # ------------------------------------------------------------------
    # Gross-weight evidence must not be net-weight evidence
    # ------------------------------------------------------------------

    gross_ev = evidence.get("gross_weight_kg") or {}

    raw_label = str(gross_ev.get("raw_label") or "").upper()
    raw_value = str(gross_ev.get("raw_value") or "").upper()

    if "NET WEIGHT" in raw_label:
        flags.append("gross_weight_from_net_weight_label")

    if "NET WEIGHT" in raw_value and "GROSS" not in raw_value:
        flags.append("possible_net_weight_capture")

    # ------------------------------------------------------------------
    # OCR confidence
    # ------------------------------------------------------------------

    for field in FIELDS:
        ev = evidence.get(field) or {}

        if ev.get("source") == "ocr":
            confidence = ev.get("confidence", 0)

            if confidence > CONFIDENCE_CAP_OCR:
                flags.append(
                    f"{field}:ocr_confidence_capped"
                )

    return flags


# ---------------------------------------------------------------------------
# Duplicate / conflict detection
# ---------------------------------------------------------------------------

def detect_conflicts(evidence):
    """
    Detect situations where multiple pieces of evidence appear to exist
    for a field.

    The current extractor generally chooses the first recognised field.
    This function makes that decision visible to the reviewer.
    """

    conflicts = {}

    for field in FIELDS:

        ev = evidence.get(field) or {}

        raw_value = ev.get("raw_value")

        if not raw_value:
            continue

        # Values separated by "|" represent multi-line evidence.
        pieces = [
            x.strip()
            for x in str(raw_value).split("|")
            if x.strip()
        ]

        if len(pieces) <= 1:
            continue

        unique = []

        for value in pieces:
            if not any(
                _similarity(value, existing) >= 0.92
                for existing in unique
            ):
                unique.append(value)

        if len(unique) > 1:
            conflicts[field] = unique

    return conflicts


# ---------------------------------------------------------------------------
# Evidence quality
# ---------------------------------------------------------------------------

def evidence_quality(field, value, evidence, method):
    """
    Calculate an independent quality score.

    This score is deliberately separate from the parser's confidence.
    """

    if value is None:
        return 0.0, ["missing_value"]

    ev = evidence.get(field) or {}

    score = float(ev.get("confidence", 0.0))
    flags = []

    note = ev.get("note")

    if note == "filled_by_ai":
        score = min(score, 0.65)
        flags.append("ai_only")

    if note == "ai_differs_from_ocr":
        score = min(score, 0.65)
        flags.append("ocr_ai_disagreement")

    if note == "ocr_and_ai_agree":
        score = max(score, 0.95)

    if note == "derived_from_container_rows":
        score = min(score, 0.50)
        flags.append("derived_value")

    if method == "ocr":
        score = min(score, CONFIDENCE_CAP_OCR)

        if "ocr" not in flags:
            flags.append("ocr_risk")

    # ---------------------------------------------------------------
    # Field-specific validation
    # ---------------------------------------------------------------

    if field == "shipper":
        flags.extend(validate_shipper(value))

    elif field == "consignee":
        flags.extend(validate_consignee(value))

    elif field == "notify_party":
        flags.extend(validate_notify_party(value))

    elif field in ("port_of_loading", "port_of_discharge"):
        flags.extend(validate_port(value))

    elif field == "container_count":
        flags.extend(validate_container_count(value))

    elif field == "gross_weight_kg":
        flags.extend(validate_weight(value))

    # ---------------------------------------------------------------
    # Penalise suspicious results
    # ---------------------------------------------------------------

    penalty_flags = {
        "party_value_too_short",
        "party_value_too_long",
        "port_value_too_short",
        "port_value_too_long",
        "possible_wrong_capture",
        "container_count_not_integer",
        "container_count_too_small",
        "container_count_implausibly_large",
        "weight_not_numeric",
        "weight_implausibly_small",
        "weight_implausibly_large",
        "possible_net_weight_capture",
        "suspicious_document_instruction",
    }

    for flag in flags:
        if flag in penalty_flags:
            score -= 0.15

    score = max(0.0, min(1.0, score))

    return round(score, 3), sorted(set(flags))


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

def build_provenance(field, evidence, method):
    """
    Produce a compact explanation of where the final value came from.
    """

    ev = evidence.get(field) or {}

    return {
        "field": field,
        "method": method,
        "source": ev.get("source", "rule"),
        "raw_label": ev.get("raw_label"),
        "raw_value": ev.get("raw_value"),
        "confidence": ev.get("confidence", 0.0),
        "note": ev.get("note"),
        "ocr_value": ev.get("ocr_value"),
        "ai_rejected": ev.get("ai_rejected"),
    }


# ---------------------------------------------------------------------------
# Main quality engine
# ---------------------------------------------------------------------------

def evaluate(fields, evidence, method):
    """
    Main entry point.

    Returns:

        {
            "quality_score": 0.97,
            "validation_status": "PASS",
            "flags": [],
            "field_quality": {...},
            "provenance": {...},
            "conflicts": {...}
        }
    """

    field_quality = {}
    provenance = {}
    all_flags = []

    for field in FIELDS:

        value = fields.get(field)

        score, flags = evidence_quality(
            field,
            value,
            evidence,
            method
        )

        field_quality[field] = {
            "score": score,
            "status": (
                "HIGH"
                if score >= CONFIDENCE_HIGH
                else
                "MEDIUM"
                if score >= CONFIDENCE_MEDIUM
                else
                "LOW"
                if score > 0
                else
                "MISSING"
            ),
            "flags": flags,
        }

        provenance[field] = build_provenance(
            field,
            evidence,
            method
        )

        all_flags.extend(
            f"{field}:{flag}"
            for flag in flags
        )

    # Cross-field validation.
    cross_flags = cross_field_validation(
        fields,
        evidence
    )

    all_flags.extend(cross_flags)

    # Duplicate/conflicting evidence.
    conflicts = detect_conflicts(evidence)

    for field in conflicts:
        all_flags.append(
            f"{field}:multiple_candidates"
        )

    # ------------------------------------------------------------------
    # Overall score
    # ------------------------------------------------------------------

    scores = [
        x["score"]
        for x in field_quality.values()
        if x["score"] > 0
    ]

    if scores:
        average_score = sum(scores) / len(scores)
    else:
        average_score = 0.0

    # Missing fields significantly reduce overall quality.
    missing = sum(
        1
        for field in FIELDS
        if fields.get(field) is None
    )

    completeness = 1 - (
        missing / len(FIELDS)
    )

    quality_score = (
        average_score * 0.70
        + completeness * 0.30
    )

    quality_score = round(
        max(0.0, min(1.0, quality_score)),
        3
    )

    # ------------------------------------------------------------------
    # Final status
    # ------------------------------------------------------------------

    if missing:
        validation_status = "INCOMPLETE"

    elif any(
        "suspicious_document_instruction" in flag
        for flag in all_flags
    ):
        validation_status = "REVIEW"

    elif any(
        "multiple_candidates" in flag
        for flag in all_flags
    ):
        validation_status = "REVIEW"

    elif quality_score < 0.75:
        validation_status = "REVIEW"

    elif quality_score < 0.90:
        validation_status = "VERIFY"

    else:
        validation_status = "PASS"

    return {
        "quality_score": quality_score,
        "validation_status": validation_status,
        "flags": sorted(set(all_flags)),
        "field_quality": field_quality,
        "provenance": provenance,
        "conflicts": conflicts,
    }