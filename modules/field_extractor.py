"""
modules/field_extractor.py

Advanced multi-stage shipping-document extraction engine.

Pipeline:

    document
       ↓
    label detection
       ↓
    fuzzy matching
       ↓
    field block collection
       ↓
    normalization
       ↓
    structural fallbacks
       ↓
    optional AI
       ↓
    domain validation
       ↓
    quality scoring
       ↓
    final extraction result

The public API is intentionally compatible with the original project.
"""

import re
import textwrap
from difflib import SequenceMatcher, get_close_matches

from modules.normalizer import (
    clean,
    normalize_value,
    parse_weight_kg,
)

from modules.ai_extractor import (
    ai_enabled,
    enhance,
)

from modules.document_reader import (
    read_document,
)

from modules.schema import (
    FIELDS,
    IGNORE,
    LABEL_ALIASES,
    PARTY_FIELDS,
    PORT_FIELDS,
    TITLE_RULES,
)

from modules.advanced_quality import evaluate


# ---------------------------------------------------------------------------
# Confidence configuration
# ---------------------------------------------------------------------------

REVIEW_CONFIDENCE = 0.75
OCR_MAX_CONFIDENCE = 0.70

_CJK = re.compile(
    r"[\u3000-\u303f\u3400-\u9fff\uff00-\uffef]"
)


# ---------------------------------------------------------------------------
# Label normalisation
# ---------------------------------------------------------------------------

def _compact(label: str) -> str:
    """
    Convert a label into a comparison-safe representation.

    Examples:

        Gross Weight毛重(KGS)
            ->
        grossweight

        Port of Loading
            ->
        portofloading
    """

    if not label:
        return ""

    s = _CJK.sub("", str(label))

    # Remove bracketed content.
    s = re.sub(
        r"\([^)]*\)",
        "",
        s
    )

    return re.sub(
        r"[^a-z0-9]",
        "",
        s.lower()
    )


# ---------------------------------------------------------------------------
# Build alias index
# ---------------------------------------------------------------------------

ALIAS_TO_FIELD = {}

for _field, _aliases in LABEL_ALIASES.items():

    for _alias in _aliases:

        compact = _compact(_alias)

        if compact:
            ALIAS_TO_FIELD[compact] = _field


# ---------------------------------------------------------------------------
# Advanced label matching
# ---------------------------------------------------------------------------
# Words that flip the MEANING of a port label. A typo-tolerant match must never turn
# "Port of Unloading" into "Port of Loading" (they differ by only two letters).
_LOAD_WORDS = ("load", "receipt", "origin", "depart")
_DISCHARGE_WORDS = ("unload", "discharg", "destin", "deliver")


def _meaning_flips(key: str, field: str) -> bool:
    if field == "port_of_loading":
        return any(w in key for w in _DISCHARGE_WORDS)
    if field == "port_of_discharge":
        return any(w in key for w in _LOAD_WORDS) and "unload" not in key
    return False


def lookup_label(text: str, cutoff=None):
    """
    Resolve a document label to one of the seven required fields.
    Returns (field, similarity): 1.0 for an exact label, 0..1 for a typo'd one.
    cutoff=None -> exact matches only;  cutoff=0.88 -> also accept near-exact labels.
    """
    key = _compact(text)
    if not key:
        return None
    if key in ALIAS_TO_FIELD:
        return ALIAS_TO_FIELD[key], 1.0
    if cutoff and len(key) > 4:
        hit = get_close_matches(key, ALIAS_TO_FIELD.keys(), n=1, cutoff=cutoff)
        if hit and not _meaning_flips(key, ALIAS_TO_FIELD[hit[0]]):
            return ALIAS_TO_FIELD[hit[0]], round(SequenceMatcher(None, key, hit[0]).ratio(), 3)
    return None

# ---------------------------------------------------------------------------
# Label line parser
# ---------------------------------------------------------------------------

