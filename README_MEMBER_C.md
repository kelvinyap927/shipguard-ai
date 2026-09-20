# Member C — Verification, Normalisation & Reliability (revision 2)

Module for the SDOC Hackathon. Member C receives extracted Shipping Instruction (SI) and
draft Bill of Lading (BL) data from Member B. It does **not** classify emails and does **not**
do OCR / extraction.

It performs: canonical field mapping · conservative normalisation · field-by-field SI vs BL
comparison · `OK` / `MISMATCH` / `NEEDS_REVIEW` decisions · evidence retention (in the result and,
optionally, on disk) · a human confirm/correct loop that re-runs the same logic · conversion to
the exact v2 self-evaluation record.

The seven fields: `shipper`, `consignee`, `notify_party`, `port_of_loading`,
`port_of_discharge`, `container_count`, `gross_weight_kg`.

## Files

| File | Purpose |
|---|---|
| `member_c_verifier.py` | the module (standard library only) |
| `test_member_c.py` | unit / adversarial / regression tests — `python3 test_member_c.py` |
| `integration_example.py` | how A / B / D call it |
| `dataset_check/` | runs Member C over the SDOC dataset (txt/pdf/docx/xlsx) with a *simulated* Member B; not part of the product |

## Member B → Member C contract

```python
payload = {
    "si": {"shipper": {"value": "ABC SHIPPING", "confidence": 0.99, "source": "SI p1 / Shipper row"}, ...},
    "bl": {...},
    "si_meta": {"document_type": "shipping_instruction", "readable": True},
    "bl_meta": {"document_type": "bill_of_lading",       "readable": True},
}
```

* Field keys may be the 7 canonical names **or the raw printed labels** — `Load Port`,
  `POD (卸货港)`, `TOTAL Gross Wt (kgs)`, `Gross Weight毛重(KGS)` … are all mapped.
* Values may be plain strings/numbers or `{"value", "confidence", "source"}` objects.
  `confidence` is 0–1 (a value in 1–100 is read as a percentage; NaN / negative / non-numeric
  is treated as *untrusted* and sent to review, never silently ignored).
* `document_type` may be a normalised name **or the document's own title** (`BILL OF LADING (DRAFT)`,
  `BILL OF LADING INSTRUCTION`, `BL INSTRUCTION`, `COMMERCIAL INVOICE` …). Alternatively provide
  `raw_text`; the first lines are inspected.
* For an unreadable file send `{"readable": False}` (or `status: "unreadable"/"failed"/"ocr_failed"`,
  or an `error` string) — **never a guessed value**.
* Entity values may include address lines (`\n`, `;` or ` | ` separated); only the first
  segment (the name) is compared.
* Wrapper shapes `{"documents": {...}}`, `{"extracted": {"SI":..,"BL":..}}` are accepted.

### `attachments_expected` (Member A)

* Email says *"please compare the SI and draft BL"* but an attachment is missing →
  set `attachments_expected=True` → `NEEDS_REVIEW / missing_attachment`.
* Email is just *"please send the draft BL"* → do not call `verify()` (or call it without the flag):
  the result is an unevaluated `OK`.
* If Member B produced metadata for a document but **no fields**, that is escalated as
  `unreadable` — it is never treated as “nothing to compare”.
* `category` is normalised (`"bl comparison"` → `BL_COMPARISON`) and validated; an unknown
  category raises `ValueError` (a wiring bug should be loud). Non-comparison categories return an
  unevaluated `OK` record.

## Decision policy

* **MATCH (`OK`)** only when all seven fields are present, valid, confident, and agree after
  field-specific normalisation. Message: `No mismatch detected.`
* **`MISMATCH`** only when both values are valid and a field-specific rule proves they differ.
  `defect_fields` lists only the differing fields; `discrepancies` gives
  `[{"field", "si", "bl"}]` for the side-by-side display.
* **`NEEDS_REVIEW`** (never a guess) for: unreadable document · wrong document type · missing
  attachment · missing / placeholder value (`N/A`, `TBA`, `???`, `____MT`, `NIL` …) · invalid or
  **ambiguous** number (`22,5 t`, `22.000 KG`, `22,000 KG (22 MT)`, `1 x 40'HC + 2 x 20'GP`) ·
  low or unusable confidence · conflicting duplicate aliases · same port name with different
  country wording (`US` vs `USA`).
  `review_reason` ∈ `wrong_doc_type | missing_attachment | unreadable | missing_value`.
  The review record still contains **every** field comparison (`field_results`) and
  `partial_defect_fields`, so a real mismatch on another field is visible to the reviewer.
* Internal failures never raise: `verify()` returns a `NEEDS_REVIEW` record with
  `processing_error=True`, `retryable=True` and the error text. `verify()` is pure, so a retry is
  just calling it again.

## Normalisation policy

