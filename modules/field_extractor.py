"""
modules/field_extractor.py  --  plain text  ->  the 7 shipment fields.

How it works (rule based, no AI needed, fully explainable):

  1. Go line by line. For every line decide: "is this the START of a field?"
     by matching the label against modules/schema.py LABEL_ALIASES.
        "Load Port: NANTONG"      -> port_of_loading   (colon style)
        "Shipper     ACME LTD"    -> shipper           (column style, from PDFs)
        "Consignee (Non-Negotiable) ACME"  -> consignee (label + value, one space)
  2. Lines indented under a label belong to it (multi-line addresses).
  3. Clean each raw value with normalizer.py.
  4. Attach evidence (raw label/value + confidence) so a human can verify.

Main entry point:   extract_document(data, filename, expected_type) -> dict
"""
import re
import textwrap
from difflib import SequenceMatcher, get_close_matches

from modules.normalizer import clean, normalize_value, parse_weight_kg
from modules.ai_extractor import ai_enabled, enhance      # optional AI layer (off by default)
from modules.document_reader import read_document
from modules.schema import FIELDS, IGNORE, LABEL_ALIASES, PARTY_FIELDS, PORT_FIELDS, TITLE_RULES

REVIEW_CONFIDENCE = 0.75      # below this a value is flagged "please verify"
OCR_MAX_CONFIDENCE = 0.70     # a value read ONLY by OCR is never trusted alone (Tesseract's own score is not
                              # reliable: the scans in the dataset scored ~0.78 and still had misread letters).
                              # The optional AI layer raises it to 0.95 when it reads the same value.

_CJK = re.compile(r"[\u3000-\u303f\u3400-\u9fff\uff00-\uffef]")


# ------------------------------------------------------------ label matching
def _compact(label: str) -> str:
    """'Gross Weight毛重(KGS)' -> 'grossweight'  (ignore case, spaces, punctuation, brackets, Chinese)."""
    s = _CJK.sub("", label)
    s = re.sub(r"\([^)]*\)", "", s)
    return re.sub(r"[^a-z0-9]", "", s.lower())


ALIAS_TO_FIELD = {}
for _field, _aliases in LABEL_ALIASES.items():
    for _a in _aliases:
        ALIAS_TO_FIELD[_compact(_a)] = _field


def lookup_label(text: str, cutoff=None):
    """
    Return (field, score) or None.
    score = 1.0 for an exact label; otherwise the similarity (0..1) of a typo'd label.
    cutoff=None -> exact matches only;  cutoff=0.88 -> also accept near-exact labels.
    """
    key = _compact(text)
    if not key:
        return None
    if key in ALIAS_TO_FIELD:
        return ALIAS_TO_FIELD[key], 1.0
    if cutoff and len(key) > 4:
        hit = get_close_matches(key, ALIAS_TO_FIELD.keys(), n=1, cutoff=cutoff)
        if hit:
            return ALIAS_TO_FIELD[hit[0]], round(SequenceMatcher(None, key, hit[0]).ratio(), 3)
    return None


def parse_label_line(line: str, ocr: bool = False):
    """
    If `line` starts a field, return (field, raw_label, rest_of_line, match_score).
    Otherwise None.

    Fuzzy matching is what rescues garbled labels:
      * normal files : 'TOTAL Gross Weightnn(KGS)'  (a PDF glyph artifact)  -> accepted at 0.88
      * OCR scans    : 'Portof Leading', 'Grees Weight'                     -> accepted at 0.75
    """
    cutoff = 0.75 if ocr else 0.88
    s = line.strip()

    # style 1 -- "Label: value"
    if ":" in s:
        label, _, rest = s.partition(":")
        if len(label) <= 70:
            hit = lookup_label(label, cutoff)
            if hit:
                return hit[0], label.strip(), rest.strip(), hit[1]

    # style 2 -- "Label      value"  (two or more spaces = a column gap)
    parts = re.split(r"\s{2,}", s, maxsplit=1)
    if len(parts) == 2:
        hit = lookup_label(parts[0], cutoff)
        if hit:
            return hit[0], parts[0].strip(), parts[1].strip(), hit[1]

    # style 3 -- "Label value" with single spaces.
    # Try the label being 1..N words long and keep the best-scoring one
    # (ties -> the longer one, so "Consignee (Non-Negotiable)" swallows its bracket).
    # Typos are only tolerated for OCR text here, otherwise value words could be mistaken for label words.
    tokens = s.split()
    best = None
    for k in range(1, min(5 if ocr else 8, len(tokens)) + 1):
        cand = " ".join(tokens[:k]).rstrip(".,;")
        hit = lookup_label(cand, 0.75 if ocr else None)
        if hit and (best is None or hit[1] >= best[1]):
            best = (hit[0], hit[1], k, cand)
    if best:
        field, score, k, cand = best
        return field, cand, " ".join(tokens[k:]), score
    return None


