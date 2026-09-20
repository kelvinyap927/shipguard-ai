"""
Member C - Verification, Normalisation & Reliability          (revision 2)
SDOC Hackathon 2026

This module intentionally does NOT classify emails or extract document text.
It consumes extracted SI/BL data from Member B and produces:
    OK | MISMATCH | NEEDS_REVIEW
plus evidence suitable for Member D and a submission record suitable for the
organizer's self-evaluation endpoint.

Design goals
- conservative: never turn missing/uncertain information into a mismatch
- deterministic: no LLM / fuzzy guesswork for the core decision
- field-specific normalisation and comparison
- preserve raw evidence (and optionally persist it: save_evidence)
- tolerate several reasonable Member-B payload shapes
- a human correction/confirmation is re-run through the SAME verifier
- never crash the pipeline: internal failures become a visible, retryable
  NEEDS_REVIEW record

Revision-2 changes (see README_MEMBER_C.md, "Change log")
  * entity names: " | " separated addresses (xlsx) no longer cause false MISMATCH
  * label aliases: bilingual (docx) labels and "TOTAL ..." labels (pdf) map correctly
  * document type: tolerant classification of titles such as
    "BILL OF LADING (DRAFT)" / "BILL OF LADING INSTRUCTION" / "BL INSTRUCTION"
  * placeholders such as "____MT", "NIL", "TBD" are treated as missing everywhere
  * review-reason classification looks at BOTH sides (was SI only)
  * confidence values: percentages / NaN / negative / non-numeric no longer
    silently disable the low-confidence check
  * duplicate-alias conflicts compare normalised values (no false conflicts)
  * container / weight parsing: 3x40HC, 3 x 40'HC, 3.0, "1,234.5", "22,5 t",
    "22,000 KG (22 MT)" ... are parsed correctly or escalated, never guessed
  * ports: UN/LOCODE only stripped when it looks like a code AND agrees;
    country-optional match; "(NORTH)" vs "(SOUTH)" no longer match
  * review results keep ALL field comparisons (a real mismatch is not hidden)
  * apply_human_correction: works for every payload shape, can resolve
    unreadable / wrong-doc / missing-attachment reviews, supports "confirm",
    and returns an audit block
  * verify() never raises for bad input; category is validated
"""

from __future__ import annotations

import copy
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


COMPARE_FIELDS = (
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
)

CATEGORIES = {"BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"}
REVIEW_REASONS = {"wrong_doc_type", "missing_attachment", "unreadable", "missing_value"}

# --------------------------------------------------------------------------
# Missing / placeholder detection
# --------------------------------------------------------------------------
_MISSING_TOKENS = {
    "", "n/a", "na", "n.a.", "n.a", "none", "null", "nil", "unknown",
    "tba", "tbc", "tbd", "to be advised", "to be confirmed", "to be determined",
    "not available", "not applicable", "not stated", "not provided", "blank",
    "pending", "-", "--", "\u2014", "\u2013",
}
# only punctuation / underscores / question marks  ("???", "_______", "---")
_PLACEHOLDER_CHARS_RE = re.compile(r"[\s_?\-\u2013\u2014.*#/\\]+")
# a placeholder followed only by a unit word: "____MT", "??? MTS", "N/A KG"
_PLACEHOLDER_UNIT_RE = re.compile(r"(.*?)\s*(?:mts?|kgs?|tonnes?)\.?")

# --------------------------------------------------------------------------
# Field aliases
# --------------------------------------------------------------------------
FIELD_ALIASES = {
    "shipper": {
        "shipper", "shipper/exporter", "shipper exporter",
        "shipper (principal or seller)", "exporter", "seller",
    },
    "consignee": {
        "consignee", "consignee (non-negotiable)", "receiver", "to the order of",
    },
    "notify_party": {
        "notify", "notify party", "notify party/intermediate consignee",
        "intermediate consignee", "notify_party",
        "notify party / intermediate consignee",
    },
    "port_of_loading": {
        "port of loading", "port of loading (pol)", "load port", "pol",
        "port_of_loading", "loading port",
    },
    "port_of_discharge": {
        "port of discharge", "port of discharge (pod)", "discharge port",
        "pod", "port_of_discharge", "discharging port",
    },
    "container_count": {
        "no. of containers", "total containers",
        "no. of containers or packages", "container count",
        "containers", "container_count",
    },
    "gross_weight_kg": {
        "gross weight", "gross weight (kg)", "gross wt (kgs)", "gross wt (kg)",
        "gross weight (kgs)", "gross weight\u6bdb\u91cd(kgs)", "gross weight\u6bdb\u91cd",
        "gross_weight_kg", "gross wt", "gross weight kg", "gross weight kgs",
    },
}

_CJK = "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_CJK_RE = re.compile(f"[{_CJK}]")
_CJK_PAREN_RE = re.compile(rf"\s*\([^)]*[{_CJK}][^)]*\)")