def parse_label_line(
    line: str,
    ocr: bool = False,
):
    """
    Recognise three major document layouts.

    1. Label: Value

    2. Label        Value

    3. Label Value

    OCR uses a lower fuzzy threshold.
    """

    if not line:
        return None

    cutoff = (
        0.75
        if ocr
        else
        0.88
    )

    s = line.strip()

    # ---------------------------------------------------------------
    # STYLE 1
    #
    # Gross Weight: 22,000 KG
    # ---------------------------------------------------------------

    if ":" in s:

        label, _, rest = s.partition(":")

        if len(label) <= 80:

            hit = lookup_label(
                label,
                cutoff,
            )

            if hit:

                return (
                    hit[0],
                    label.strip(),
                    rest.strip(),
                    hit[1],
                )

    # ---------------------------------------------------------------
    # STYLE 2
    #
    # Gross Weight          22,000 KG
    # ---------------------------------------------------------------

    parts = re.split(
        r"\s{2,}",
        s,
        maxsplit=1,
    )

    if len(parts) == 2:

        label = parts[0]
        rest = parts[1]

        hit = lookup_label(
            label,
            cutoff,
        )

        if hit:

            return (
                hit[0],
                label.strip(),
                rest.strip(),
                hit[1],
            )

    # ---------------------------------------------------------------
    # STYLE 3
    #
    # Gross Weight 22,000 KG
    #
    # Try increasingly large label prefixes.
    # ---------------------------------------------------------------

    tokens = s.split()

    best = None

    max_words = (
        5
        if ocr
        else
        8
    )

    for k in range(
        1,
        min(max_words, len(tokens)) + 1,
    ):

        candidate = (
            " ".join(tokens[:k])
            .rstrip(".,;")
        )

        hit = lookup_label(
            candidate,
            0.75 if ocr else None,
        )

        if hit:

            field, score = hit

            candidate_result = (
                field,
                score,
                k,
                candidate,
            )

            if (
                best is None
                or score > best[1]
                or (
                    score == best[1]
                    and k > best[2]
                )
            ):
                best = candidate_result

    if best:

        field, score, k, candidate = best

        return (
            field,
            candidate,
            " ".join(tokens[k:]),
            score,
        )

    return None

# ---------------------------------------------------------------------------
# Document type detection
# ---------------------------------------------------------------------------

def detect_doc_type(text: str):
    """
    Determine SI / BL / other document type.

    We inspect the beginning of the document because titles normally
    appear near the top.
    """

    if not text:
        return None

    useful_lines = [
        line
        for line in text.splitlines()
        if line.strip()
    ][:12]

    head = _compact(
        "\n".join(useful_lines)
    )

    for doc_type, phrases in TITLE_RULES:

        for phrase in phrases:

            if _compact(phrase) in head:
                return doc_type

    return None


# ---------------------------------------------------------------------------
# Field block collection
# ---------------------------------------------------------------------------

def collect_blocks(
    text: str,
    ocr: bool = False,
):
    """
    Convert raw document text into field blocks.

    Example:

        Shipper: ACME LTD
          1 MAIN ROAD
          SINGAPORE

    becomes:

        {
            "shipper": {
                "label": "Shipper",
                "lines": [
                    "ACME LTD",
                    "1 MAIN ROAD",
                    "SINGAPORE"
                ]
            }
        }
    """

    if not text:
        return {}

    text = textwrap.dedent(
        "\n".join(
            line.rstrip()
            for line in text.splitlines()
        )
    )

    blocks = {}

    current = None

    for raw in text.splitlines():

        # Empty lines terminate a field block.
        if not raw.strip():

            current = None
            continue

        indent = (
            len(raw)
            - len(raw.lstrip())
        )

        # -----------------------------------------------------------
        # Continuation line
        # -----------------------------------------------------------

        if (
            indent > 0
            and current is not None
        ):

            blocks[current]["lines"].append(
                raw.strip()
            )

            continue

        # -----------------------------------------------------------
        # New field
        # -----------------------------------------------------------

        hit = parse_label_line(
            raw,
            ocr,
        )

        if not hit:

            current = None
            continue

        field, label, rest, quality = hit

        # Ignore known irrelevant labels such as Net Weight.
        if field == IGNORE:

            current = None
            continue

        # First occurrence wins.
        if field in blocks:

            current = None
            continue

        blocks[field] = {
            "label": label,
            "lines": (
                [rest]
                if rest
                else []
            ),
            "quality": quality,
        }

        current = field

    return blocks


# ---------------------------------------------------------------------------
# Container-row fallback
# ---------------------------------------------------------------------------

_CONTAINER_ROW = re.compile(
    r"^\s*([A-Z]{4}\d{7})\b(.*)$",
    re.M,
)


def _rows_fallback(text: str):
    """
    Detect container-number rows when the document does not explicitly
    provide a container-count field.

    Example:

        ABCD1234567 ... 20,500
        EFGH1234567 ... 21,200

    -> container count = 2

    -> total weight = 41,700 kg
    """

    if not text:
        return None, None

    rows = _CONTAINER_ROW.findall(text)

    if not rows:
        return None, None

    weights = []

    for _, rest in rows:

        m = re.search(
            r"(\d[\d,.]*)\s*(?:KG|KGS)?\s*$",
            rest.strip(),
            re.I,
        )

        if not m:
            continue

        weight = parse_weight_kg(
            m.group(1)
        )

        if weight is not None:
            weights.append(weight)

    total = (
        sum(weights)
        if weights
        and len(weights) == len(rows)
        else None
    )

    return len(rows), total


