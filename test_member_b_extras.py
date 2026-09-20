"""
Tests for Member B's optional AI layer + JSON export.   Run:   python test_member_b_extras.py

No API key, no internet needed: a FAKE Claude client returns canned answers, so these tests check
OUR safety logic (blank stays blank, made-up values are rejected, failures never crash), not the model.
"""
import json
import os
from types import SimpleNamespace

from modules import ai_extractor, document_reader
from modules.ai_extractor import _parse_json, enhance
from modules.field_extractor import extract_document, extract_fields
from modules.json_export import doc_to_clean, email_to_clean
from modules.schema import FIELDS


class FakeClient:
    """Looks like anthropic.Anthropic() as far as ai_extractor is concerned."""
    def __init__(self, reply=None, raises=False):
        self.reply, self.raises, self.calls = reply, raises, 0
        self.messages = self

    def create(self, **kwargs):
        self.calls += 1
        if self.raises:
            raise RuntimeError("network down")
        text = self.reply if isinstance(self.reply, str) else json.dumps(self.reply)
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])


os.environ.pop("SDOC_USE_AI", None)          # tests start with AI OFF, like a normal run

FULL_DOC = """BILL OF LADING (DRAFT)
Shipper: ACME LTD
Consignee: FOO GMBH
Notify: FOO GMBH
Load Port: NANTONG, CHINA
Discharge Port: KARACHI, PAKISTAN
Container Count: 3 x 40'HC
Gross Weight: 22,000 KG
"""
UNFAMILIAR = FULL_DOC.replace("Load Port:", "Departure Terminal:")      # a label the rules do not know

# ---- 1. AI is OFF by default: nothing is called, result identical ------------------------------------
fake = FakeClient({"port_of_loading": "SOMEWHERE"})
r = extract_fields(UNFAMILIAR, ai_client=None)
assert r["fields"]["port_of_loading"] is None and r["evidence"]["port_of_loading"]["note"] == "label_not_found"
assert enhance({}, {}, {}, "", "text", client=None)["ai_used"] is False

# ---- 2. rules found everything -> the AI is never called (free + fast) -------------------------------
fake = FakeClient({"document_type": "BILL_OF_LADING"})
extract_fields(FULL_DOC, ai_client=fake)
assert fake.calls == 0

# ---- 3. unfamiliar label: the AI rescues it, flagged 'please verify' ---------------------------------
fake = FakeClient({"document_type": "BILL_OF_LADING", "port_of_loading": "NANTONG, CHINA"})
r = extract_fields(UNFAMILIAR, ai_client=fake)
ev = r["evidence"]["port_of_loading"]
assert fake.calls == 1
assert r["fields"]["port_of_loading"] == "NANTONG, CHINA" and r["keys"]["port_of_loading"] == "NANTONG"
assert ev["note"] == "filled_by_ai" and ev["confidence"] == ai_extractor.CONF_AI_ONLY < 0.75
assert r["fields"]["shipper"] == "ACME LTD" and r["evidence"]["shipper"].get("source") in (None, "rule")   # rules' fields untouched by the AI

# ---- 4. a made-up value (not in the document) is rejected --------------------------------------------
fake = FakeClient({"port_of_loading": "SHANGHAI, CHINA"})
r = extract_fields(UNFAMILIAR, ai_client=fake)
assert r["fields"]["port_of_loading"] is None
assert r["evidence"]["port_of_loading"]["ai_rejected"] == "SHANGHAI, CHINA"

# ---- 5. a BLANK stays blank: the AI must not fill in what the customer left empty ---------------------
BLANK = FULL_DOC.replace("Gross Weight: 22,000 KG", "Gross Weight: N/A")
fake = FakeClient({"gross_weight": "22,000 KG"})
r = extract_fields(BLANK, ai_client=fake)
assert r["fields"]["gross_weight_kg"] is None and r["evidence"]["gross_weight_kg"]["note"] == "blank_value"
assert fake.calls == 0                                    # nothing to rescue -> not even asked

# ---- 6. AI failures never crash and never change the result ------------------------------------------
r = extract_fields(UNFAMILIAR, ai_client=FakeClient(raises=True))
assert r["fields"]["port_of_loading"] is None
r = extract_fields(UNFAMILIAR, ai_client=FakeClient(reply="sorry, I cannot help with that"))
assert r["fields"]["port_of_loading"] is None

# ---- 7. reply parsing is forgiving --------------------------------------------------------------------
assert _parse_json('```json\n{"a": 1}\n```') == {"a": 1}
assert _parse_json('Here you go: {"a": 1} hope that helps') == {"a": 1}
assert _parse_json("no json here") is None and _parse_json("") is None and _parse_json("[1,2]") is None

# ---- 8. json export shape -----------------------------------------------------------------------------
doc = extract_document(FULL_DOC.encode(), "x_BL.txt", expected_type="BL")
clean = doc_to_clean(doc)
assert list(clean["fields"]) == FIELDS and list(clean["keys"]) == FIELDS and list(clean["confidence"]) == FIELDS
assert clean["fields"]["container_count"] == 3 and clean["fields"]["gross_weight_kg"] == 22000
d = clean["details"]["port_of_loading"]
assert d["port_name"] == "NANTONG" and d["country"] == "CHINA" and "locode" not in d   # empty details (no locode) are left out
assert clean["details"]["container_count"]["container_type"] == "40'HC"
json.dumps(clean)                                          # must be plain JSON
assert email_to_clean("email_1", {"category": "spam"}) is None
assert email_to_clean("email_2", {"category": "document_comparison", "status": "human_review",
                                  "review_reason": "missing_attachment"})["si"] is None

