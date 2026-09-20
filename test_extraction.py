"""
Quick self-checks.  Run:   python test_extraction.py
If you change the extractor and something breaks, this tells you immediately.
"""
from modules.field_extractor import extract_fields, detect_doc_type
from modules.normalizer import is_blank, parse_container_count, parse_port, parse_weight_kg, party_key

# ---- normalisers ----------------------------------------------------------
assert parse_weight_kg("131,058 KG") == 131058
assert parse_weight_kg("128.544 KG") == 128544          # OCR turned ',' into '.'
assert parse_weight_kg("21,707.5") == 21707.5
assert parse_weight_kg("20 MT") == 20000
assert parse_weight_kg(341715) == 341715                # number straight from Excel
assert parse_weight_kg("N/A") is None

assert parse_container_count("6 x 40'HC") == (6, "40'HC")
assert parse_container_count("1X20'GP") == (1, "20'GP")
assert parse_container_count("10 x 20'FCL")[0] == 10

p = parse_port("PORT KLANG (WESTPORT), MALAYSIA (MYPKG)")
assert p["name"] == "PORT KLANG" and p["locode"] == "MYPKG" and p["country"] == "MALAYSIA"
assert parse_port("NHAVA SHEVA INDIA.")["name"] == "NHAVA SHEVA"       # OCR lost the comma
assert parse_port("NANTONG, CHINA (CNNTG)")["key"] == parse_port("NANTONG, CHINA")["key"]

assert party_key("Ball & Doggett Pty. Ltd.") == "BALL AND DOGGETT PTY LTD"
for blank in ("", "N/A", "TBA", "____MT", "-", None):
    assert is_blank(blank), blank
assert not is_blank("SINGAPORE")

# ---- extractor: SI and BL use different labels for the same fields --------
SI = """SHIPPING INSTRUCTION
Shipper: ACME LTD
  1 MAIN ROAD; SINGAPORE
Consignee (Non-Negotiable): FOO GMBH
Notify: FOO GMBH
Port of Loading (POL): NANTONG, CHINA (CNNTG)
POD: KARACHI, PAKISTAN
Total Containers: 3 x 40'HC
Gross Wt (kgs): 22,000 KG
NET WEIGHT: 21,000 KG
"""
BL = """BILL OF LADING (DRAFT)
SHIPPER: ACME LTD
To the Order of: FOO GMBH
Notify Party/Intermediate Consignee: FOO GMBH
Load Port: NANTONG, CHINA
Discharge Port: KARACHI, PAKISTAN
Container Count: 4 x 40'HC
Gross Weight毛重(KGS): 22,000 KG
"""
si, bl = extract_fields(SI), extract_fields(BL)
assert detect_doc_type(SI) == "SI" and detect_doc_type(BL) == "BL"
assert si["fields"]["shipper"] == "ACME LTD"
assert si["evidence"]["shipper"]["address"] == "1 MAIN ROAD; SINGAPORE"
assert si["fields"]["gross_weight_kg"] == 22000          # NET weight must NOT be used
diff = [f for f in si["keys"] if si["keys"][f] != bl["keys"][f]]
assert diff == ["container_count"], diff                # the example from the hackathon brief
assert (si["fields"]["container_count"], bl["fields"]["container_count"]) == (3, 4)

# ---- blank value is reported, never guessed -------------------------------
blank = extract_fields("Shipper: ACME\nGross Weight毛重(KGS): N/A\nPOD: TBA\n")
assert blank["fields"]["gross_weight_kg"] is None
assert blank["evidence"]["gross_weight_kg"]["note"] == "blank_value"
assert blank["evidence"]["port_of_discharge"]["note"] == "blank_value"
assert blank["evidence"]["consignee"]["note"] == "label_not_found"

# ---- column-style text (as produced from PDFs) ----------------------------
COL = """BILL OF LADING (DRAFT)
Shipper                        ACME LTD
                               1 MAIN ROAD
Consignee (Non-Negotiable) FOO GMBH
Load Port                      NANTONG, CHINA
No. of Containers: 6 x 40'HC
TOTAL Gross Weightnn(KGS): 131,322 KG
"""
col = extract_fields(COL)
assert col["fields"]["shipper"] == "ACME LTD"
assert col["fields"]["consignee"] == "FOO GMBH"
assert col["fields"]["port_of_loading"] == "NANTONG, CHINA"
assert col["fields"]["gross_weight_kg"] == 131322        # survives the 'nn' glyph artifact

# ---- real data (skipped if the organizers' inbox/ + attachments/ folders are not in this folder) ----
# Tests the reading + extraction directly (document_job -> run_extraction), so the result does not
# depend on the email classifier or on an API key.
import os
if os.path.isdir("inbox") and os.path.isdir("attachments"):
    from modules.document_job import build_document_job
    from modules.extraction_job import run_extraction
    from modules.inbox import load_inbox

    emails = {e["email_id"]: e for e in load_inbox()}

    def run(eid):
        job = build_document_job(emails[eid])
        if job["status"] == "human_review":                   # e.g. an attachment is missing
            return {"status": "human_review", "review_reason": job.get("review_reason")}
        return run_extraction(job)

    r = run("email_004")                                      # plain text pair, consignee differs
    assert r["status"] == "extracted", (r["status"], r["review_reason"])
    diff = [f for f in r["si"]["keys"] if r["si"]["keys"][f] != r["bl"]["keys"][f]]
    assert diff == ["consignee", "notify_party"], diff

    checks = {                                                # edge cases from the organizers' data
        "email_505": "wrong_doc_type",                        # BL slot holds a certificate of origin
        "email_507": "missing_attachment",                    # only the SI is attached
        "email_511": "unreadable",                            # corrupt PDF
        "email_516": "missing_value",                         # SI weight left blank
    }
    for eid, reason in checks.items():
        r = run(eid)
        assert r["status"] == "human_review" and r["review_reason"] == reason, (eid, r["status"], r.get("review_reason"))

    # every ordinary SI/BL pair (emails 1-500) must extract cleanly with all 7 fields.
    # This catches a label that was dropped from schema.py: the pair would silently go to human review.
    not_clean = []
    for eid in sorted(emails):
        if int(eid.split("_")[1]) > 500 or len(emails[eid]["attachments"]) != 2:
            continue
        r = run(eid)
        if r["status"] != "extracted":
            not_clean.append((eid, r["review_reason"], (r.get("review_notes") or [""])[0][:60]))
    assert not not_clean, f"{len(not_clean)} ordinary pairs were not extracted, e.g. {not_clean[:3]}"

    r = run("email_055")                                      # docx BL + xlsx SI
    assert r["status"] == "extracted", r["status"]
    print("real-data checks passed")
else:
    print("(no inbox/ + attachments/ folder here - skipped the real-data checks)")

print("all checks passed")