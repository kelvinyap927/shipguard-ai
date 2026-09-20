"""
Run Member C over the SDOC v2 dataset using a simulated Member-B extractor.

  python3 dataset_check.py <dataset_dir>                       # dir with inbox/ + attachments/
  python3 dataset_check.py <dataset_dir> <ground_truth.json>   # also diff against a key (optional)

Needs: pdftotext (poppler), openpyxl, python-docx.
Scenarios cover the extraction styles Member B might deliver:
  raw-labels  : field labels exactly as printed in the document (tests alias mapping)
  canonical   : labels already mapped to the 7 canonical names
  addr / name : entity value with address lines vs. name only
Member A routing is simulated: a comparison is expected when the email body says
"compare the SI and draft BL" and an attachment is missing.
"""
import glob, json, os, re, sys, collections
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sdoc_extract_sim as extract
from member_c_verifier import verify, to_submission_record

SCENARIOS = {
    "raw labels + addresses":       dict(addr=True,  canon=False),
    "raw labels, name only":        dict(addr=False, canon=False),
    "canonical labels + addresses": dict(addr=True,  canon=True),
    "canonical labels, name only":  dict(addr=False, canon=True),
    "canonical + raw_text only (no document_type)": dict(addr=True, canon=True, rawtext=True),
}


def build_payload(root, e, mode):
    atts = {}
    for a in e["attachments"]:
        atts["si" if re.search(r"_SI\.\w+$", a) else "bl"] = a
    p = {}
    for side in ("si", "bl"):
        if side not in atts:
            p[side] = {}
            continue
        fields, m = extract.read(os.path.join(root, atts[side]), mode["addr"])
        if mode["canon"]:
            fields = {(extract.label_field(k) or k): v for k, v in fields.items()}
        meta = {"readable": m["readable"]}
        if not m["readable"]:
            meta["status"] = "unreadable"
        if mode.get("rawtext"):
            meta["raw_text"] = m.get("raw_text")
        else:
            meta["document_type"] = m.get("document_type")
        p[side], p[side + "_meta"] = fields, meta
    p["attachments_expected"] = len(e["attachments"]) < 2 and "compare the si and draft bl" in e["body"].casefold()
    return p


def main():
    root = sys.argv[1]
    gt = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else None
    emails = {}
    for pth in sorted(glob.glob(os.path.join(root, "inbox", "email_*.json"))):
        e = json.load(open(pth, encoding="utf-8"))
        emails[e["email_id"]] = e
    ids = [i for i, g in gt.items() if g["category"] == "BL_COMPARISON"] if gt else \
          [i for i, e in emails.items() if e["attachments"] or "compare the si and draft bl" in e["body"].casefold()]
    print(f"{len(ids)} comparison emails")
    for name, mode in SCENARIOS.items():
        tally, bad = collections.Counter(), []
        for eid in ids:
            r = verify(build_payload(root, emails[eid], mode), email_id=eid)
            sub = to_submission_record(r)
            tally[(sub["status"], sub["review_reason"])] += 1
            if gt:
                g = gt[eid]
                exp = (g["status"], g["review_reason"], sorted(g["defect_fields"]))
                got = (sub["status"], sub["review_reason"], sorted(sub["defect_fields"]))
                if exp != got:
                    bad.append((eid, exp, got))
        line = f"{name:48}"
        if gt:
            line += f" exact {len(ids) - len(bad)}/{len(ids)}"
        print(line, dict(tally) if not gt else "")
        for b in bad[:10]:
            print("    ", b)


if __name__ == "__main__":
    main()
