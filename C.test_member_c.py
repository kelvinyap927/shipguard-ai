"""
Member C unit / adversarial tests (revision 2).
Run:  python3 test_member_c.py
Contains the original tests (unchanged) plus one regression test per defect
found in the review, plus the cases the old README claimed but did not test.
"""
import json
import math

import member_c_verifier as mc
from member_c_verifier import (
    COMPARE_FIELDS, verify, to_submission_record, apply_human_correction,
    normalize_value, canonicalize_fields,
)


def case(name, payload, expected_status, expected_fields=None, expected_reason=None):
    r = verify(payload, email_id=name)
    assert r["status"] == expected_status, (name, r["status"], r.get("message"))
    if expected_fields is not None:
        assert set(r["defect_fields"]) == set(expected_fields), (name, r)
    if expected_reason is not None:
        assert r["review_reason"] == expected_reason, (name, r["review_reason"], r.get("message"))
    return r


def seven(**over):
    d = {
        "shipper": "ABC SHIPPING SDN BHD", "consignee": "XYZ TRADING PTE LTD",
        "notify_party": "XYZ TRADING PTE LTD", "port_of_loading": "PORT KLANG (MYPKG)",
        "port_of_discharge": "SINGAPORE (SGSIN)", "container_count": "3 x 40'HC",
        "gross_weight_kg": "22,000 KG",
    }
    d.update(over)
    return d


def pair(si=None, bl=None, **extra):
    return {"si": seven(**(si or {})), "bl": seven(**(bl or {})), **extra}


# --------------------------------------------------------------------------
def original_tests():
    base = {
        "si": {
            "Shipper": "ABC SHIPPING SDN BHD", "Consignee": "XYZ TRADING PTE LTD",
            "Notify Party": "XYZ TRADING PTE LTD",
            "Port of Loading": "PORT KLANG (WESTPORT), MALAYSIA (MYPKG)",
            "Gross Weight (KG)": "22,000 KG", "Container Count": "3 x 40'HC",
            "Port of Discharge": "SINGAPORE",
        },
        "bl": {
            "Shipper/Exporter": "ABC SHIPPING SDN BHD", "To the Order of": "XYZ TRADING PTE LTD",
            "Notify": "XYZ TRADING PTE LTD", "Load Port": "PORT KLANG (WESTPORT), MALAYSIA",
            "Gross Wt (kgs)": "22000 kg", "No. of Containers": "3 x 40'HC",
            "POD": "SINGAPORE (SGSIN)",
        },
    }
    case("match", base, "OK", [])
    assert case("container", {**base, "bl": {**base["bl"], "No. of Containers": "4 x 40'HC"}},
                "MISMATCH", ["container_count"])["has_defect"]
    case("weight", {**base, "bl": {**base["bl"], "Gross Wt (kgs)": "22 tonnes"}}, "OK", [])
    case("port", {**base, "bl": {**base["bl"], "POD": "PORT KLANG"}}, "MISMATCH", ["port_of_discharge"])
    case("missing", {**base, "si": {**base["si"], "Gross Weight (KG)": "N/A"}},
         "NEEDS_REVIEW", [], "missing_value")
    case("missing_bl", {"si": base["si"], "bl": {}, "attachments_expected": True},
         "NEEDS_REVIEW", [], "missing_attachment")
    case("wrong_type", {**base, "bl_meta": {"document_type": "commercial_invoice"}},
         "NEEDS_REVIEW", [], "wrong_doc_type")
    case("unreadable", {**base, "bl_meta": {"readable": False}}, "NEEDS_REVIEW", [], "unreadable")
    low = {**base, "si": {**base["si"], "Gross Weight (KG)": {"value": "22000 kg", "confidence": 0.4}}}
    case("low_conf", low, "NEEDS_REVIEW", [], "unreadable")

    bad = {**base, "bl": {**base["bl"], "No. of Containers": "4"}}
    r = case("correction", bad, "MISMATCH", ["container_count"])
    assert apply_human_correction(bad, bl_corrections={"container_count": "3"},
                                  email_id="correction")["status"] == "OK"

    sub = to_submission_record(r)
    assert set(sub) == {"category", "status", "review_reason", "defect_fields", "has_defect"}
    assert sub["defect_fields"] == ["container_count"]

    for alias, canonical in [
        ("Port of Loading (POL)", "port_of_loading"), ("Load Port", "port_of_loading"),
        ("Discharge Port", "port_of_discharge"), ("POD", "port_of_discharge"),
        ("Gross Weight\u6bdb\u91cd(KGS)", "gross_weight_kg"),
        ("No. of Containers or Packages", "container_count"),
        ("Consignee (Non-Negotiable)", "consignee"),
    ]:
        assert canonical in canonicalize_fields({alias: "x"})


