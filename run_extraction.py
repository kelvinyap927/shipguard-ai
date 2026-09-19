"""
run_extraction.py  --  run the WHOLE pipeline (classify -> route -> extract) on the inbox.

    python run_extraction.py                      # every email
    python run_extraction.py --only email_004 email_512     # re-run a few (= retry)

    python run_extraction.py --ai                 # also use the optional Claude AI layer (needs ANTHROPIC_API_KEY)

Writes to out/:
    pipeline_results.json   every email's full result (share with the comparison person)
    extracted_all.json      the CLEAN structured JSON: the 7 fields of every SI and BL   <- hand this over
    extracted/email_XXX.json  the same, one file per email
    review_queue.json       every case a human must look at, with the reason
Then prints a summary.
"""
import argparse
import collections
import json
import os
import time

from modules.inbox import load_inbox
from modules.json_export import write_json_exports
from modules.pipeline import process_email


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="only these email ids (use this to retry failures)")
    ap.add_argument("--out", default="out")
    ap.add_argument("--ai", action="store_true", help="use the optional Claude AI layer for scans / unknown labels")
    args = ap.parse_args()
    if args.ai:
        os.environ["SDOC_USE_AI"] = "1"

    inbox = load_inbox()
    emails = [e for e in inbox if not args.only or e["email_id"] in set(args.only)]

    os.makedirs(args.out, exist_ok=True)
    results_path = os.path.join(args.out, "pipeline_results.json")
    results = {}
    if args.only and os.path.exists(results_path):           # keep earlier results when retrying a few
        results = json.load(open(results_path, encoding="utf-8"))

    t0 = time.time()
    for email in emails:
        results[email["email_id"]] = process_email(email)

    json.dump(results, open(results_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    queue = [{"email_id": eid, "reason": r.get("review_reason"),
              "notes": r.get("extraction", {}).get("review_notes") or
                       [x["message"] for x in r["audit_log"] if x["step"] == "attachment_check"]}
             for eid, r in results.items() if r["status"] == "human_review"]
    json.dump(queue, open(os.path.join(args.out, "review_queue.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    exported = write_json_exports(results, args.out)

    mine = [r for r in results.values() if "extraction" in r]
    print(f"Done in {time.time() - t0:.1f}s -> {args.out}/")
    print("status counts        :", dict(collections.Counter(r["status"] for r in results.values())))
    print("review reasons       :", dict(collections.Counter(r["review_reason"] for r in results.values() if r.get("review_reason"))))
    print("extracted pairs      :", sum(1 for r in mine if r["status"] == "extracted"),
          "| via OCR:", sum(1 for r in mine if r["extraction"]["ocr_used"]))
    print("clean JSON exported  :", exported, "comparison emails ->", os.path.join(args.out, "extracted_all.json"))


if __name__ == "__main__":
    main()