def _label_key(name: str) -> str:
    """Canonical lookup key for a field label.

    Handles: case, NFKC, bilingual suffixes "(\u53d1\u8d27\u4eba)", CJK glued to the label
    ("Gross Weight\u6bdb\u91cd(KGS)"), trailing colon, spacing before "(", underscores.
    """
    s = unicodedata.normalize("NFKC", str(name)).casefold()
    s = _CJK_PAREN_RE.sub(" ", s)          # "(\u53d1\u8d27\u4eba)", "(\u6bdb\u91cd KGS)"
    s = _CJK_RE.sub("", s)                 # CJK glued to the English label
    s = s.replace("_", " ")
    s = re.sub(r"\s*:\s*$", "", s.strip())
    s = re.sub(r"\s*\(\s*", " (", s)
    s = re.sub(r"\s*\)", ")", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


_ALIAS_TO_CANONICAL = {
    _label_key(k): field
    for field, aliases in FIELD_ALIASES.items()
    for k in aliases
}
_FIELD_KEYS = {_label_key(f): f for f in COMPARE_FIELDS}

# --------------------------------------------------------------------------
# Weight units
# --------------------------------------------------------------------------
_TONNE_UNIT_RE = re.compile(
    r"(?<![a-z])(?:mts?|m/t|tonnes?|metric\s+tonnes?|metric\s+tons?|t)(?![a-z/])"
)
_KG_UNIT_RE = re.compile(
    r"(?<![a-z])(?:kgs?|kilograms?|\u516c\u65a4|\u5343\u514b)(?![a-z])"
)
_WEIGHT_FILLER_RE = re.compile(r"\b(?:gross|total|weight|wt|approx\.?|about)\b")
_WEIGHT_NUM_RE = re.compile(
    r"(?<![\d.,])(?:\d{1,3}(?:[ \u202f]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)*)(?![\d])"
)


@dataclass
class NormalizedValue:
    field: str
    raw: Any
    normalized: Any
    present: bool
    valid: bool
    reason: Optional[str] = None
    confidence: Optional[float] = None
    source: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None   # e.g. port name / code / country
    note: Optional[str] = None


# --------------------------------------------------------------------------
# Basic helpers
# --------------------------------------------------------------------------
def _clean_scalar(value: Any) -> Any:
    if isinstance(value, str):
        value = unicodedata.normalize("NFKC", value)
        value = value.replace("\u00a0", " ")
        value = value.strip()
    return value


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str):
        s = re.sub(r"\s+", " ", _clean_scalar(value).casefold())
        if s in _MISSING_TOKENS:
            return True
        if _PLACEHOLDER_CHARS_RE.fullmatch(s):
            return True
        m = _PLACEHOLDER_UNIT_RE.fullmatch(s)
        if m:
            head = m.group(1).strip()
            if head in _MISSING_TOKENS or _PLACEHOLDER_CHARS_RE.fullmatch(head or "_"):
                return True
    return False


def _parse_confidence(c: Any) -> Tuple[Optional[float], Optional[str]]:
    """Return (confidence, note). Never silently drops a bad confidence:
    an unusable value becomes 0.0 (forces human review) with an explanation."""
    if c is None:
        return None, None
    if isinstance(c, bool):
        return 0.0, "invalid confidence (boolean)"
    try:
        x = float(c)
    except (TypeError, ValueError):
        return 0.0, f"invalid confidence {c!r}"
    if math.isnan(x) or x < 0:
        return 0.0, f"invalid confidence {c!r}"
    if x <= 1:
        return x, None
    if x <= 100:
        return x / 100.0, f"confidence {c!r} interpreted as a percentage"
    return 0.0, f"invalid confidence {c!r}"


def _extract_value_meta(item: Any):
    """
    Accepts a scalar or a Member-B object:
      {"value": ..., "confidence": ..., "source": ..., "status": ...}
    Returns (value, confidence, source, meta_error, note).
    """
    if not isinstance(item, Mapping):
        return item, None, None, None, None

    value = item.get("value", item.get("raw_value", item.get("text")))
    if value is None and "normalized" in item:
        value = item["normalized"]

    confidence, note = _parse_confidence(item.get("confidence"))
    if item.get("confirmed_by_human"):
        confidence, note = 1.0, "confirmed by human reviewer"

    source = item.get("source") or item.get("evidence") or item.get("location")
    status = item.get("status")
    if isinstance(status, str) and status.casefold() in {
        "unreadable", "parse_error", "error", "failed"
    }:
        return value, confidence, source, "unreadable", note
    return value, confidence, source, None, note


def _item_value(item: Any) -> Any:
    return _extract_value_meta(item)[0]


def _canonical_field_name(name: Any) -> Optional[str]:
    if not isinstance(name, str):
        return None
    key = _label_key(name)
    if key in _FIELD_KEYS:
        return _FIELD_KEYS[key]
    if key in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[key]
    # "TOTAL Gross Wt (kgs)", "Total Gross Weight" (pdf footers)
    if key.startswith("total ") and key[6:] in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[key[6:]]
    return None


def _normalize_text(value: Any) -> str:
    s = _clean_scalar(value)
    if not isinstance(s, str):
        s = str(s)
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s*\n\s*", "\n", s).strip()
    return s


