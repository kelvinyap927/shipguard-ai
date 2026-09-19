"""
modules/normalizer.py  --  make "the same thing" look the same.

The extractor finds raw strings ("131,058 KG", "NANTONG, CHINA (CNNTG)").
These helpers turn them into clean values so the comparison step (Member C)
does not report false alarms caused by formatting.

    parse_weight_kg("131,058 KG")            -> 131058
    parse_container_count("6 x 40'HC")       -> (6, "40'HC")
    parse_port("NANTONG, CHINA (CNNTG)")     -> {"display": "NANTONG, CHINA", "name": "NANTONG", ...}
    party_key("Ball & Doggett Pty. Ltd.")    -> "BALL AND DOGGETT PTY LTD"
"""
import re
from difflib import SequenceMatcher

from modules.schema import PARTY_FIELDS, PORT_FIELDS

CJK = re.compile(r"[\u3000-\u303f\u3400-\u9fff\uff00-\uffef]")

# Values that mean "the customer left this empty".
BLANK_WORDS = {"", "NA", "N/A", "TBA", "TBC", "TBD", "NIL", "NONE", "NULL", "UNKNOWN",
               "MT", "MTS", "KG", "KGS", "PENDING", "TOBEADVISED"}


def clean(s) -> str:
    """Collapse whitespace, drop Chinese text, trim stray separators (keeps a final '.', e.g. 'PTE. LTD.')."""
    if s is None:
        return ""
    s = CJK.sub("", str(s))
    s = re.sub(r"\s+", " ", s).strip()
    return s.strip(" ;,|")


def is_blank(s) -> bool:
    """True for '', 'N/A', 'TBA', '____MT', '-' ..."""
    if s is None:
        return True
    squeezed = re.sub(r"[\s_\-.]+", "", str(s)).upper()
    return squeezed in BLANK_WORDS


# ------------------------------------------------------------------- parties
def party_key(name: str) -> str:
    """Comparison key for a company name: upper-case, '&'->AND, no punctuation."""
    s = clean(name).upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------- ports
# Used to drop a trailing country when a scan/OCR lost the comma
# ("NHAVA SHEVA INDIA" -> "NHAVA SHEVA").  Add more if you meet them.
COUNTRIES = {
    "INDIA", "CHINA", "MALAYSIA", "INDONESIA", "SINGAPORE", "PERU", "TURKEY", "GUINEA",
    "POLAND", "NIGERIA", "LITHUANIA", "US", "USA", "SLOVENIA", "MYANMAR", "VIETNAM",
    "AUSTRALIA", "ISRAEL", "SOUTH KOREA", "KOREA", "KENYA", "PAKISTAN", "CHILE", "UAE",
    "JORDAN", "PHILIPPINES", "UNITED ARAB EMIRATES", "THAILAND", "JAPAN", "GERMANY",
}
_LOCODE = re.compile(r"\(\s*([A-Z]{5})\s*\)")


def parse_port(raw: str) -> dict:
    """
    'PORT KLANG (WESTPORT), MALAYSIA (MYPKG)' ->
        display : 'PORT KLANG (WESTPORT), MALAYSIA'   (nice to show a human)
        name    : 'PORT KLANG'                         (what to compare)
        country : 'MALAYSIA'
        locode  : 'MYPKG'
        key     : 'PORT KLANG'                         (upper, alnum only)
    """
    s = clean(raw).upper()
    m = _LOCODE.search(s)
    locode = m.group(1) if m else None
    s = _LOCODE.sub("", s)
    s = re.sub(r"\.(?=\s|$)", "", s).strip(" ,")      # OCR often turns ',' into '.'
    display = re.sub(r"\s+", " ", s)

    no_paren = re.sub(r"\([^)]*\)", "", s)
    parts = [p.strip() for p in no_paren.split(",") if p.strip()]
    name = parts[0] if parts else ""
    country = parts[-1] if len(parts) > 1 else None

    if country is None:                       # OCR may have lost the comma
        for c in sorted(COUNTRIES, key=len, reverse=True):
            if name.endswith(" " + c) and len(name) > len(c) + 2:
                country, name = c, name[: -len(c)].strip()
                break
    key = re.sub(r"[^A-Z0-9/]", "", name)
    return {"display": display, "name": name, "country": country, "locode": locode, "key": key}