# ------------------------------------------------------------- doc type
def detect_doc_type(text: str):
    """
    Look at the title area (first 6 lines). Returns 'SI', 'BL', 'OTHER:<what>' or None.
    Spaces/punctuation are ignored so OCR splits like 'BILLOF LADING' still match.
    """
    head = _compact("\n".join([l for l in text.splitlines() if l.strip()][:6]))
    for doc_type, phrases in TITLE_RULES:
        if any(_compact(p) in head for p in phrases):
            return doc_type
    return None


# ---------------------------------------------------- collect raw field blocks
def collect_blocks(text: str, ocr: bool = False) -> dict:
    """text -> {field: {'label':..., 'lines':[...], 'quality':...}}   (first occurrence wins)"""
    text = textwrap.dedent("\n".join(l.rstrip() for l in text.splitlines()))
    blocks, current = {}, None
    for raw in text.splitlines():
        if not raw.strip():
            current = None
            continue
        indent = len(raw) - len(raw.lstrip())
        if indent > 0 and current is not None:       # continuation (address line)
            blocks[current]["lines"].append(raw.strip())
            continue
        hit = parse_label_line(raw, ocr)
        if not hit:
            current = None                           # some other label we don't need
            continue
        field, label, rest, quality = hit
        if field == IGNORE or field in blocks:
            current = None
            continue
        blocks[field] = {"label": label, "lines": [rest] if rest else [], "quality": quality}
        current = field
    return blocks


# ----------------------------------------------- fallbacks when a label is absent
_CONTAINER_ROW = re.compile(r"^\s*([A-Z]{4}\d{7})\b(.*)$", re.M)


def _rows_fallback(text: str):
    """Count container-number rows and sum their weights (only used if labels are absent)."""
    rows = _CONTAINER_ROW.findall(text)
    if not rows:
        return None, None
    weights = []
    for _, rest in rows:
        m = re.search(r"(\d[\d,]*)\s*$", rest.strip())
        if m:
            weights.append(parse_weight_kg(m.group(1)))
    total = sum(weights) if weights and all(w is not None for w in weights) else None
    return len(rows), total


# ------------------------------------------------------------- main function
def extract_fields(text: str, method: str = "text", ocr_conf=None, images=None, ai_client=None) -> dict:
    """
    text -> {'fields': {...}, 'keys': {...}, 'evidence': {...}, 'ai_doc_type': ...}
    Every one of the 7 fields is always present; missing ones are None.

    images / ai_client are only used by the OPTIONAL AI layer (modules/ai_extractor.py).
    """
    is_ocr = method == "ocr"
    blocks = collect_blocks(text, is_ocr)

    base_conf = {"text": 0.98, "pdf_text": 0.95, "docx": 0.95, "xlsx": 0.95}.get(method)
    if method == "ocr":
        base_conf = min(OCR_MAX_CONFIDENCE, ocr_conf if ocr_conf else 0.6)

    fields, keys, evidence = {}, {}, {}

    for f in FIELDS:
        block = blocks.get(f)
        ev = {"raw_label": None, "raw_value": None, "confidence": 0.0, "note": None}
        value, key = None, None

        if block is None:
            ev["note"] = "label_not_found"
        else:
            lines = [l for l in (clean(x) for x in block["lines"]) if l]
            raw_value = " | ".join(lines)
            ev.update(raw_label=block["label"], raw_value=raw_value)
            conf = base_conf * block["quality"]

            value, key, extra, note = normalize_value(f, lines)
            ev.update(extra)
            ev["note"] = note
            if note:                                   # blank_value / unparseable_value
                conf = 0.0
            ev["confidence"] = round(conf, 3)

        fields[f], keys[f], evidence[f] = value, key, ev

    # ---- fallbacks: ONLY when the label was never found (never when it was left blank)
    if evidence["container_count"]["note"] == "label_not_found" or \
       evidence["gross_weight_kg"]["note"] == "label_not_found":
        n_rows, total = _rows_fallback(text)
        if fields["container_count"] is None and evidence["container_count"]["note"] == "label_not_found" and n_rows:
            fields["container_count"] = keys["container_count"] = n_rows
            evidence["container_count"].update(confidence=0.5, note="derived_from_container_rows")
        if fields["gross_weight_kg"] is None and evidence["gross_weight_kg"]["note"] == "label_not_found" and total:
            fields["gross_weight_kg"] = keys["gross_weight_kg"] = total
            evidence["gross_weight_kg"].update(confidence=0.5, note="derived_from_container_rows")

    # ---- optional AI layer: re-reads scans, rescues unfamiliar labels (does nothing unless switched on)
    ai = enhance(fields, keys, evidence, text, method, images, ai_client)

    # ---- sanity checks (catch parser mistakes and typos)
    n = fields["container_count"]
    if n is not None and not (1 <= n <= 500):
        evidence["container_count"]["note"] = "implausible_value"
        evidence["container_count"]["confidence"] = min(evidence["container_count"]["confidence"], 0.4)
    w = fields["gross_weight_kg"]
    if w is not None and not (100 <= w <= 2_000_000):
        evidence["gross_weight_kg"]["note"] = "implausible_value"
        evidence["gross_weight_kg"]["confidence"] = min(evidence["gross_weight_kg"]["confidence"], 0.4)

    return {"fields": fields, "keys": keys, "evidence": evidence, "ai_doc_type": ai["doc_type"]}