# --------------------------------------------------------------------------
# Entities (shipper / consignee / notify)
# --------------------------------------------------------------------------
def _normalize_entity(value: Any) -> str:
    s = _normalize_text(value).casefold()

    # If extraction included the address, compare the primary entity name.
    # xlsx cells use  "NAME | ADDR1; ADDR2",  docx/pdf use  "NAME\nADDR1\nADDR2".
    pieces = [p.strip() for p in re.split(r"[\n;|]+", s) if p.strip()]
    if len(pieces) > 1:
        s = pieces[0]

    s = re.sub(
        r"^(shipper(?:/exporter)?|consignee|notify(?: party)?|seller|receiver)\s*[:\-]\s*",
        "", s, flags=re.I,
    )
    s = s.replace("&", " and ")
    s = re.sub(r"[.,]+", " ", s)
    s = re.sub(r"[\(\)\[\]\{\}]", " ", s)
    s = re.sub(r"\s*-\s*", " ", s)            # FZ-LLC == FZ LLC
    s = re.sub(r"\s+", " ", s).strip(" ,;:-")
    return s


# --------------------------------------------------------------------------
# Ports
# --------------------------------------------------------------------------
_LOCODE_PAREN_RE = re.compile(r"\(\s*([A-Za-z]{2}[A-Za-z0-9]{3})\s*\)")
_PORT_PREFIX_RE = re.compile(
    r"^(port of loading|load port|pol|port of discharge|discharge port|pod)\s*[:\-]\s*",
    re.I,
)


def _clean_port_segment(seg: str) -> str:
    seg = seg.replace("&", " and ")
    seg = re.sub(r"[/|;:]+", " ", seg)
    seg = re.sub(r"[-]+", " ", seg)
    seg = seg.replace(".", "")
    seg = re.sub(r"[\(\)]", " ", seg)
    return re.sub(r"\s+", " ", seg).strip()


def _split_port(value: Any) -> Dict[str, Any]:
    s = _normalize_text(value)
    s = _PORT_PREFIX_RE.sub("", s)
    codes = [m.group(1).upper() for m in _LOCODE_PAREN_RE.finditer(s)]
    s = _LOCODE_PAREN_RE.sub(" ", s).casefold()
    parts = [_clean_port_segment(p) for p in s.split(",")]
    parts = [p for p in parts if p]
    name = parts[0] if parts else ""
    country = " ".join(parts[1:])
    full = (name + " " + country).strip()
    return {"name": name, "country": country, "code": codes[0] if codes else None, "full": full}


def _normalize_port(value: Any) -> str:
    return _split_port(value)["full"]


# --------------------------------------------------------------------------
# Numbers
# --------------------------------------------------------------------------
def _decimal_from_token(token: str, unit: Optional[str]) -> Tuple[Optional[Decimal], Optional[str]]:
    """Interpret a numeric token; return (value, None) or (None, reason) if ambiguous."""
    t = re.sub(r"[ \u202f]", "", token)
    try:
        if "," in t and "." in t:
            dec = "," if t.rfind(",") > t.rfind(".") else "."
            other = "." if dec == "," else ","
            t = t.replace(other, "").replace(dec, ".")
            return Decimal(t), None
        if "," in t:
            parts = t.split(",")
            if all(len(p) == 3 for p in parts[1:]) and 1 <= len(parts[0]) <= 3:
                if unit == "tonne":
                    return None, "ambiguous_number_format"  # "21,577 MT": thousands or decimal comma?
                return Decimal("".join(parts)), None
            return None, "ambiguous_number_format"          # "22,5"
        if "." in t:
            parts = t.split(".")
            if len(parts) > 2:
                if all(len(p) == 3 for p in parts[1:]):
                    return Decimal("".join(parts)), None    # 1.234.567
                return None, "ambiguous_number_format"
            if len(parts[1]) == 3:
                # "21.577": decimal for tonnes, thousands-separator for kg  -> ambiguous
                if unit == "tonne":
                    return Decimal(t), None
                return None, "ambiguous_number_format"
            return Decimal(t), None
        return Decimal(t), None
    except InvalidOperation:
        return None, "invalid_gross_weight"


def _parse_number(raw: Any) -> Optional[Decimal]:
    """Kept for backward compatibility: first numeric token as Decimal."""
    if isinstance(raw, bool) or raw is None:
        return None
    if isinstance(raw, (int, float, Decimal)):
        try:
            d = Decimal(str(raw))
            return d if d.is_finite() else None
        except InvalidOperation:
            return None
    m = _WEIGHT_NUM_RE.search(_normalize_text(raw))
    if not m:
        return None
    d, err = _decimal_from_token(m.group(0), None)
    return d if err is None else None


def _normalize_container_count(value: Any) -> Tuple[Optional[int], Optional[str]]:
    if _is_missing(value):
        return None, "missing_value"
    if isinstance(value, bool):
        return None, "invalid_container_count"
    if isinstance(value, int):
        return (value, None) if value > 0 else (None, "invalid_container_count")
    if isinstance(value, (float, Decimal)):
        try:
            d = Decimal(str(value))
            if d.is_finite() and d == d.to_integral_value() and d > 0:
                return int(d), None
        except InvalidOperation:
            pass
        return None, "invalid_container_count"

    s = _normalize_text(value).casefold().replace("\u00d7", "x")

    m = re.fullmatch(r"\s*(\d+)(?:\.0+)?\s*", s)
    if m:
        n = int(m.group(1))
        return (n, None) if n > 0 else (None, "invalid_container_count")

    # "3 x 40'HC", "3x40HC", "3 X 20'FCL"
    groups = re.findall(r"(?<![\d.\-])(\d+)\s*x(?![a-z])", s)
    if not groups:
        groups = re.findall(r"(?<![\d.\-])(\d+)\s*(?:containers?|ctnrs?|units?)\b", s)
    if len(groups) > 1:
        # e.g. "1 x 40'HC + 2 x 20'GP": do not guess which number is the total
        return None, "ambiguous_container_count"
    if len(groups) == 1:
        n = int(groups[0])
        return (n, None) if n > 0 else (None, "invalid_container_count")

    nums = re.findall(r"(?<![\d.\-])\d+(?![\d.])", s)
    if len(nums) == 1:
        n = int(nums[0])
        return (n, None) if n > 0 else (None, "invalid_container_count")
    return None, "invalid_container_count"


