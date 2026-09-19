"""
extract_file.py  --  read ONE document and print its 7 fields as JSON.  (Member B's demo tool)
 
    python extract_file.py attachments/email_004_SI.txt
    python extract_file.py my_bill_of_lading.pdf
    python extract_file.py scan.png --ai                 # let Claude vision read it (needs ANTHROPIC_API_KEY)
    python extract_file.py some.docx --type BL           # say what you expect: warns if the title says otherwise
    python extract_file.py some.pdf --full               # also print the raw evidence for every field
    python extract_file.py some.pdf --save out/result.json
 
Works with: .txt  .pdf (text or scanned)  .docx  .xlsx  .png  .jpg  .tif
It does not need the inbox, so you can point it at any file on your computer.
"""
import argparse
import json
import os
import sys
 
from modules.field_extractor import extract_document
from modules.json_export import doc_to_clean
 
 
def main():
    ap = argparse.ArgumentParser(description="Extract the 7 shipment fields from one document.")
    ap.add_argument("path", help="the document to read")
    ap.add_argument("--type", choices=["SI", "BL"], help="what you expect it to be (optional)")
    ap.add_argument("--ai", action="store_true", help="turn on the optional Claude AI layer")
    ap.add_argument("--full", action="store_true", help="include the raw evidence for each field")
    ap.add_argument("--save", metavar="FILE", help="also write the JSON to this file")
    args = ap.parse_args()
 
    if not os.path.isfile(args.path):
        sys.exit(f"file not found: {args.path}")
    if args.ai:
        os.environ["SDOC_USE_AI"] = "1"
 
    with open(args.path, "rb") as fh:
        data = fh.read()
    doc = extract_document(data, os.path.basename(args.path), expected_type=args.type)
 
    out = doc_to_clean(doc)
    if args.full:
        out["evidence"] = doc["evidence"]
    text = json.dumps(out, indent=2, ensure_ascii=False)
    print(text)
    if args.save:
        os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
        with open(args.save, "w", encoding="utf-8") as fh:
            fh.write(text)
 
 
if __name__ == "__main__":
    main()
 