# --------------------------------------------------------------------------
# things the README claimed to test but the old test-suite did not
# --------------------------------------------------------------------------
def readme_claims():
    case("all-seven", pair(bl=dict(shipper="OTHER SHIPPER", consignee="OTHER CONSIGNEE",
                                   notify_party="OTHER NOTIFY", port_of_loading="NANTONG",
                                   port_of_discharge="BUSAN", container_count="9",
                                   gross_weight_kg="1 KG")),
         "MISMATCH", list(COMPARE_FIELDS))
    case("case/space", pair(bl=dict(shipper="  abc   shipping sdn bhd ")), "OK", [])
    case("port-code", pair(bl=dict(port_of_loading="PORT KLANG", port_of_discharge="SINGAPORE")), "OK", [])
    # conflicting duplicate aliases -> human review, not mismatch
    conflicting = {"si": {**seven(), "Gross Weight": "22,000 KG", "Gross Wt (kgs)": "23,000 KG"},
                   "bl": seven()}
    del conflicting["si"]["gross_weight_kg"]
    case("dup-conflict", conflicting, "NEEDS_REVIEW", [], "missing_value")
    # harmless duplicates (same information) -> no false review
    same = {"si": {**seven(), "Gross Weight": {"value": "22,000 KG", "confidence": 0.9},
                   "Gross Wt (kgs)": {"value": "22 MT", "confidence": 0.99}}, "bl": seven()}
    del same["si"]["gross_weight_kg"]
    case("dup-same", same, "OK", [])