def _normalize_gross_weight(value: Any) -> Tuple[Optional[int], Optional[str]]:
    if _is_missing(value):
        return None, "missing_value"
    if isinstance(value, bool):
        return None, "invalid_gross_weight"

    if isinstance(value, (int, float, Decimal)):
        try:
            n = Decimal(str(value))
        except InvalidOperation:
            return None, "invalid_gross_weight"
        if not n.is_finite() or n <= 0:
            return None, "invalid_gross_weight"
        if n != n.to_integral_value():
            return None, "non_integer_gross_weight"
        return int(n), None

    s = _normalize_text(value).casefold()
    if re.search(r"(?<![\w)])-\s*\d", s):
        return None, "invalid_gross_weight"             # negative weight
    tokens = _WEIGHT_NUM_RE.findall(s)
    if not tokens:
        return None, "invalid_gross_weight"
    if len(tokens) > 1:
        return None, "ambiguous_gross_weight"      # "22,000 KG / 22 MT", "40'HC 22,000 KG"

    rest = s.replace(tokens[0], " ", 1)
    has_tonne = bool(_TONNE_UNIT_RE.search(rest))
    has_kg = bool(_KG_UNIT_RE.search(rest))
    if has_tonne and has_kg:
        return None, "ambiguous_gross_weight"

    unit = "tonne" if has_tonne else ("kg" if has_kg else None)
    if unit is None:
        leftover = _WEIGHT_FILLER_RE.sub(" ", rest)
        if re.search(r"[a-z]", leftover):
            return None, "unknown_weight_unit"

    n, err = _decimal_from_token(tokens[0], unit)
    if err:
        return None, err
    if n is None or n <= 0:
        return None, "invalid_gross_weight"
    if unit == "tonne":
        n = n * Decimal("1000")
    if n != n.to_integral_value():
        return None, "non_integer_gross_weight"
    return int(n), None


# --------------------------------------------------------------------------
# Public normaliser
# --------------------------------------------------------------------------
def normalize_value(field: str, raw_item: Any) -> NormalizedValue:
    raw, confidence, source, meta_error, note = _extract_value_meta(raw_item)

    def make(normalized, valid, reason=None, extra=None):
        return NormalizedValue(field, raw, normalized, valid, valid, reason,
                               confidence, source, extra, note)

    if meta_error == "unreadable":
        return NormalizedValue(field, raw, None, False, False, "unreadable",
                               confidence, source, None, note)
    if _is_missing(raw):
        return NormalizedValue(field, raw, None, False, False, "missing_value",
                               confidence, source, None, note)

    if field in {"shipper", "consignee", "notify_party"}:
        n = _normalize_entity(raw)
        return make(n or None, bool(n), None if n else "missing_value")

    if field in {"port_of_loading", "port_of_discharge"}:
        p = _split_port(raw)
        return make(p["full"] or None, bool(p["full"]), None if p["full"] else "missing_value", p)

    if field == "container_count":
        n, err = _normalize_container_count(raw)
        return make(n, n is not None, err)

    if field == "gross_weight_kg":
        n, err = _normalize_gross_weight(raw)
        return make(n, n is not None, err)

    raise KeyError(field)


# --------------------------------------------------------------------------
# Payload plumbing
# --------------------------------------------------------------------------
_SIDE_KEYS = {
    "si": ("si", "SI", "shipping_instruction", "shippingInstruction"),
    "bl": ("bl", "BL", "bill_of_lading", "billOfLading"),
}
_CONTAINER_KEYS = ("documents", "extracted", "data")


def _locate_document(payload: Mapping[str, Any], side: str):
    """Return (container, key) where verify() reads the SI/BL mapping from."""
    candidates = []
    for ck in _CONTAINER_KEYS:
        obj = payload.get(ck)
        if isinstance(obj, Mapping):
            candidates.append(obj)
    candidates.append(payload)
    for obj in candidates:
        for key in _SIDE_KEYS[side.casefold()]:
            if isinstance(obj.get(key), Mapping):
                return obj, key
    return None


def _extract_document_mapping(payload: Mapping[str, Any], side: str) -> Mapping[str, Any]:
    loc = _locate_document(payload, side)
    return loc[0][loc[1]] if loc else {}


_META_KEYS = {
    "si": ("si_meta", "SI_meta", "si_metadata", "SI_metadata"),
    "bl": ("bl_meta", "BL_meta", "bl_metadata", "BL_metadata"),
}