Safe normalisation: Unicode/whitespace/case; punctuation in entity names (`PTE. LTD.`, `&`≙`AND`,
`FZ-LLC`≙`FZ LLC`); label aliases (incl. bilingual and `TOTAL …`); container counts (`3`, `3.0`,
`3 containers`, `3 x 40'HC`, `3x40HC`, `3 × 40'HC`); weights (`22,000 KG`, `22000kg`, `22 tonnes`,
`22 MT`, `22 t`, `138 M/T`, plain numbers = kg); ports (parenthesised UN/LOCODE, optional country,
`ST.`/`ST`).

Deliberately **not** fuzzy: `APRIL FINE PAPER TRADING` ≠ `APRIL FINE PAPER TRADING (MIDDLE EAST) FZE`;
`KLANG` ≠ `PORT KLANG`; `LIMITED` ≠ `LTD`. A UN/LOCODE is only stripped when written in
parentheses; if **both** sides carry one and they differ (`(MYPKG)` vs `(SGSIN)`, or `(NORTH)` vs
`(SOUTH)`) the ports do not match.

## Human-review loop (Member D)

```python
result = apply_human_correction(
    payload,
    bl_corrections={"container_count": "3"},   # person types the right value
    si_confirmed=["gross_weight_kg"],          # person confirms a low-confidence reading as-is
    email_id="email_123", reviewer="ops.user", note="checked scan p.1",
)
result["human_review"]  # {"reviewer", "note", "reviewed_at", "changes": [{side, field, action, before, after}], "resolved"}
```

* Works for every payload shape, including `documents` / `extracted` wrappers and upper-case keys.
* A side that a person touched is marked `human_verified`, so **unreadable / wrong-document /
  missing-attachment** cases can be resolved by typing the values from the real document.
* The corrected data runs through the same `verify()` — one comparison implementation only.

## Evidence

`save_evidence(result, "member_c_evidence.jsonl")` appends every result (raw + normalised values,
confidence, source, document metadata, human-review audit block) as JSON Lines — a persistent
record for Member D's audit trail.

## Output for the organiser scorer

```python
submission[email_id] = to_submission_record(result)
# {"category","status","review_reason","defect_fields","has_defect"}  — exactly the v2 keys
```

Do not send the rich result to the scorer.

## Testing

```bash
python3 test_member_c.py                                   # unit / adversarial / regression
python3 dataset_check/dataset_check.py <dataset_dir> [ground_truth.json]
```

Validated on the 220 `BL_COMPARISON` emails of the SDOC v2 dataset (txt, pdf, docx, xlsx,
scanned/garbled files, wrong documents, blanks) under five extraction styles (raw labels vs
canonical labels, name-only vs name+address, `raw_text`-only document typing): all statuses,
review reasons and defect fields reproduced. Fuzzed with 6,000 random malformed payloads: no
exceptions, invariants hold (`MISMATCH` ⇔ `defect_fields` ⇔ `has_defect`, `review_reason` only on
`NEEDS_REVIEW`).

## Known limitations / team decisions

1. **Address differences are ignored** — only the entity name is compared (the dataset only
   mutates names). If the business wants address diffs, surface them as a warning, not a defect.
2. A blank on any field turns the whole email into `NEEDS_REVIEW` (a partial mismatch stays visible
   in `partial_defect_fields`). This is what the dataset expects; change only knowingly.
3. `document_type: "unknown"` (or missing) disables the wrong-document gate; a non-SI/BL document
   whose fields still extract cleanly is only caught if Member B labels it.
4. Bare (un-parenthesised) port codes (`KARACHI PKKHI`) are not stripped, and `SGSIN` alone is not
   matched to `SINGAPORE` (no port database on purpose).
5. Only entity names are single-line aware: `NAME, ADDRESS` on one line is not split.

## Change log (revision 2)

Fixed: xlsx ` | ` address caused false MISMATCH on xlsx↔docx pairs · docx/pdf label variants
(`(发货人)`, `TOTAL …`) not mapped · whole-title `document_type` and `raw_text` inference produced
false `wrong_doc_type` (`BILL OF LADING INSTRUCTION` was read as a BL) · `____MT`/`NIL`/`TBD` treated as
real names/ports · review reason only inspected the SI side · out-of-range / NaN confidence silently
disabled the low-confidence gate · duplicate-alias check compared raw text/confidence and raised
false reviews · `3x40HC`, `3 × 40'HC`, `3.0`, multi-group counts · `22,000 KG (22 MT)` → 22,000,000 kg,
`22,5 t`, `1,234.5` truncation · `(NORTH)` vs `(SOUTH)` ports matched · review results hid real
mismatches · `apply_human_correction` ignored corrections for wrapper/upper-case payloads and could not
resolve unreadable/wrong-doc/missing-attachment cases · `verify(None)` crashed · misspelt category
silently skipped verification · README claimed tests that did not exist.