# ---- 9. scans (only if the organizers' data + Tesseract are here) ------------------------------------
SCAN = "attachments/email_512_BL.pdf"
if os.path.isfile(SCAN):
    data = open(SCAN, "rb").read()
    TRUTH = {"document_type": "BILL_OF_LADING", "shipper": "APRIL FAR EAST (M) SDN BHD",
             "consignee": "AL GURG STATIONERY LLC", "notify_party": "AL GURG STATIONERY LLC",
             "port_of_loading": "NHAVA SHEVA, INDIA", "port_of_discharge": "TUTICORIN, INDIA",
             "container_count": "6 x 40'HC", "gross_weight": "128,544 KG"}
    real_get_client = ai_extractor._get_client
    try:
        os.environ["SDOC_USE_AI"] = "1"

        # 9a. OCR + AI together: whatever OCR misread, the final KEYS equal the AI's reading
        ai_extractor._get_client = lambda: FakeClient(TRUTH)
        d = extract_document(data, os.path.basename(SCAN), expected_type="BL")
        if d["read_method"] == "ocr" and d["status"] in ("ok", "partial"):
            expect = extract_fields("\n".join(f"{k}: {v}" for k, v in {
                "Shipper": TRUTH["shipper"], "Consignee": TRUTH["consignee"], "Notify": TRUTH["notify_party"],
                "Port of Loading": TRUTH["port_of_loading"], "Port of Discharge": TRUTH["port_of_discharge"],
                "Containers": TRUTH["container_count"], "Gross Weight": TRUTH["gross_weight"]}.items()))["keys"]
            assert d["keys"] == expect, (d["keys"], expect)
            assert all(d["evidence"][f]["confidence"] in (0.95, ai_extractor.CONF_AI_ONLY) for f in FIELDS)
            assert d["evidence"]["consignee"].get("ocr_value") or d["evidence"]["consignee"]["note"] == "ocr_and_ai_agree"

        # 9b. Tesseract missing: with AI on the scan is still read; with AI off it is 'unreadable'
        real_ocr = document_reader._run_ocr
        document_reader._run_ocr = lambda images: document_reader._fail("ocr", "ocr_unavailable", "no tesseract")
        ai_extractor._get_client = lambda: FakeClient(TRUTH)
        d = extract_document(data, os.path.basename(SCAN), expected_type="BL")
        assert d["status"] == "ok" and d["keys"]["gross_weight_kg"] == 128544, d["status"]
        assert all(d["evidence"][f]["confidence"] == ai_extractor.CONF_AI_ONLY for f in FIELDS)   # AI-only -> verify
        # 9c. ...and then the AI is the only one who can see the title: an invoice in the BL slot is caught
        ai_extractor._get_client = lambda: FakeClient({"document_type": "COMMERCIAL_INVOICE"})
        d = extract_document(data, os.path.basename(SCAN), expected_type="BL")
        assert d["status"] == "wrong_doc_type" and d["review_reason"] == "wrong_doc_type", d["status"]
        # 9d. AI switched off + no Tesseract = 'unreadable' (goes to a human), never a guess
        os.environ["SDOC_USE_AI"] = "0"
        d = extract_document(data, os.path.basename(SCAN), expected_type="BL")
        assert d["status"] == "unreadable" and d["review_reason"] == "unreadable"
        document_reader._run_ocr = real_ocr
    finally:
        ai_extractor._get_client = real_get_client
        os.environ.pop("SDOC_USE_AI", None)
    print("scan checks passed")
else:
    print("(no attachments/ folder here - skipped the scan checks)")

print("all Member B extra checks passed")

# ---------------------------------------------------------------------------
# 10. Advanced quality engine
# ---------------------------------------------------------------------------

from modules.advanced_quality import evaluate

QUALITY_DOC = """BILL OF LADING
Shipper: ACME LTD
Consignee: FOO GMBH
Notify Party: FOO GMBH
Port of Loading: NANTONG, CHINA
Port of Discharge: KARACHI, PAKISTAN
Container Count: 3 x 40'HC
Gross Weight: 22,000 KG
"""

qdoc = extract_fields(
    QUALITY_DOC,
    method="text",
)

quality = qdoc["quality"]

assert quality["validation_status"] in (
    "PASS",
    "VERIFY",
)

assert quality["quality_score"] > 0.70

assert "shipper" in quality["field_quality"]

assert "gross_weight_kg" in quality["provenance"]

# Weight sanity check
bad_fields = {
    "container_count": 3,
    "gross_weight_kg": 22000,
}

bad_evidence = {
    field: {
        "confidence": 0.98,
        "note": None,
        "source": "rule",
    }
    for field in FIELDS
}

bad_evidence["gross_weight_kg"]["raw_label"] = "Net Weight"

quality = evaluate(
    bad_fields,
    bad_evidence,
    "text",
)

assert any(
    flag.startswith(("gross_weight_from_", "gross_weight_kg:gross_weight_from_")) and flag.endswith("_label")
    for flag in quality["flags"]
)        

print("advanced quality checks passed")