def _locate_meta(payload: Mapping[str, Any], side: str):
    for key in _META_KEYS[side.casefold()]:
        if isinstance(payload.get(key), Mapping):
            return payload, key
    for key in ("document_meta", "documents_meta", "metadata"):
        meta = payload.get(key)
        if isinstance(meta, Mapping):
            for side_key in (side, side.upper(), side.casefold()):
                if isinstance(meta.get(side_key), Mapping):
                    return meta, side_key
    return None


def _get_meta(payload: Mapping[str, Any], side: str) -> Mapping[str, Any]:
    loc = _locate_meta(payload, side)
    return loc[0][loc[1]] if loc else {}


def _is_false(v: Any) -> bool:
    return v is False or (isinstance(v, (int, float)) and not isinstance(v, bool) and v == 0) \
        or (isinstance(v, str) and v.strip().casefold() in {"false", "no", "0", "n"})


def _is_true(v: Any) -> bool:
    return v is True or (isinstance(v, (int, float)) and not isinstance(v, bool) and v == 1) \
        or (isinstance(v, str) and v.strip().casefold() in {"true", "yes", "1", "y"})


# --- document type ---------------------------------------------------------
_NON_DOC_LABELS = {"", "unknown", "none", "null", "n/a", "na"}
_WRONG_DOC_RE = re.compile(
    r"invoice|packing\s*list|certificate|origin|waybill|manifest|purchase\s*order|"
    r"delivery\s*order|debit\s*note|credit\s*note|statement|receipt", re.I)


def _classify_doc_text(text: str) -> Optional[str]:
    """Return 'si', 'bl', 'other' or None (no information)."""
    t = unicodedata.normalize("NFKC", text).casefold().strip()
    if t in _NON_DOC_LABELS:
        return None
    if _WRONG_DOC_RE.search(t):
        return "other"
    if "instruction" in t or re.search(r"(?<![a-z])s\.?i\.?(?![a-z])", t):
        return "si"          # "BILL OF LADING INSTRUCTION", "BL INSTRUCTION", "S.I."
    if "lading" in t or re.search(r"(?<![a-z])b/?l(?![a-z])", t) or "draft" in t:
        return "bl"
    return "other"


def _infer_document_type(meta: Mapping[str, Any], doc: Mapping[str, Any]) -> Optional[str]:
    """Explicit Member-B metadata first; otherwise the document's opening lines."""
    raw = (meta.get("document_type") or meta.get("doc_type")
           or doc.get("document_type") or doc.get("doc_type"))
    if raw is not None:
        return _classify_doc_text(str(raw))

    text = meta.get("raw_text") or meta.get("text") or meta.get("document_text")
    if isinstance(text, str) and text.strip():
        head = " ".join([ln for ln in text.splitlines() if ln.strip()][:6])
        return _classify_doc_text(head)
    return None


def _raw_doc_label(meta: Mapping[str, Any]) -> str:
    return str(meta.get("document_type") or meta.get("doc_type") or "unknown")


def _meta_unreadable(meta: Mapping[str, Any]) -> bool:
    if not meta:
        return False
    if _is_false(meta.get("readable")):
        return True
    for key in ("status", "ocr_status", "parse_status"):
        st = str(meta.get(key, "")).strip().casefold()
        if st in {"unreadable", "parse_error", "error", "failed", "ocr_failed"}:
            return True
    if meta.get("error"):
        return True
    return False


def _has_attachment_problem(meta: Mapping[str, Any]) -> Optional[str]:
    if meta and _is_true(meta.get("missing_attachment")):
        return "missing_attachment"
    return None


def _confidence_issue(nv: NormalizedValue, threshold: float) -> bool:
    return nv.confidence is not None and nv.confidence < threshold


# --------------------------------------------------------------------------
# Canonicalisation
# --------------------------------------------------------------------------
def _canonicalize_with_conflicts(document: Mapping[str, Any]) -> Tuple[Dict[str, Any], Dict[str, list]]:
    """Canonicalise fields; detect duplicate aliases carrying DIFFERENT information.
    Values are compared after field-specific normalisation, so "22,000 KG" and
    "22 MT" (or differing confidences) are not conflicts."""
    result: Dict[str, Any] = {}
    conflicts: Dict[str, list] = {}
    for key, value in document.items():
        field = _canonical_field_name(key)
        if not field:
            continue
        if field not in result or _is_missing(_item_value(result[field])):
            result[field] = value
            continue
        first = result[field]
        if _is_missing(_item_value(value)):
            continue
        a, b = normalize_value(field, first), normalize_value(field, value)
        same = (a.valid and b.valid and a.normalized == b.normalized) or \
               (str(_item_value(first)).strip().casefold() == str(_item_value(value)).strip().casefold())
        if not same:
            conflicts.setdefault(field, [_item_value(first)])
            conflicts[field].append(_item_value(value))
    return result, conflicts


def canonicalize_fields(document: Mapping[str, Any]) -> Dict[str, Any]:
    """Map known field labels to the seven canonical field names.
    If duplicate aliases occur, the first non-missing value is returned;
    internal verification additionally detects the conflict and escalates it."""
    return _canonicalize_with_conflicts(document)[0]


def _normalise_document(document: Mapping[str, Any]):
    canonical, conflicts = _canonicalize_with_conflicts(document)
    return {f: normalize_value(f, canonical.get(f)) for f in COMPARE_FIELDS}, conflicts