# --------------------------------------------------------------------------
# regression tests for the defects found in the review
# --------------------------------------------------------------------------
def regressions():
    # R1 xlsx "NAME | ADDR; ADDR"  vs  docx/pdf "NAME\nADDR\nADDR"
    si = {"shipper": "APRIL FINE PAPER TRADING | ON BEHALF OF VITAL SOLUTIONS PTE LTD; 77 ROBINSON ROAD, #21-01; SINGAPORE 068896"}
    bl = {"shipper": "APRIL FINE PAPER TRADING\nON BEHALF OF VITAL SOLUTIONS PTE LTD\n77 ROBINSON ROAD, #21-01\nSINGAPORE 068896"}
    case("R1-pipe-address", pair(si=si, bl=bl), "OK", [])
    case("R1b-real-shipper-diff", pair(si=si, bl={"shipper": "APRIL FINE PAPER TRADING (MIDDLE EAST) FZE\nDUBAI"}),
         "MISMATCH", ["shipper"])

    # R2 labels seen in the real docx / pdf attachments
    for label, field in [
        ("Shipper (Principal or Seller) (\u53d1\u8d27\u4eba)", "shipper"), ("Consignee (\u6536\u8d27\u4eba)", "consignee"),
        ("Notify (\u901a\u77e5\u4eba)", "notify_party"), ("PORT OF LOADING (\u88c5\u8d27\u6e2f)", "port_of_loading"),
        ("POD (\u5378\u8d27\u6e2f)", "port_of_discharge"), ("Total Containers (\u7bb1\u6570)", "container_count"),
        ("Gross Wt (kgs) (\u6bdb\u91cd KGS)", "gross_weight_kg"), ("Gross Weight\u6bdb\u91cd(KGS) (\u6bdb\u91cd KGS)", "gross_weight_kg"),
        ("TOTAL Gross Wt (kgs)", "gross_weight_kg"), ("TOTAL GROSS WEIGHT", "gross_weight_kg"),
        ("TOTAL Gross Weight (KGS)", "gross_weight_kg"), ("Port of Discharge (POD) (\u5378\u8d27\u6e2f)", "port_of_discharge"),
        ("Notify Party/Intermediate Consignee (\u901a\u77e5\u4eba)", "notify_party"), ("Gross Weight:", "gross_weight_kg"),
    ]:
        assert field in canonicalize_fields({label: "x"}), label
    assert canonicalize_fields({"Random Field": "x"}) == {}

    # R3 document-type strings: real titles must not trigger wrong_doc_type
    for t in ["BILL OF LADING INSTRUCTION", "BL INSTRUCTION", "SHIPPING INSTRUCTION", "Shipping Instruction (SI)"]:
        case("R3-si-" + t, pair(si_meta={"document_type": t}), "OK", [])
    for t in ["BILL OF LADING (DRAFT)", "bill_of_lading_draft", "Draft B/L", "BL"]:
        case("R3-bl-" + t, pair(bl_meta={"document_type": t}), "OK", [])
    for t in ["COMMERCIAL INVOICE", "Packing List", "Certificate of Origin"]:
        case("R3-wrong-" + t, pair(bl_meta={"document_type": t}), "NEEDS_REVIEW", [], "wrong_doc_type")
    # inference from raw text must not call an SI titled "BILL OF LADING INSTRUCTION" a BL
    case("R3-rawtext-si", pair(si_meta={"raw_text": "BILL OF LADING INSTRUCTION\nB/L NUMBER: X\nShipper ..."}), "OK", [])
    case("R3-rawtext-wrong", pair(bl_meta={"raw_text": "COMMERCIAL INVOICE\n=====\nInvoice No.: 1\n*** NOT A SHIPPING INSTRUCTION ***"}),
         "NEEDS_REVIEW", [], "wrong_doc_type")
    case("R3-swapped", pair(si_meta={"document_type": "bill_of_lading"}), "NEEDS_REVIEW", [], "wrong_doc_type")

    # R4 placeholders (dataset uses '____MT' for any field)
    for token in ["____MT", "TBD", "NIL", "N.A.", "??? MTS", "PENDING", "\u2014"]:
        for f in ("shipper", "port_of_loading", "container_count", "gross_weight_kg"):
            case(f"R4-{f}-{token}", pair(si={f: token}), "NEEDS_REVIEW", [], "missing_value")
    assert not mc._is_missing("0") and not mc._is_missing("MT KLANG")

    # R5 review reason must look at BOTH sides
    case("R5-bl-blank", pair(bl={"gross_weight_kg": "N/A"}), "NEEDS_REVIEW", [], "missing_value")

    # R6 confidence handling
    for bad in [30, float("nan"), -1, "high", 0, 0.5, 101]:
        case(f"R6-conf-{bad}", pair(si={"shipper": {"value": "ABC SHIPPING SDN BHD", "confidence": bad}}),
             "NEEDS_REVIEW", [], "unreadable")
    case("R6-percent-ok", pair(si={"shipper": {"value": "ABC SHIPPING SDN BHD", "confidence": 95}}), "OK", [])
    case("R6-none-ok", pair(si={"shipper": {"value": "ABC SHIPPING SDN BHD"}}), "OK", [])

    # R7 container counts
    for v, n in [("3x40HC", 3), ("3 \u00d7 40'HC", 3), ("3.0", 3), (3.0, 3), ("03 x 40'HC", 3),
                 ("3 CONTAINERS", 3), ("12 x 20'FCL", 12), (3, 3)]:
        assert normalize_value("container_count", v).normalized == n, v
    for v in ["1 x 40'HC + 2 x 20'GP", "-3", "three", "0 x 40'HC", True, "40'HC x 3"]:
        assert normalize_value("container_count", v).normalized is None, v
    assert normalize_value("container_count", "1 x 40'HC + 2 x 20'GP").reason == "ambiguous_container_count"

    # R8 weights
    for v, n in [("22,000 KG", 22000), ("22000kg", 22000), ("22 tonnes", 22000), ("22 MT", 22000), ("22 t", 22000),
                 ("138 M/T", 138000), ("22.5 MT", 22500), ("21.577 MT", 21577), ("22 000 kg", 22000),
                 ("22,000.00 KG", 22000), (243588, 243588), (243588.0, 243588), ("GROSS 22,000", 22000),
                 ("343,715 KG", 343715)]:
        assert normalize_value("gross_weight_kg", v).normalized == n, v
    for v in ["22,000 KG (22 MT)", "22,000 kg / 22.0 mt", "22,5 tonnes", "22.000 KG", "21,577 MT",
              "1,234.5 KG", "22,000 lbs", "-5 KG", "0 kg", "40'HC 22,000 KG", 22000.5]:
        r = normalize_value("gross_weight_kg", v)
        assert r.normalized is None and r.reason, (v, r)
    case("R8-tonne-vs-kg", pair(si={"gross_weight_kg": "22,000 KG"}, bl={"gross_weight_kg": "22 MT"}), "OK", [])
    case("R8-weight-diff", pair(si={"gross_weight_kg": "22,000 KG"}, bl={"gross_weight_kg": "22,500 KG"}),
         "MISMATCH", ["gross_weight_kg"])

    # R9 entities / ports
    case("R9-and", pair(si={"shipper": "BALL & DOGGETT PTY LTD"}, bl={"shipper": "BALL AND DOGGETT PTY LTD"}), "OK", [])
    case("R9-hyphen", pair(si={"consignee": "EAST BRIGHT FZ-LLC"}, bl={"consignee": "EAST BRIGHT FZ LLC"}), "OK", [])
    case("R9-suffix-is-real-diff", pair(si={"shipper": "APRIL FINE PAPER TRADING"},
                                        bl={"shipper": "APRIL FINE PAPER TRADING (MIDDLE EAST) FZE"}),
         "MISMATCH", ["shipper"])
    case("R9-north-south", pair(si={"port_of_loading": "PORT KLANG (NORTH)"}, bl={"port_of_loading": "PORT KLANG (SOUTH)"}),
         "MISMATCH", ["port_of_loading"])
    case("R9-locode-differs", pair(si={"port_of_discharge": "SINGAPORE (SGSIN)"}, bl={"port_of_discharge": "SINGAPORE (MYPKG)"}),
         "MISMATCH", ["port_of_discharge"])
    case("R9-country-optional", pair(si={"port_of_discharge": "KARACHI, PAKISTAN (PKKHI)"}, bl={"port_of_discharge": "KARACHI"}), "OK", [])
    case("R9-country-wording", pair(si={"port_of_discharge": "NEW YORK, US"}, bl={"port_of_discharge": "NEW YORK, USA"}),
         "NEEDS_REVIEW", [], "unreadable")
    case("R9-klang-not-a-code", pair(si={"port_of_loading": "KLANG"}, bl={"port_of_loading": "PORT KLANG"}),
         "MISMATCH", ["port_of_loading"])
    case("R9-st-period", pair(si={"port_of_loading": "ST. PETERSBURG"}, bl={"port_of_loading": "ST PETERSBURG"}), "OK", [])

    # R10 review keeps every field comparison (a real mismatch is not hidden)
    r = case("R10-partial", pair(bl={"container_count": "4", "notify_party": ""}), "NEEDS_REVIEW", [], "missing_value")
    assert set(r["field_results"]) == set(COMPARE_FIELDS)
    assert r["field_results"]["container_count"]["status"] == "MISMATCH"
    assert r["partial_defect_fields"] == ["container_count"]
    assert r["defect_fields"] == [] and r["has_defect"] is False       # submission stays NEEDS_REVIEW

    # R11 mismatch report shows SI and BL values side by side
    r = case("R11-discrepancies", pair(bl={"container_count": "4 x 40'HC"}), "MISMATCH", ["container_count"])
    assert r["discrepancies"] == [{"field": "container_count", "si": "3 x 40'HC", "bl": "4 x 40'HC"}]
    assert case("R11-ok-message", pair(), "OK", [])["message"] == "No mismatch detected."

    # R12 never crash, never fail silently
    for bad in (None, [], "oops", 5):
        r = verify(bad, email_id="x")
        assert r["status"] == "NEEDS_REVIEW" and r["processing_error"] and r["retryable"], bad
        json.dumps(r, default=str)
    try:
        verify(pair(), category="NOT_A_CATEGORY")
        raise AssertionError("invalid category must raise")
    except ValueError:
        pass
    case("R12-category-spelling", {**pair(bl={"container_count": "4"})}, "MISMATCH", ["container_count"])
    assert verify(pair(bl={"container_count": "4"}), category="bl comparison")["status"] == "MISMATCH"
    assert verify(pair(bl={"container_count": "4"}), category="SPAM")["status"] == "OK"

    # R13 metadata flag variants
    for meta in [{"readable": "false"}, {"readable": 0}, {"status": "OCR_FAILED"}, {"error": "boom"}]:
        case(f"R13-{meta}", pair(bl_meta=meta), "NEEDS_REVIEW", [], "unreadable")
    case("R13-missing-attachment-str", pair(bl_meta={"missing_attachment": "true"}), "NEEDS_REVIEW", [], "missing_attachment")

    # R14 a received document with no extracted fields is NOT silently 'OK'
    case("R14-empty-extraction", {"si": seven(), "bl": {}, "bl_meta": {"readable": True}}, "NEEDS_REVIEW", [], "unreadable")
    # ...but the 'please send the draft BL' emails (no metadata, no flag) stay unevaluated
    r = case("R14-send-draft", {"si": {}, "bl": {}}, "OK", [])
    assert r["message"].startswith("Comparison not performed")
    case("R14-missing-flagged", {"si": seven(), "bl": {}, "attachments_expected": True}, "NEEDS_REVIEW", [], "missing_attachment")