# ---------------------------------------------------------------------------
# Additional shipping-domain fallbacks
# ---------------------------------------------------------------------------

def _find_port_candidates(text):
    """
    Look for port-like patterns independently of field labels.

    This is NOT used blindly to fill a field.

    It creates evidence that can help a human or AI review.
    """

    if not text:
        return []

    candidates = []

    patterns = [
        r"\b([A-Z][A-Z .'-]{2,40}),\s*([A-Z][A-Z .'-]{2,40})\b",
        r"\b([A-Z][A-Z .'-]{2,40})\s*\(([A-Z]{5})\)",
    ]

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            text.upper(),
        ):

            candidates.append(
                match.group(0).strip()
            )

    # Preserve order while removing duplicates.
    seen = set()
    unique = []

    for value in candidates:

        key = value.upper()

        if key not in seen:

            seen.add(key)
            unique.append(value)

    return unique


def _extract_container_types(text):
    """
    Find common container-size/type expressions.

    Examples:

        40'HC
        40 HC
        20'GP
        45'HC
    """

    if not text:
        return []

    pattern = re.compile(
        r"\b(?:20|40|45)\s*['’]?\s*"
        r"(?:GP|HC|HQ|DV|DC|RF|REEFER)\b",
        re.I,
    )

    return sorted(
        set(
            x.upper().replace("’", "'")
            for x in pattern.findall(text)
        )
    )


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def extract_fields(
    text: str,
    method: str = "text",
    ocr_conf=None,
    images=None,
    ai_client=None,
):
    """
    Extract the seven required fields.

    Public API remains compatible with the original project.
    """

    is_ocr = (
        method == "ocr"
    )

    blocks = collect_blocks(
        text,
        is_ocr,
    )

    # ---------------------------------------------------------------
    # Base confidence by source
    # ---------------------------------------------------------------

    base_conf = {
        "text": 0.98,
        "pdf_text": 0.95,
        "docx": 0.95,
        "xlsx": 0.95,
    }.get(
        method,
        0.90,
    )

    if is_ocr:

        base_conf = min(
            OCR_MAX_CONFIDENCE,
            ocr_conf
            if ocr_conf
            else
            0.60,
        )

    fields = {}
    keys = {}
    evidence = {}

    # ---------------------------------------------------------------
    # Primary extraction
    # ---------------------------------------------------------------

    for field in FIELDS:

        block = blocks.get(field)

        ev = {
            "raw_label": None,
            "raw_value": None,
            "confidence": 0.0,
            "note": None,
            "source": "rule",
        }

        value = None
        key = None

        # -----------------------------------------------------------
        # Label not found
        # -----------------------------------------------------------

        if block is None:

            ev["note"] = (
                "label_not_found"
            )

        else:

            lines = [
                clean(x)
                for x in block["lines"]
            ]

            lines = [
                x
                for x in lines
                if x
            ]

            raw_value = " | ".join(
                lines
            )

            ev.update(
                raw_label=block["label"],
                raw_value=raw_value,
            )

            # Label similarity influences confidence.
            label_quality = float(
                block["quality"]
            )

            confidence = (
                base_conf
                * label_quality
            )

            value, key, extra, note = (
                normalize_value(
                    field,
                    lines,
                )
            )

            ev.update(extra)

            ev["note"] = note

            if note:
                confidence = 0.0

            ev["confidence"] = round(
                confidence,
                3,
            )

        fields[field] = value
        keys[field] = key
        evidence[field] = ev

    # ---------------------------------------------------------------
    # Structural fallback
    # ---------------------------------------------------------------

    n_rows, total_weight = (
        _rows_fallback(text)
    )

    # Container count.
    if (
        fields["container_count"] is None
        and evidence["container_count"]["note"]
        == "label_not_found"
        and n_rows
    ):

        fields["container_count"] = n_rows
        keys["container_count"] = n_rows

        evidence["container_count"].update(
            confidence=0.50,
            note="derived_from_container_rows",
            source="structural_fallback",
            raw_value=f"{n_rows} container rows",
        )

    # Gross weight.
    if (
        fields["gross_weight_kg"] is None
        and evidence["gross_weight_kg"]["note"]
        == "label_not_found"
        and total_weight
    ):

        fields["gross_weight_kg"] = total_weight
        keys["gross_weight_kg"] = total_weight

        evidence["gross_weight_kg"].update(
            confidence=0.50,
            note="derived_from_container_rows",
            source="structural_fallback",
            raw_value=f"sum of {n_rows} container weights",
        )

    # ---------------------------------------------------------------
    # Extra document intelligence metadata
    # ---------------------------------------------------------------

    port_candidates = (
        _find_port_candidates(text)
    )

    container_types = (
        _extract_container_types(text)
    )

    # ---------------------------------------------------------------
    # Optional AI / vision
    # ---------------------------------------------------------------

    ai = enhance(
        fields,
        keys,
        evidence,
        text,
        method,
        images,
        ai_client,
    )

    # ---------------------------------------------------------------
    # Sanity checks
    # ---------------------------------------------------------------

    container_count = (
        fields["container_count"]
    )

    if container_count is not None:

        try:

            if not (
                1
                <= int(container_count)
                <= 500
            ):

                evidence[
                    "container_count"
                ]["note"] = (
                    "implausible_value"
                )

                evidence[
                    "container_count"
                ]["confidence"] = min(
                    evidence[
                        "container_count"
                    ]["confidence"],
                    0.40,
                )

        except (
            ValueError,
            TypeError,
        ):

            evidence[
                "container_count"
            ]["note"] = (
                "implausible_value"
            )

    gross_weight = (
        fields["gross_weight_kg"]
    )

    if gross_weight is not None:

        try:

            if not (
                100
                <= float(gross_weight)
                <= 2_000_000
            ):

                evidence[
                    "gross_weight_kg"
                ]["note"] = (
                    "implausible_value"
                )

                evidence[
                    "gross_weight_kg"
                ]["confidence"] = min(
                    evidence[
                        "gross_weight_kg"
                    ]["confidence"],
                    0.40,
                )

        except (
            ValueError,
            TypeError,
        ):

            evidence[
                "gross_weight_kg"
            ]["note"] = (
                "implausible_value"
            )

    # ---------------------------------------------------------------
    # ADVANCED QUALITY ENGINE
    # ---------------------------------------------------------------

    quality = evaluate(
        fields,
        evidence,
        method,
    )

    # ---------------------------------------------------------------
    # Attach advanced metadata without breaking existing code
    # ---------------------------------------------------------------

    return {
        "fields": fields,

        "keys": keys,

        "evidence": evidence,

        "ai_doc_type": ai[
            "doc_type"
        ],

        # -----------------------------------------------------------
        # NEW ADVANCED OUTPUT
        # -----------------------------------------------------------

        "quality": quality,

        "port_candidates": (
            port_candidates
        ),

        "container_types": (
            container_types
        ),

        "container_rows_detected": (
            n_rows or 0
        ),

        "derived_weight_kg": (
            total_weight
        ),
    }