# --------------------------------------------------------------------------
# Comparison
# --------------------------------------------------------------------------
def _compare_values(field: str, si: NormalizedValue, bl: NormalizedValue) -> Tuple[str, str]:
    """Returns (status, reason); status in MATCH | MISMATCH | REVIEW.
    Only called when both values are valid and present."""
    if field in {"shipper", "consignee", "notify_party"}:
        # No fuzzy/prefix matching: "APRIL FINE PAPER TRADING" and
        # "APRIL FINE PAPER TRADING (MIDDLE EAST) FZE" are different parties.
        if si.normalized == bl.normalized:
            return "MATCH", "normalised entity values are equal"
        return "MISMATCH", "normalised entity values differ"

    if field in {"port_of_loading", "port_of_discharge"}:
        a, b = si.extra or {}, bl.extra or {}
        if a.get("code") and b.get("code") and a["code"] != b["code"]:
            return "MISMATCH", "port codes differ"
        if a.get("name") != b.get("name"):
            return "MISMATCH", "normalised port names differ"
        ca, cb = a.get("country"), b.get("country")
        if ca and cb and ca != cb:
            # same port name, different country wording (US vs USA, UAE vs
            # UNITED ARAB EMIRATES) or a genuinely different port (PORTLAND)
            return "REVIEW", "same port name but country text differs"
        return "MATCH", "normalised port values are equal"

    if field in {"container_count", "gross_weight_kg"}:
        if si.normalized == bl.normalized:
            return "MATCH", "normalised numeric values are equal"
        return "MISMATCH", "normalised numeric values differ"

    raise KeyError(field)


def _evidence_value(nv: NormalizedValue) -> Dict[str, Any]:
    return {"raw": nv.raw, "normalized": nv.normalized,
            "confidence": nv.confidence, "source": nv.source, "note": nv.note}


_VALUE_REASONS = {
    "missing_value", "invalid_container_count", "invalid_gross_weight",
    "unknown_weight_unit", "non_integer_gross_weight", "ambiguous_container_count",
    "ambiguous_gross_weight", "ambiguous_number_format",
}


def _base_result(email_id, category, status, reason, has_defect, defects, message, review, field_results):
    return {
        "email_id": email_id, "category": category, "status": status,
        "review_reason": reason, "has_defect": has_defect, "defect_fields": defects,
        "message": message, "requires_human_review": review,
        "field_results": field_results, "discrepancies": [],
    }


def _not_evaluated(email_id, category, message=None):
    return _base_result(email_id, category, "OK", None, False, [], message, False, {})


def _review_result(email_id, category, reason, message, si_meta, bl_meta, *,
                   field_results=None, partial_defects=None, extra=None):
    r = _base_result(email_id, category, "NEEDS_REVIEW", reason, False, [], message, True,
                     field_results or {})
    r["document_evidence"] = {"si": dict(si_meta) if si_meta else {},
                              "bl": dict(bl_meta) if bl_meta else {}}
    if partial_defects:
        r["partial_defect_fields"] = list(partial_defects)
    if extra:
        r.update(extra)
    return r


def _field_result_dict(si_n, bl_n, *, only=None) -> Dict[str, Any]:
    """Backward-compatible helper (review rows only)."""
    allowed = {x[0] for x in only} if only is not None else set(COMPARE_FIELDS)
    out = {}
    for f in COMPARE_FIELDS:
        if f in allowed:
            out[f] = {"status": "REVIEW", "si": _evidence_value(si_n[f]),
                      "bl": _evidence_value(bl_n[f]),
                      "reason": f"SI={si_n[f].reason}; BL={bl_n[f].reason}"}
    return out


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------
def _normalise_category(category: Any) -> str:
    c = str(category).strip().upper().replace(" ", "_").replace("-", "_")
    if c not in CATEGORIES:
        raise ValueError(f"Unknown category {category!r}; expected one of {sorted(CATEGORIES)}")
    return c


def verify(
    payload: Mapping[str, Any],
    *,
    email_id: Optional[str] = None,
    category: str = "BL_COMPARISON",
    confidence_threshold: float = 0.70,
) -> Dict[str, Any]:
    """
    Main Member-C entry point. Route only document-comparison requests here.

    Never raises for malformed *payloads*: an internal failure is returned as a
    visible, retryable NEEDS_REVIEW record (processing_error=True).
    An invalid *category* is a programming error and raises ValueError.
    """
    category = _normalise_category(category)
    try:
        return _verify_impl(payload, email_id, category, confidence_threshold)
    except Exception as exc:  # noqa: BLE001 - reliability requirement: fail visibly
        r = _review_result(
            email_id, category, "unreadable",
            f"Verification could not be completed ({type(exc).__name__}: {exc}). "
            "Retry, or review the documents manually.",
            {}, {}, extra={"processing_error": True, "retryable": True,
                           "error": f"{type(exc).__name__}: {exc}"},
        )
        return r