# ---------------------------------------------------------------- containers
def parse_container_count(raw: str):
    """
    '6 x 40'HC' -> (6, "40'HC")     '1X20'GP' -> (1, "20'GP")     '12' -> (12, None)
    Returns (None, None) if no count can be read.
    """
    s = clean(raw)
    m = re.match(r"^(\d{1,4})\s*[xX\u00d7]\s*(.*)$", s)
    if m:
        ctype = re.sub(r"\s+", "", m.group(2)).upper().replace("'X", "'") or None
        return int(m.group(1)), ctype
    m = re.match(r"^(\d{1,4})\b", s)
    if m:
        return int(m.group(1)), None
    return None, None


# -------------------------------------------------------------------- weight
_THOUSANDS = re.compile(r"^\d{1,3}([.,]\d{3})+$")


def parse_weight_kg(raw):
    """
    '131,058 KG' -> 131058      '128.544 KG' (OCR turned , into .) -> 128544
    '21,707.5'   -> 21707.5     '20 MT' -> 20000       341715 (xlsx number) -> 341715
    Returns None if unreadable.
    """
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw) if float(raw).is_integer() else float(raw)

    s = clean(raw).upper()
    factor = 1
    if re.search(r"\b(MT|MTS|TON|TONS|TONNE|TONNES)\b", s):
        factor = 1000
    m = re.search(r"\d[\d.,]*", s)
    if not m:
        return None
    num = m.group(0).rstrip(".,")

    if _THOUSANDS.match(num):                    # 131,058  or OCR'd 131.058
        num = re.sub(r"[.,]", "", num)
    elif "," in num and "." in num:              # 21,707.50
        num = num.replace(",", "") if num.rfind(".") > num.rfind(",") else num.replace(".", "").replace(",", ".")
    elif "," in num:                             # 21707,5  (decimal comma)
        num = num.replace(",", ".")
    try:
        val = float(num) * factor
    except ValueError:
        return None
    return int(val) if val.is_integer() else round(val, 3)


# ---------------------------------------------------------------- similarity
def similar(a: str, b: str) -> float:
    """0..1 text similarity. Useful for telling an OCR typo from a real change."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, re.sub(r"\s+", "", a.upper()), re.sub(r"\s+", "", b.upper())).ratio()


# ------------------------------------------------- one field: raw lines -> value
def normalize_value(field: str, lines: list):
    """
    The ONE place that turns the raw text of a field into a clean value.
    Used by the rule-based extractor AND by the AI extractor, so both behave identically.

        lines = the cleaned text lines belonging to the field (first line = the value)
        returns (value, key, extra_evidence, note)

        value  : what a human reads            "NANTONG, CHINA"     131058     6
        key    : what the comparison uses      "NANTONG"            131058     6
        note   : None | "blank_value" | "unparseable_value"
    """
    extra = {}
    if not lines or is_blank(lines[0]):
        return None, None, extra, "blank_value"          # label present, customer left it empty
    value = key = None
    if field in PARTY_FIELDS:
        value = lines[0]                                 # company NAME = first line
        key = party_key(value)
        extra["address"] = "; ".join(lines[1:]) or None
    elif field in PORT_FIELDS:
        p = parse_port(" ".join(lines))
        value, key = p["display"], p["key"]
        extra.update(port_name=p["name"], country=p["country"], locode=p["locode"])
    elif field == "container_count":
        n, ctype = parse_container_count(lines[0])
        value = key = n
        extra["container_type"] = ctype
    elif field == "gross_weight_kg":
        value = parse_weight_kg(lines[0])
        key = value
    return value, key, extra, (None if value is not None else "unparseable_value")