# ---------------------------------------------------------------------------
# Document-type validation
# ---------------------------------------------------------------------------

def _wrong_type(
    result: dict,
    detected_type,
    expected_type,
) -> bool:

    if (
        detected_type
        and detected_type.startswith(
            "OTHER"
        )
    ):

        result.update(
            status="wrong_doc_type",
            review_reason="wrong_doc_type",
        )

        result[
            "review_notes"
        ].append(
            "document looks like "
            + detected_type.split(
                ":",
                1,
            )[1]
            .replace(
                "_",
                " ",
            )
            .lower()
            + ", expected "
            + (
                expected_type
                or "SI/BL"
            )
        )

        return True

    if (
        detected_type
        and expected_type
        and detected_type != expected_type
    ):

        result.update(
            status="wrong_doc_type",
            review_reason="wrong_doc_type",
        )

        result[
            "review_notes"
        ].append(
            f"file is named {expected_type} "
            f"but its title says {detected_type}"
        )

        return True

    return False


# ---------------------------------------------------------------------------
# Full document extraction
# ---------------------------------------------------------------------------

def extract_document(
    data: bytes,
    filename: str,
    expected_type: str = None,
) -> dict:

    """
    Full file -> extraction pipeline.

    Status:

        ok
        partial
        unreadable
        wrong_doc_type
    """

    result = {
        "source": filename,
        "expected_type": expected_type,
        "detected_type": None,
        "read_method": None,
        "ocr_confidence": None,
        "status": "ok",
        "review_reason": None,
        "review_notes": [],
        "missing_fields": [],
        "low_confidence_fields": [],
        "fields": {
            f: None
            for f in FIELDS
        },
        "keys": {
            f: None
            for f in FIELDS
        },
        "evidence": {},
    }

    # ---------------------------------------------------------------
    # Read document
    # ---------------------------------------------------------------

    rd = read_document(
        data,
        filename,
    )

    result["read_method"] = rd.method
    result["ocr_confidence"] = (
        rd.ocr_confidence
    )

    result[
        "review_notes"
    ].extend(
        rd.warnings
    )

    # ---------------------------------------------------------------
    # AI-only scan fallback
    # ---------------------------------------------------------------

    vision_only = (
        not rd.ok
        and rd.problem in (
            "ocr_unavailable",
            "empty_document",
        )
        and bool(rd.images)
        and ai_enabled()
    )

    if vision_only:

        rd.method = "ocr"

        result[
            "read_method"
        ] = "ocr"

        result[
            "review_notes"
        ].append(
            f"OCR failed ({rd.problem}); "
            "the scan is being read by AI vision only"
        )

    elif not rd.ok:

        result.update(
            status="unreadable",
            review_reason="unreadable",
        )

        result[
            "review_notes"
        ].append(
            f"{rd.problem}: {rd.detail}"
        )

        return result

    # ---------------------------------------------------------------
    # Detect document type
    # ---------------------------------------------------------------

    result[
        "detected_type"
    ] = detect_doc_type(
        rd.text
    )

    if _wrong_type(
        result,
        result["detected_type"],
        expected_type,
    ):

        return result

    # ---------------------------------------------------------------
    # Extract fields
    # ---------------------------------------------------------------

    ext = extract_fields(
        rd.text,
        rd.method,
        rd.ocr_confidence,
        images=rd.images,
    )

    # ---------------------------------------------------------------
    # AI document-type fallback
    # ---------------------------------------------------------------

    if (
        result["detected_type"]
        is None
        and ext["ai_doc_type"]
    ):

        result[
            "detected_type"
        ] = ext["ai_doc_type"]

        result[
            "review_notes"
        ].append(
            "document type was read by AI vision"
        )

        if _wrong_type(
            result,
            result["detected_type"],
            expected_type,
        ):

            return result

    # ---------------------------------------------------------------
    # Copy extraction result
    # ---------------------------------------------------------------

    result[
        "fields"
    ] = ext["fields"]

    result[
        "keys"
    ] = ext["keys"]

    result[
        "evidence"
    ] = ext["evidence"]

    # ---------------------------------------------------------------
    # Advanced metadata
    # ---------------------------------------------------------------

    result[
        "quality"
    ] = ext["quality"]

    result[
        "port_candidates"
    ] = ext["port_candidates"]

    result[
        "container_types"
    ] = ext["container_types"]

    result[
        "container_rows_detected"
    ] = ext[
        "container_rows_detected"
    ]

    result[
        "derived_weight_kg"
    ] = ext[
        "derived_weight_kg"
    ]

    # ---------------------------------------------------------------
    # Missing fields
    # ---------------------------------------------------------------

    result[
        "missing_fields"
    ] = [
        f
        for f in FIELDS
        if result[
            "fields"
        ][f] is None
    ]

    # ---------------------------------------------------------------
    # Low confidence
    # ---------------------------------------------------------------

    result[
        "low_confidence_fields"
    ] = [
        f
        for f in FIELDS
        if (
            result["fields"][f]
            is not None
            and result[
                "evidence"
            ][f][
                "confidence"
            ]
            < REVIEW_CONFIDENCE
        )
    ]

    # ---------------------------------------------------------------
    # Review notes
    # ---------------------------------------------------------------

    if result[
        "missing_fields"
    ]:

        result.update(
            status="partial",
            review_reason="missing_value",
        )

        result[
            "review_notes"
        ].append(
            "missing: "
            + ", ".join(
                result[
                    "missing_fields"
                ]
            )
        )

    if result[
        "low_confidence_fields"
    ]:

        result[
            "review_notes"
        ].append(
            "low confidence: "
            + ", ".join(
                result[
                    "low_confidence_fields"
                ]
            )
        )

    # ---------------------------------------------------------------
    # Advanced validation notes
    # ---------------------------------------------------------------

    quality = result.get(
        "quality",
        {},
    )

    quality_status = quality.get(
        "validation_status"
    )

    if quality_status in (
        "REVIEW",
        "VERIFY",
    ):

        result[
            "review_notes"
        ].append(
            "advanced validation: "
            + quality_status
        )

    for flag in quality.get(
        "flags",
        [],
    ):

        result[
            "review_notes"
        ].append(
            "validation flag: "
            + flag
        )

    return result