def _verify_impl(payload, email_id, category, confidence_threshold) -> Dict[str, Any]:
    if category != "BL_COMPARISON":
        return _not_evaluated(email_id, category)
    if not isinstance(payload, Mapping):
        raise TypeError(f"payload must be a mapping, got {type(payload).__name__}")

    si = _extract_document_mapping(payload, "si")
    bl = _extract_document_mapping(payload, "bl")
    si_meta = _get_meta(payload, "si")
    bl_meta = _get_meta(payload, "bl")
    si_hv = bool(si_meta.get("human_verified"))
    bl_hv = bool(bl_meta.get("human_verified"))

    attachment_problem = ((not si_hv and _has_attachment_problem(si_meta))
                          or (not bl_hv and _has_attachment_problem(bl_meta)))
    attachments_expected = bool(
        _is_true(payload.get("attachments_expected"))
        or _is_true(si_meta.get("attachments_expected"))
        or _is_true(bl_meta.get("attachments_expected"))
    )

    # 1) document-level gates (a human-verified side skips its own gates)
    if (not si_hv and _meta_unreadable(si_meta)) or (not bl_hv and _meta_unreadable(bl_meta)):
        return _review_result(email_id, category, "unreadable",
                              "At least one required document could not be read reliably.",
                              si_meta, bl_meta)

    if attachment_problem or (attachments_expected and (not si or not bl)):
        return _review_result(email_id, category, "missing_attachment",
                              "Required attachment is missing; comparison cannot be completed.",
                              si_meta, bl_meta)

    if not si_hv:
        si_type = _infer_document_type(si_meta, si)
        if si_type is not None and si_type != "si":
            return _review_result(
                email_id, category, "wrong_doc_type",
                f"SI attachment was identified as {_raw_doc_label(si_meta)!r}, "
                "not a Shipping Instruction.", si_meta, bl_meta)
    if not bl_hv:
        bl_type = _infer_document_type(bl_meta, bl)
        if bl_type is not None and bl_type != "bl":
            return _review_result(
                email_id, category, "wrong_doc_type",
                f"BL attachment was identified as {_raw_doc_label(bl_meta)!r}, "
                "not a Bill of Lading.", si_meta, bl_meta)

    # A document that was received/processed (metadata exists) but produced no
    # fields must not be silently treated as "nothing to compare".
    if (si_meta and not si) or (bl_meta and not bl):
        return _review_result(email_id, category, "unreadable",
                              "A document was received but no fields could be extracted from it.",
                              si_meta, bl_meta)

    if not si or not bl:
        # "please send the draft BL" emails: nothing to compare yet. Member A
        # should not call verify() for these; if it does, stay unevaluated.
        return _not_evaluated(
            email_id, category,
            "Comparison not performed because the required documents are not available yet.")

    # 2) field-level normalisation
    si_n, si_conf = _normalise_document(si)
    bl_n, bl_conf = _normalise_document(bl)

    dup = [(side, f, v) for side, c in (("SI", si_conf), ("BL", bl_conf)) for f, v in c.items()]
    if dup:
        detail = "; ".join(f"{s}.{f} has conflicting extracted values: {v!r}" for s, f, v in dup)
        return _review_result(email_id, category, "missing_value",
                              "Conflicting extracted values require human confirmation. " + detail,
                              si_meta, bl_meta)

    # 3) evaluate every field (uncertainty is NOT a mismatch, but real
    #    mismatches on other fields are still kept for the reviewer)
    field_results: Dict[str, Any] = {}
    problems: List[Tuple[str, Optional[str], Optional[str]]] = []
    defects: List[str] = []
    for f in COMPARE_FIELDS:
        a, b = si_n[f], bl_n[f]
        row = {"si": _evidence_value(a), "bl": _evidence_value(b)}
        if not a.valid or not b.valid:
            problems.append((f, a.reason if not a.valid else None, b.reason if not b.valid else None))
            row.update(status="REVIEW", reason=f"SI={a.reason}; BL={b.reason}")
        elif _confidence_issue(a, confidence_threshold) or _confidence_issue(b, confidence_threshold):
            problems.append((f, "low_confidence", "low_confidence"))
            row.update(status="REVIEW",
                       reason=f"low extraction confidence (SI={a.confidence}, BL={b.confidence})")
        else:
            status, reason = _compare_values(f, a, b)
            if status == "REVIEW":
                problems.append((f, "ambiguous_format", "ambiguous_format"))
            elif status == "MISMATCH":
                defects.append(f)
            row.update(status=status, reason=reason)
        field_results[f] = row

    if problems:
        details = "; ".join(f"{f}: SI={sr or 'ok'}, BL={br or 'ok'}" for f, sr, br in problems)
        reasons = {r for _, sr, br in problems for r in (sr, br) if r}
        reason = "missing_value" if reasons & _VALUE_REASONS else "unreadable"
        return _review_result(
            email_id, category, reason,
            "One or more required values cannot be compared confidently. " + details,
            si_meta, bl_meta, field_results=field_results, partial_defects=defects)

    if defects:
        r = _base_result(email_id, category, "MISMATCH", None, True, defects,
                         "Mismatch detected in: " + ", ".join(defects), False, field_results)
        r["discrepancies"] = [
            {"field": f, "si": field_results[f]["si"]["raw"], "bl": field_results[f]["bl"]["raw"]}
            for f in defects
        ]
        return r

    return _base_result(email_id, category, "OK", None, False, [],
                        "No mismatch detected.", False, field_results)


