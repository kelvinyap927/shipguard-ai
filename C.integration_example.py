"""
Minimal integration example (revision 2).

Member A decides the email category and whether the comparison should run now.
Member B extracts SI/BL fields (+ document metadata).
Member C verifies them.
Member D displays the rich result and drives the human-review loop.
"""

from member_c_verifier import (
    verify, to_submission_record, apply_human_correction, save_evidence,
)

email_id = "email_001"
member_a_category = "BL_COMPARISON"

member_b_output = {
    "si": {
        "shipper": {"value": "ABC SHIPPING SDN BHD", "confidence": 0.99},
        "consignee": {"value": "XYZ TRADING PTE LTD", "confidence": 0.98},
        "notify_party": {"value": "XYZ TRADING PTE LTD", "confidence": 0.98},
        "port_of_loading": {"value": "PORT KLANG (MYPKG)", "confidence": 0.99},
        "port_of_discharge": {"value": "SINGAPORE (SGSIN)", "confidence": 0.99},
        "container_count": {"value": "3 x 40'HC", "confidence": 0.99},
        "gross_weight_kg": {"value": "22,000 KG", "confidence": 0.99},
    },
    "bl": {
        "shipper": {"value": "ABC SHIPPING SDN BHD", "confidence": 0.99},
        "consignee": {"value": "XYZ TRADING PTE LTD", "confidence": 0.98},
        "notify_party": {"value": "XYZ TRADING PTE LTD", "confidence": 0.98},
        "port_of_loading": {"value": "PORT KLANG", "confidence": 0.99},
        "port_of_discharge": {"value": "SINGAPORE", "confidence": 0.99},
        "container_count": {"value": "4 x 40'HC", "confidence": 0.99},
        "gross_weight_kg": {"value": "22 tonnes", "confidence": 0.99},
    },
    # Member B: send the document's title as document_type (or raw_text), and
    # readable=False (never a guess) when a file cannot be read.
    "si_meta": {"document_type": "shipping_instruction", "readable": True},
    "bl_meta": {"document_type": "bill_of_lading", "readable": True},
    # Member A: set True ONLY when the email says "please compare ..." but an
    # attachment is missing. Omit it for normal "please send the draft BL" mails.
    # "attachments_expected": True,
}

result = verify(member_b_output, email_id=email_id, category=member_a_category)

print(result["status"], result["defect_fields"])
for d in result["discrepancies"]:                       # side-by-side for Member D
    print(f"  {d['field']}: SI: {d['si']}  /  BL: {d['bl']}")

save_evidence(result, "member_c_evidence.jsonl")        # persistent evidence / audit trail

# Human review loop (Member D): the reviewer decides the BL really says 3 containers
fixed = apply_human_correction(
    member_b_output, bl_corrections={"container_count": "3"},
    email_id=email_id, reviewer="ops.user", note="checked against scanned BL page 1",
)
print(fixed["status"], fixed["human_review"]["changes"])

# Submission-shaped record for Member A's final submission dict:
print(to_submission_record(result))