def human_loop():
    bad = seven(container_count="4")
    for name, payload in {
        "top-level": {"si": seven(), "bl": bad},
        "documents wrapper": {"documents": {"si": seven(), "bl": bad}},
        "extracted + SI/BL": {"extracted": {"SI": seven(), "BL": bad}},
        "upper-case top level": {"SI": seven(), "BL": bad},
    }.items():
        assert verify(payload)["status"] == "MISMATCH", name
        r = apply_human_correction(payload, bl_corrections={"container_count": "3"}, reviewer="tester")
        assert r["status"] == "OK", (name, r)
        assert r["human_review"]["reviewer"] == "tester"
        assert r["human_review"]["changes"] == [{"side": "BL", "field": "container_count",
                                                 "action": "corrected", "before": "4", "after": "3"}]
        assert r["human_review"]["resolved"] is True

    # every reason can be resolved by a person
    full = seven()
    assert apply_human_correction({"si": seven(), "bl": {}, "bl_meta": {"readable": False, "status": "unreadable"}},
                                  bl_corrections=full)["status"] == "OK"
    assert apply_human_correction({"si": seven(), "bl": {}, "attachments_expected": True},
                                  bl_corrections=full)["status"] == "OK"
    assert apply_human_correction({"si": seven(), "bl": {"Seller": "X"}, "bl_meta": {"document_type": "commercial_invoice"}},
                                  bl_corrections=full)["status"] == "OK"
    assert apply_human_correction({"si": seven(gross_weight_kg="N/A"), "bl": seven()},
                                  si_corrections={"gross_weight_kg": "22,000 KG"})["status"] == "OK"
    # a human can correct into a real mismatch too
    r = apply_human_correction({"si": seven(gross_weight_kg="N/A"), "bl": seven()},
                               si_corrections={"gross_weight_kg": "21,000 KG"})
    assert r["status"] == "MISMATCH" and r["defect_fields"] == ["gross_weight_kg"]

    # confirm a low-confidence value without retyping it
    payload = {"si": {**seven(), "gross_weight_kg": {"value": "22,000 KG", "confidence": 0.4}}, "bl": seven()}
    assert verify(payload)["status"] == "NEEDS_REVIEW"
    r = apply_human_correction(payload, si_confirmed=["gross_weight_kg"])
    assert r["status"] == "OK" and r["human_review"]["changes"][0]["action"] == "confirmed"
    try:
        apply_human_correction({"si": seven(gross_weight_kg="N/A"), "bl": seven()}, si_confirmed=["gross_weight_kg"])
        raise AssertionError("cannot confirm a missing value")
    except ValueError:
        pass
    try:
        apply_human_correction({"si": seven(), "bl": seven()}, bl_corrections={"vessel": "X"})
        raise AssertionError("unsupported field must raise")
    except ValueError:
        pass
    # input not mutated
    original = {"si": seven(), "bl": bad}
    snapshot = json.dumps(original, sort_keys=True)
    apply_human_correction(original, bl_corrections={"container_count": "3"})
    assert json.dumps(original, sort_keys=True) == snapshot


