"""
consensus_engine.py

Independent-reader consensus layer.

Combines evidence from:

    rule extraction
    OCR
    AI
    structural extraction

The principle is:

    two independent sources agreeing
        >
    one source being highly confident

But disagreement is never silently hidden.
It becomes explicit review evidence.
"""

from difflib import SequenceMatcher


def _compact(value):

    return "".join(
        c
        for c in str(
            value or ""
        ).upper()
        if c.isalnum()
    )


def similarity(
    a,
    b,
):

    a = _compact(a)
    b = _compact(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


def compare_sources(
    rule_value,
    ocr_value=None,
    ai_value=None,
):

    sources = {}

    if rule_value is not None:

        sources["rule"] = rule_value

    if ocr_value is not None:

        sources["ocr"] = ocr_value

    if ai_value is not None:

        sources["ai"] = ai_value

    if not sources:

        return {
            "status": "NO_EVIDENCE",
            "agreement": 0.0,
            "selected": None,
            "sources": {},
        }

    values = list(
        sources.items()
    )

    # ------------------------------------------------------------------------
    # Perfect agreement
    # ------------------------------------------------------------------------

    for i in range(
        len(values)
    ):

        for j in range(
            i + 1,
            len(values),
        ):

            name_a, value_a = values[i]
            name_b, value_b = values[j]

            score = similarity(
                value_a,
                value_b,
            )

            if score >= 0.97:

                return {
                    "status":
                        "AGREEMENT",

                    "agreement":
                        round(
                            score,
                            3,
                        ),

                    "selected":
                        value_a,

                    "sources":
                        sources,

                    "agreement_sources": [
                        name_a,
                        name_b,
                    ],
                }

    # ------------------------------------------------------------------------
    # No agreement
    # ------------------------------------------------------------------------

    return {

        "status":
            "DISAGREEMENT",

        "agreement":
            0.0,

        "selected":
            None,

        "sources":
            sources,

        "reason":
            "independent sources disagree; human or higher-level AI review required",
    }


def build_consensus(
    evidence,
):

    result = {}

    for field, ev in (
        evidence or {}
    ).items():

        rule_value = ev.get(
            "rule_value"
        )

        ocr_value = ev.get(
            "ocr_value"
        )

        ai_value = ev.get(
            "ai_value"
        )

        result[field] = compare_sources(
            rule_value,
            ocr_value,
            ai_value,
        )

    return result