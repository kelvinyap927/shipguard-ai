"""
advanced_quality.py

Independent validation and confidence-calibration engine.

Important design principle:

    Extraction != Validation

The extractor proposes values.
This module independently asks:

    "Does the proposed value make sense?"

Checks include:

    - completeness
    - plausibility
    - OCR risk
    - source reliability
    - candidate ambiguity
    - gross/net/tare confusion
    - container/weight relationship
    - duplicate values
    - suspicious document content
    - cross-field consistency
    - confidence calibration
    - human-review routing
"""

import re
from difflib import SequenceMatcher

from modules.schema import FIELDS


# ============================================================================
# CONFIGURATION
# ============================================================================

MIN_WEIGHT_KG = 100
MAX_WEIGHT_KG = 2_000_000

MIN_CONTAINER_COUNT = 1
MAX_CONTAINER_COUNT = 500

HIGH = 0.90
MEDIUM = 0.75
LOW = 0.50

OCR_CAP = 0.70


# ============================================================================
# BASIC HELPERS
# ============================================================================

def compact(value):

    return re.sub(
        r"[^A-Z0-9]",
        "",
        str(value or "").upper(),
    )


def similarity(a, b):

    a = compact(a)
    b = compact(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


# ============================================================================
# PROMPT-INJECTION / UNTRUSTED-DOCUMENT DETECTION
# ============================================================================

SUSPICIOUS_INSTRUCTIONS = (
    "ignore previous instructions",
    "ignore all instructions",
    "system message",
    "developer message",
    "assistant message",
    "chatgpt",
    "prompt injection",
    "do not follow",
    "follow these instructions",
    "override the system",
)


def detect_untrusted_instructions(
    text,
):

    if not text:
        return []

    lowered = text.lower()

    return [
        phrase
        for phrase in SUSPICIOUS_INSTRUCTIONS
        if phrase in lowered
    ]


# ============================================================================
# FIELD VALIDATORS
# ============================================================================

def validate_party(value):

    flags = []

    if value is None:
        return flags

    text = str(value).strip()

    if len(text) < 2:
        flags.append(
            "party_too_short"
        )

    if len(text) > 250:
        flags.append(
            "party_too_long"
        )

    if not re.search(
        r"[A-Za-z]",
        text,
    ):
        flags.append(
            "party_contains_no_letters"
        )

    return flags


def validate_port(value):

    flags = []

    if value is None:
        return flags

    text = str(value).strip()

    if len(text) < 3:
        flags.append(
            "port_too_short"
        )

    if len(text) > 150:
        flags.append(
            "port_too_long"
        )

    if not re.search(
        r"[A-Za-z]",
        text,
    ):
        flags.append(
            "port_contains_no_letters"
        )

    # A field that looks like an entire paragraph
    # is suspicious.
    if len(text.split()) > 15:
        flags.append(
            "possible_wrong_capture"
        )

    return flags


def validate_container_count(
    value,
):

    flags = []

    try:

        number = int(value)

    except (
        ValueError,
        TypeError,
    ):

        flags.append(
            "container_count_not_integer"
        )

        return flags

    if number < MIN_CONTAINER_COUNT:

        flags.append(
            "container_count_too_small"
        )

    if number > MAX_CONTAINER_COUNT:

        flags.append(
            "container_count_implausibly_large"
        )

    return flags


def validate_weight(
    value,
):

    flags = []

    try:

        weight = float(value)

    except (
        ValueError,
        TypeError,
    ):

        flags.append(
            "weight_not_numeric"
        )

        return flags

    if weight < MIN_WEIGHT_KG:

        flags.append(
            "weight_implausibly_small"
        )

    if weight > MAX_WEIGHT_KG:

        flags.append(
            "weight_implausibly_large"
        )

    return flags


# ============================================================================
# GROSS WEIGHT SPECIFIC VALIDATION
# ============================================================================

def validate_gross_weight_evidence(
    evidence,
):

    flags = []

    raw_label = str(
        evidence.get(
            "raw_label"
        )
        or ""
    ).upper()

    raw_value = str(
        evidence.get(
            "raw_value"
        )
        or ""
    ).upper()

    forbidden = (
        "NET WEIGHT",
        "NET WT",
        "NET MASS",
        "TARE WEIGHT",
        "TARE WT",
        "TARE MASS",
    )

    for term in forbidden:

        if term in raw_label:

            flags.append(
                "gross_weight_from_non_gross_label"
            )

        if term in raw_value:

            flags.append(
                "possible_non_gross_capture"
            )

    return flags


# ============================================================================
# FIELD QUALITY
# ============================================================================

def field_quality(
    field,
    value,
    evidence,
    method,
):

    flags = []

    if value is None:

        return {
            "score": 0.0,
            "status": "MISSING",
            "flags": [
                "missing_value"
            ],
        }

    confidence = float(
        evidence.get(
            "confidence",
            0.0,
        )
        or 0.0
    )

    note = evidence.get(
        "note"
    )

    source = evidence.get(
        "source",
        "rule",
    )

    # ------------------------------------------------------------------------
    # Source adjustment
    # ------------------------------------------------------------------------

    if source == "ai_vision":

        confidence = min(
            confidence,
            0.65,
        )

        flags.append(
            "ai_only"
        )

    elif source == "ocr":

        confidence = min(
            confidence,
            OCR_CAP,
        )

        flags.append(
            "ocr_risk"
        )

    elif source == "ocr+ai":

        confidence = max(
            confidence,
            0.95,
        )

        flags.append(
            "independent_reader_agreement"
        )

    # ------------------------------------------------------------------------
    # Structural fallback
    # ------------------------------------------------------------------------

    if note == "derived_from_container_rows":

        confidence = min(
            confidence,
            0.72,
        )

        flags.append(
            "derived_value"
        )

    # ------------------------------------------------------------------------
    # Field-specific validation
    # ------------------------------------------------------------------------

    if field in (
        "shipper",
        "consignee",
        "notify_party",
    ):

        flags.extend(
            validate_party(
                value
            )
        )

    elif field in (
        "port_of_loading",
        "port_of_discharge",
    ):

        flags.extend(
            validate_port(
                value
            )
        )

    elif field == "container_count":

        flags.extend(
            validate_container_count(
                value
            )
        )

    elif field == "gross_weight_kg":

        flags.extend(
            validate_weight(
                value
            )
        )

        flags.extend(
            validate_gross_weight_evidence(
                evidence
            )
        )

    # ------------------------------------------------------------------------
    # Penalties
    # ------------------------------------------------------------------------

    penalties = {

        "party_too_short": 0.15,
        "party_too_long": 0.10,

        "port_too_short": 0.15,
        "port_too_long": 0.10,
        "possible_wrong_capture": 0.20,

        "container_count_not_integer": 0.30,
        "container_count_too_small": 0.20,
        "container_count_implausibly_large": 0.20,

        "weight_not_numeric": 0.40,
        "weight_implausibly_small": 0.15,
        "weight_implausibly_large": 0.20,

        "gross_weight_from_non_gross_label": 0.50,
        "possible_non_gross_capture": 0.40,
    }

    for flag in flags:

        confidence -= penalties.get(
            flag,
            0.0,
        )

    confidence = max(
        0.0,
        min(
            1.0,
            confidence,
        ),
    )

    if confidence >= HIGH:

        status = "HIGH"

    elif confidence >= MEDIUM:

        status = "MEDIUM"

    elif confidence > 0:

        status = "LOW"

    else:

        status = "MISSING"

    return {
        "score": round(
            confidence,
            3,
        ),
        "status": status,
        "flags": sorted(
            set(flags)
        ),
    }


# ============================================================================
# CROSS-FIELD VALIDATION
# ============================================================================

def cross_field_checks(
    fields,
    evidence,
):

    flags = []

    count = fields.get(
        "container_count"
    )

    weight = fields.get(
        "gross_weight_kg"
    )

    # ------------------------------------------------------------------------
    # Container count vs weight
    # ------------------------------------------------------------------------

    if count is not None and weight is not None:

        try:

            count = int(count)
            weight = float(weight)

            average = (
                weight / count
            )

            if average < 50:

                flags.append(
                    "average_container_weight_suspiciously_low"
                )

            if average > 50000:

                flags.append(
                    "average_container_weight_suspiciously_high"
                )

        except (
            ValueError,
            TypeError,
            ZeroDivisionError,
        ):

            pass

    # ------------------------------------------------------------------------
    # Duplicate party values
    # ------------------------------------------------------------------------

    parties = [

        fields.get(
            "shipper"
        ),

        fields.get(
            "consignee"
        ),

        fields.get(
            "notify_party"
        ),
    ]

    present = [
        compact(x)
        for x in parties
        if x
    ]

    if len(present) == 3:

        if (
            similarity(
                present[0],
                present[1],
            ) > 0.96
            and similarity(
                present[1],
                present[2],
            ) > 0.96
        ):

            flags.append(
                "all_party_fields_identical"
            )

    # ------------------------------------------------------------------------
    # Gross weight evidence
    # ------------------------------------------------------------------------

    gross_ev = evidence.get(
        "gross_weight_kg"
    ) or {}

    flags.extend(
        validate_gross_weight_evidence(
            gross_ev
        )
    )

    return flags


# ============================================================================
# CANDIDATE CONFLICTS
# ============================================================================

def detect_candidate_conflicts(
    candidate_data,
):

    conflicts = {}

    for field, data in (
        candidate_data or {}
    ).items():

        candidates = data.get(
            "candidates",
            [],
        )

        if len(candidates) < 2:
            continue

        top = candidates[0]

        second = candidates[1]

        if (
            top.get("score", 0)
            - second.get("score", 0)
            < 0.08
        ):

            conflicts[field] = {
                "type": "near_tie",
                "winner": top,
                "alternative": second,
            }

    return conflicts


# ============================================================================
# MAIN QUALITY ENGINE
# ============================================================================

def evaluate(
    fields,
    evidence,
    method,
    *,
    candidate_data=None,
    raw_text=None,
):

    field_results = {}

    all_flags = []

    # ------------------------------------------------------------------------
    # Field-by-field analysis
    # ------------------------------------------------------------------------

    for field in FIELDS:

        result = field_quality(
            field,
            fields.get(field),
            evidence.get(field) or {},
            method,
        )

        field_results[
            field
        ] = result

        all_flags.extend(
            f"{field}:{flag}"
            for flag in result[
                "flags"
            ]
        )

    # ------------------------------------------------------------------------
    # Cross-field analysis
    # ------------------------------------------------------------------------

    cross_flags = cross_field_checks(
        fields,
        evidence,
    )

    all_flags.extend(
        cross_flags
    )

    # ------------------------------------------------------------------------
    # Document security
    # ------------------------------------------------------------------------

    suspicious = detect_untrusted_instructions(
        raw_text
    )

    for phrase in suspicious:

        all_flags.append(
            "document_contains_suspicious_instruction:"
            + phrase
        )

    # ------------------------------------------------------------------------
    # Candidate conflicts
    # ------------------------------------------------------------------------

    conflicts = detect_candidate_conflicts(
        candidate_data
    )

    for field in conflicts:

        all_flags.append(
            f"{field}:candidate_near_tie"
        )

    # ------------------------------------------------------------------------
    # Completeness
    # ------------------------------------------------------------------------

    missing = sum(
        1
        for field in FIELDS
        if fields.get(field) is None
    )

    completeness = (
        1
        - (
            missing
            / len(FIELDS)
        )
    )

    # ------------------------------------------------------------------------
    # Average field confidence
    # ------------------------------------------------------------------------

    scores = [
        result["score"]
        for result in field_results.values()
        if result["score"] > 0
    ]

    average = (
        sum(scores)
        / len(scores)
        if scores
        else 0.0
    )

    # ------------------------------------------------------------------------
    # Candidate confidence contribution
    # ------------------------------------------------------------------------

    candidate_scores = []

    for field, data in (
        candidate_data or {}
    ).items():

        winner = data.get(
            "winner"
        )

        if winner:

            candidate_scores.append(
                float(
                    winner.get(
                        "score",
                        0,
                    )
                )
            )

    candidate_average = (
        sum(candidate_scores)
        / len(candidate_scores)
        if candidate_scores
        else average
    )

    # ------------------------------------------------------------------------
    # Final score
    # ------------------------------------------------------------------------

    quality_score = (
        average * 0.50
        + candidate_average * 0.20
        + completeness * 0.30
    )

    # ------------------------------------------------------------------------
    # Important flags reduce final score
    # ------------------------------------------------------------------------

    severe_flags = (

        "weight_not_numeric",
        "container_count_not_integer",
        "gross_weight_from_non_gross_label",
        "possible_non_gross_capture",
    )

    if any(
        flag.split(":")[-1]
        in severe_flags
        for flag in all_flags
    ):

        quality_score -= 0.15

    if conflicts:

        quality_score -= 0.08

    if suspicious:

        quality_score -= 0.10

    quality_score = round(
        max(
            0.0,
            min(
                1.0,
                quality_score,
            ),
        ),
        3,
    )

    # ------------------------------------------------------------------------
    # Validation status
    # ------------------------------------------------------------------------

    if missing:

        status = "INCOMPLETE"

    elif suspicious:

        status = "REVIEW"

    elif conflicts:

        status = "REVIEW"

    elif quality_score < 0.70:

        status = "REVIEW"

    elif quality_score < 0.85:

        status = "VERIFY"

    else:

        status = "PASS"

    # ------------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------------

    provenance = {}

    for field in FIELDS:

        ev = evidence.get(
            field
        ) or {}

        provenance[field] = {

            "field": field,

            "source": ev.get(
                "source",
                "rule",
            ),

            "method": method,

            "raw_label": ev.get(
                "raw_label"
            ),

            "raw_value": ev.get(
                "raw_value"
            ),

            "confidence": ev.get(
                "confidence",
                0.0,
            ),

            "note": ev.get(
                "note"
            ),

            "ocr_value": ev.get(
                "ocr_value"
            ),

            "ai_rejected": ev.get(
                "ai_rejected"
            ),
        }

    return {

        "quality_score":
            quality_score,

        "validation_status":
            status,

        "flags":
            sorted(
                set(
                    all_flags
                )
            ),

        "field_quality":
            field_results,

        "provenance":
            provenance,

        "candidate_conflicts":
            conflicts,

        "suspicious_instructions":
            suspicious,

        "completeness":
            round(
                completeness,
                3,
            ),
    }