def submission_shape():
    for res in (verify(pair(bl={"container_count": "4"})), verify(pair()),
                verify({"si": seven(), "bl": {}, "attachments_expected": True}),
                verify(pair(), category="SPAM")):
        sub = to_submission_record(res)
        assert set(sub) == {"category", "status", "review_reason", "defect_fields", "has_defect"}
        json.dumps(sub)
    assert to_submission_record(verify(pair(bl={"container_count": "4"}))) == {
        "category": "BL_COMPARISON", "status": "MISMATCH", "review_reason": None,
        "defect_fields": ["container_count"], "has_defect": True}


def evidence_store(tmp="member_c_evidence_test.jsonl"):
    import os
    if os.path.exists(tmp):
        os.remove(tmp)
    mc.save_evidence(verify(pair(bl={"container_count": "4"}), email_id="e1"), tmp)
    mc.save_evidence(verify(pair(), email_id="e2"), tmp)
    rows = [json.loads(x) for x in open(tmp, encoding="utf-8")]
    assert [r["email_id"] for r in rows] == ["e1", "e2"] and "saved_at" in rows[0]
    assert rows[0]["field_results"]["container_count"]["si"]["raw"] == "3 x 40'HC"
    os.remove(tmp)


def main():
    original_tests()
    readme_claims()
    regressions()
    human_loop()
    submission_shape()
    evidence_store()
    print("ALL MEMBER-C UNIT TESTS PASSED")


if __name__ == "__main__":
    main()