# ------------------------------------------------- one file -> one result dict
def _wrong_type(result: dict, dt, expected_type) -> bool:
    """If the document is not the SI/BL we expected, fill in `result` and return True."""
    if dt and dt.startswith("OTHER"):
        result.update(status="wrong_doc_type", review_reason="wrong_doc_type")
        result["review_notes"].append(f"document looks like {dt.split(':', 1)[1].replace('_', ' ').lower()}, "
                                      f"expected {expected_type or 'SI/BL'}")
        return True
    if dt and expected_type and dt != expected_type:
        result.update(status="wrong_doc_type", review_reason="wrong_doc_type")
        result["review_notes"].append(f"file is named {expected_type} but its title says {dt}")
        return True
    return False


def extract_document(data: bytes, filename: str, expected_type: str = None) -> dict:
    """
    Read + extract one attachment. NEVER raises; problems are reported in the result.

    status:  ok | partial | unreadable | wrong_doc_type
    review_reason: None | unreadable | wrong_doc_type | missing_value   (same words as the hackathon README)
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
        "fields": {f: None for f in FIELDS},
        "keys": {f: None for f in FIELDS},
        "evidence": {},
    }

    rd = read_document(data, filename)
    result["read_method"] = rd.method
    result["ocr_confidence"] = rd.ocr_confidence
    result["review_notes"].extend(rd.warnings)

    # A scan that Tesseract could not read (or Tesseract is not installed) can still be read by AI vision.
    vision_only = (not rd.ok and rd.problem in ("ocr_unavailable", "empty_document")
                   and bool(rd.images) and ai_enabled())
    if vision_only:
        rd.method = result["read_method"] = "ocr"
        result["review_notes"].append(f"OCR failed ({rd.problem}); the scan is being read by AI vision only")
    elif not rd.ok:
        result.update(status="unreadable", review_reason="unreadable")
        result["review_notes"].append(f"{rd.problem}: {rd.detail}")
        return result

    result["detected_type"] = detect_doc_type(rd.text)
    if _wrong_type(result, result["detected_type"], expected_type):
        return result

    ext = extract_fields(rd.text, rd.method, rd.ocr_confidence, images=rd.images)
    if result["detected_type"] is None and ext["ai_doc_type"]:      # scans whose title OCR could not read
        result["detected_type"] = ext["ai_doc_type"]
        result["review_notes"].append("document type was read by AI vision")
        if _wrong_type(result, result["detected_type"], expected_type):
            return result
    result["fields"], result["keys"], result["evidence"] = ext["fields"], ext["keys"], ext["evidence"]

    result["missing_fields"] = [f for f in FIELDS if result["fields"][f] is None]
    result["low_confidence_fields"] = [f for f in FIELDS
                                       if result["fields"][f] is not None
                                       and result["evidence"][f]["confidence"] < REVIEW_CONFIDENCE]
    if result["missing_fields"]:
        result.update(status="partial", review_reason="missing_value")
        result["review_notes"].append("missing: " + ", ".join(result["missing_fields"]))
    if result["low_confidence_fields"]:
        result["review_notes"].append("low confidence: " + ", ".join(result["low_confidence_fields"]))
    return result