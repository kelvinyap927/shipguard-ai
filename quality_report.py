"""
quality_report.py

Generate a quality summary from Member B's extracted JSON.

Usage:

    python quality_report.py

Shows:
    - extraction completeness
    - average confidence
    - documents requiring review
    - OCR usage
    - validation failures
    - field-level statistics
"""

import json
import os
from collections import Counter

from modules.schema import FIELDS


def load_results(path="out/extracted_all.json"):

    if not os.path.exists(path):
        raise SystemExit(
            f"Missing {path}. Run run_extraction.py first."
        )

    with open(
        path,
        encoding="utf-8",
    ) as fh:

        return json.load(fh)


def main():

    data = load_results()

    documents = []

    for email_id, email in data.items():

        for doc_type in (
            "si",
            "bl",
        ):

            doc = email.get(
                doc_type
            )

            if doc:
                documents.append(
                    (
                        email_id,
                        doc_type.upper(),
                        doc,
                    )
                )

    print()
    print("=" * 72)
    print("       SHIPGUARD AI — MEMBER B QUALITY REPORT")
    print("=" * 72)

    print()
    print(
        "Documents analysed:",
        len(documents),
    )

    # ---------------------------------------------------------------
    # Status
    # ---------------------------------------------------------------

    status_counter = Counter(
        doc.get("status")
        for _, _, doc in documents
    )

    print()
    print("DOCUMENT STATUS")

    for status, count in (
        status_counter.most_common()
    ):

        print(
            f"  {status:<20} {count}"
        )

    # ---------------------------------------------------------------
    # Validation status
    # ---------------------------------------------------------------

    validation_counter = Counter(
        doc.get(
            "validation_status",
            "UNKNOWN",
        )
        for _, _, doc in documents
    )

    print()
    print("VALIDATION STATUS")

    for status, count in (
        validation_counter.most_common()
    ):

        print(
            f"  {status:<20} {count}"
        )

    # ---------------------------------------------------------------
    # Quality score
    # ---------------------------------------------------------------

    scores = [
        doc.get(
            "quality_score",
            0,
        )
        for _, _, doc in documents
    ]

    if scores:

        average = (
            sum(scores)
            / len(scores)
        )

        print()
        print(
            "Average quality score:",
            f"{average:.3f}",
        )

    # ---------------------------------------------------------------
    # Missing fields
    # ---------------------------------------------------------------

    missing = Counter()

    for _, _, doc in documents:

        for field in doc.get(
            "missing_fields",
            [],
        ):

            missing[field] += 1

    print()
    print("MISSING FIELDS")

    if missing:

        for field, count in (
            missing.most_common()
        ):

            print(
                f"  {field:<25} {count}"
            )

    else:

        print(
            "  None"
        )

    # ---------------------------------------------------------------
    # Validation flags
    # ---------------------------------------------------------------

    flags = Counter()

    for _, _, doc in documents:

        for flag in doc.get(
            "validation_flags",
            [],
        ):

            flags[flag] += 1

    print()
    print("VALIDATION FLAGS")

    if flags:

        for flag, count in (
            flags.most_common()
        ):

            print(
                f"  {flag:<45} {count}"
            )

    else:

        print(
            "  None"
        )

    # ---------------------------------------------------------------
    # OCR
    # ---------------------------------------------------------------

    ocr_count = sum(
        1
        for _, _, doc in documents
        if doc.get(
            "read_method"
        ) == "ocr"
    )

    print()
    print(
        "OCR documents:",
        ocr_count,
    )

    # ---------------------------------------------------------------
    # Field-level confidence
    # ---------------------------------------------------------------

    print()
    print("FIELD CONFIDENCE")

    for field in FIELDS:

        values = []

        for _, _, doc in documents:

            confidence = (
                doc.get(
                    "confidence",
                    {},
                ).get(
                    field,
                    0,
                )
            )

            if confidence:

                values.append(
                    confidence
                )

        if values:

            average = (
                sum(values)
                / len(values)
            )

            print(
                f"  {field:<25} "
                f"{average:.3f}"
            )

    # ---------------------------------------------------------------
    # Review queue
    # ---------------------------------------------------------------

    print()
    print("DOCUMENTS REQUIRING REVIEW")

    review_count = 0

    for email_id, doc_type, doc in documents:

        if doc.get(
            "validation_status"
        ) in (
            "REVIEW",
            "VERIFY",
            "INCOMPLETE",
        ):

            review_count += 1

            print(
                f"  {email_id:<15}"
                f"{doc_type:<5}"
                f"{doc.get('validation_status'):<12}"
                f"score={doc.get('quality_score', 0):.3f}"
            )

    if review_count == 0:

        print(
            "  None"
        )

    print()
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()