# --------------------------------------------------------------------------
# Submission helpers / evidence store
# --------------------------------------------------------------------------
def to_submission_record(result: Mapping[str, Any]) -> Dict[str, Any]:
    """Strip internal evidence into the exact v2 self-evaluation shape."""
    return {
        "category": result.get("category", "GENERAL"),
        "status": result.get("status", "OK"),
        "review_reason": result.get("review_reason"),
        "defect_fields": list(result.get("defect_fields") or []),
        "has_defect": bool(result.get("has_defect", False)),
    }


def merge_into_submission(submission: Dict[str, Any], email_id: str,
                          result: Mapping[str, Any]) -> Dict[str, Any]:
    """Mutate and return a submission dict for the organizer's scorer."""
    submission[email_id] = to_submission_record(result)
    return submission


def save_evidence(result: Mapping[str, Any], path: str = "member_c_evidence.jsonl") -> None:
    """Append one verification result (with all evidence) to a JSON-Lines file.
    Gives Member D / the audit trail a persistent record of every decision."""
    rec = {"saved_at": datetime.now(timezone.utc).isoformat(), **dict(result)}
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


# --------------------------------------------------------------------------
# Human review loop
# --------------------------------------------------------------------------
def _ensure_side_dict(corrected: Dict[str, Any], side: str) -> Dict[str, Any]:
    loc = _locate_document(corrected, side)
    if loc is None:
        corrected[side] = {}
        return corrected[side]
    container, key = loc
    if not isinstance(container[key], dict):
        container[key] = dict(container[key])
    return container[key]


def _ensure_meta_dict(corrected: Dict[str, Any], side: str) -> Dict[str, Any]:
    loc = _locate_meta(corrected, side)
    if loc is None:
        corrected[f"{side}_meta"] = {}
        return corrected[f"{side}_meta"]
    container, key = loc
    if not isinstance(container[key], dict):
        container[key] = dict(container[key])
    return container[key]


def apply_human_correction(
    payload: Mapping[str, Any],
    *,
    si_corrections: Optional[Mapping[str, Any]] = None,
    bl_corrections: Optional[Mapping[str, Any]] = None,
    si_confirmed: Iterable[str] = (),
    bl_confirmed: Iterable[str] = (),
    email_id: Optional[str] = None,
    category: str = "BL_COMPARISON",
    confidence_threshold: float = 0.70,
    reviewer: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Human-review hook for Member D.

    * ``*_corrections``: {field: new_value}; replaces the extracted value.
    * ``*_confirmed``  : [field, ...]; the human confirms the extracted value as
      correct (e.g. a low-confidence reading) without retyping it.

    The payload is deep-copied. Corrected/confirmed values go through the SAME
    verify() logic. A side that a human touched is marked ``human_verified`` so
    that unreadable / wrong-document / missing-attachment gates no longer block
    the case (the person has supplied the values). The returned record contains
    a ``human_review`` audit block (who, why, before -> after).
    """
    corrected = copy.deepcopy(dict(payload))
    changes: List[Dict[str, Any]] = []

    for side, corrections, confirmed in (("si", si_corrections, si_confirmed),
                                         ("bl", bl_corrections, bl_confirmed)):
        corrections = dict(corrections or {})
        confirmed = list(confirmed or [])
        if not corrections and not confirmed:
            continue
        doc = _ensure_side_dict(corrected, side)

        for raw_key, value in corrections.items():
            field = _canonical_field_name(raw_key) or raw_key
            if field not in COMPARE_FIELDS:
                raise ValueError(f"Unsupported correction field: {raw_key!r}")
            before = None
            for existing_key in list(doc):
                if _canonical_field_name(existing_key) == field:
                    if before is None or _is_missing(before):
                        before = _item_value(doc[existing_key])
                    del doc[existing_key]
            doc[field] = value
            changes.append({"side": side.upper(), "field": field, "action": "corrected",
                            "before": before, "after": value})

        for raw_key in confirmed:
            field = _canonical_field_name(raw_key) or raw_key
            if field not in COMPARE_FIELDS:
                raise ValueError(f"Unsupported confirmation field: {raw_key!r}")
            keys = [k for k in doc if _canonical_field_name(k) == field]
            current = doc[keys[0]] if keys else None
            val = _item_value(current)
            if _is_missing(val):
                raise ValueError(f"{side.upper()}.{field} has no value to confirm; supply a correction")
            for k in keys:
                del doc[k]
            src = current.get("source") if isinstance(current, Mapping) else None
            doc[field] = {"value": val, "confidence": 1.0, "source": src, "confirmed_by_human": True}
            changes.append({"side": side.upper(), "field": field, "action": "confirmed",
                            "before": val, "after": val})

        meta = _ensure_meta_dict(corrected, side)
        meta["human_verified"] = True
        meta["readable"] = True
        meta.pop("missing_attachment", None)
        for k in ("status", "ocr_status", "parse_status", "error"):
            meta.pop(k, None)

    result = verify(corrected, email_id=email_id, category=category,
                    confidence_threshold=confidence_threshold)
    result["human_review"] = {
        "reviewer": reviewer, "note": note,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "changes": changes,
        "resolved": result["status"] != "NEEDS_REVIEW",
    }
    return result


__all__ = [
    "COMPARE_FIELDS",
    "FIELD_ALIASES",
    "verify",
    "to_submission_record",
    "merge_into_submission",
    "apply_human_correction",
    "canonicalize_fields",
    "normalize_value",
    "save_evidence",
]
