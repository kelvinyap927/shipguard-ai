# Member B — document reading & field extraction

## Where it plugs in
    classifier -> attachment_router -> document_job -> **extraction_job** -> (comparison: Member C)

`modules/pipeline.py` calls `run_extraction(document_job)` (Step 6). After it, `process_email(email)` returns:

    result["status"]             "extracted" | "human_review" | "classified"
    result["review_reason"]      missing_attachment | unreadable | wrong_doc_type | missing_value
    result["extraction"]["si"]   / ["bl"]:
        fields      the 7 values, readable          {"port_of_loading": "NANTONG, CHINA", "gross_weight_kg": 131058, ...}
        keys        the 7 values, normalised        <- COMPARE THESE (equal keys = same value)
        evidence    raw label/value + confidence per field (show this to the human reviewer)
        read_method text | pdf_text | ocr | docx | xlsx
    result["extraction"]["ocr_used"]   True => a scan was involved

## The clean JSON  (for Member C / the report / the demo)
`python run_extraction.py` writes `out/extracted_all.json` (+ one file per email in `out/extracted/`).
Shape of each document is documented at the top of `modules/json_export.py`:
`fields`, `keys`, `confidence`, `needs_verification`, `missing_fields`, `details` (address, port code, container type), `notes`.

## Files
    modules/schema.py            the 7 fields + every label variant ("Load Port" = POL ...)          <- add new labels HERE
    modules/document_reader.py   file -> text (txt / pdf / scanned pdf via OCR / docx / xlsx / png / jpg)
    modules/normalizer.py        clean values: weights, ports, container counts, names, blank detection
    modules/field_extractor.py   text -> 7 fields + evidence + confidence
    modules/ai_extractor.py      OPTIONAL Claude layer: reads scans (vision) + rescues unfamiliar labels     [new]
    modules/json_export.py       clean structured JSON per document / per email                              [new]
    modules/extraction_job.py    glue: document_job -> extraction result + audit lines
    run_extraction.py            whole inbox -> out/ (pipeline_results, extracted_all, review_queue)
    extract_file.py              ONE file -> JSON.  Demo tool, no inbox needed                               [new]
    show_extraction.py           one email, audit trail + SI/BL side by side
    test_extraction.py           self-checks for the rules
    test_member_b_extras.py      self-checks for the AI layer + JSON export (fake AI, no key needed)         [new]

## Run
    pip install -r requirements.txt
    python test_extraction.py
    python test_member_b_extras.py
    python run_extraction.py
    python show_extraction.py email_004
    python extract_file.py attachments/email_004_SI.txt

Scanned PDFs (emails 512-514) need the Tesseract program installed (Windows installer:
https://github.com/UB-Mannheim/tesseract/wiki). Without it they go to human review as `unreadable`
— unless the AI layer is on, which can still read them.

## Optional AI layer (Claude)      -- OFF by default
    pip install anthropic
    set ANTHROPIC_API_KEY=sk-ant-...          (PowerShell:  $env:ANTHROPIC_API_KEY="sk-ant-...")
    python run_extraction.py --ai
    python extract_file.py scan.pdf --ai --full
Optional: `SDOC_AI_MODEL=<model name>` to change the model (default in modules/ai_extractor.py).

What it does — only two jobs, and only when needed (rules found everything -> no AI call, no cost):
  1. **Scans**: OCR makes small reading errors. The AI reads the page image; if OCR and AI agree the value
     gets confidence 0.95, if they differ the AI value is used, marked 0.65 (= "please verify") and the OCR
     value is kept in `evidence[field]["ocr_value"]`.
  2. **Unfamiliar label** (rules can't find a field): the AI reads the text. Its answer is accepted only if
     it really appears in the document.
Safety: a field the customer left BLANK is never filled by the AI. Any AI failure (no key, no internet,
bad reply) silently keeps the rules result. Nothing changes when the switch is off.

## For Member C (comparison) — please read
* Compare `keys`, not `fields`.
* **Scans:** a value read only by OCR always has confidence 0.70 (listed in `needs_verification`). In the
  three scanned pairs of the dataset, every difference between SI and BL was an OCR misreading
  ("NHAVA"/"MHAVA", "FZ-LLC"/"FZ-LLO"), not a real defect. Suggested rule: if `ocr_used` is True and a
  difference is only in a `needs_verification` field, report NEEDS_REVIEW instead of MISMATCH.
* A blank field (`missing_fields`, review_reason `missing_value`) is NOT a mismatch.

## Change log (what was added/changed in Member B's own files)
    modules/document_reader.py   ReadResult.images keeps scan pages; OCR call split into _run_ocr()
    modules/normalizer.py        + normalize_value()  (one shared place: raw text -> value + key)
    modules/field_extractor.py   uses normalize_value(); AI hook; vision-only fallback; OCR_MAX_CONFIDENCE=0.70;
                                 doc-type check moved into _wrong_type()
    run_extraction.py            + --ai flag, + writes out/extracted_all.json
    requirements.txt             + anthropic (optional)

Teammate files touched (small, additive):
    modules/pipeline.py        + Step 6 (extraction), kept the teammates' try/except + "failed" status; + review_reason
    modules/document_job.py    + "review_reason": "missing_attachment"
    test_batch_pipeline.py     + counts the new "extracted" status
    .gitignore                 + out/
classifier.py, attachment_router.py, format_router.py, inbox.py are unchanged.