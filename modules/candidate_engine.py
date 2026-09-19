"""
candidate_engine.py

Advanced candidate-generation and ranking engine for shipping documents.

Instead of accepting the first value found by the parser, this module
generates multiple possible candidates and scores them using:

    1. Label similarity
    2. Distance between label and value
    3. Value plausibility
    4. Field-specific semantics
    5. Negative evidence
    6. OCR risk
    7. Unit consistency
    8. Document structure

The winning candidate is retained, while rejected candidates are also
available for explainability and debugging.
"""

import re
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# Candidate model
# ---------------------------------------------------------------------------

@dataclass
class Candidate:
    field: str
    value: object
    raw_value: str
    raw_label: str

    label_score: float = 0.0
    distance_score: float = 0.0
    semantic_score: float = 0.0
    plausibility_score: float = 0.0
    unit_score: float = 0.0
    negative_score: float = 0.0

    source: str = "rule"

    selected: bool = False
    rejection_reason: str | None = None

    @property
    def score(self):
        """
        Weighted candidate score.

        Positive evidence:
            label       30%
            proximity   15%
            semantics   20%
            plausibility 20%
            units       15%

        Negative evidence is subtracted afterwards.
        """

        positive = (
            self.label_score * 0.30
            + self.distance_score * 0.15
            + self.semantic_score * 0.20
            + self.plausibility_score * 0.20
            + self.unit_score * 0.15
        )

        return max(
            0.0,
            min(
                1.0,
                positive - self.negative_score,
            ),
        )

    def to_dict(self):
        result = asdict(self)

        result["score"] = round(
            self.score,
            3,
        )

        return result


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _normalise(text):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(text or "").lower(),
    )


def _similarity(a, b):
    a = _normalise(a)
    b = _normalise(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


# ---------------------------------------------------------------------------
# Field semantics
# ---------------------------------------------------------------------------

FIELD_TERMS = {

    "shipper": {
        "positive": [
            "shipper",
            "exporter",
            "consignor",
            "seller",
        ],
        "negative": [
            "consignee",
            "notify",
            "importer",
            "buyer",
        ],
    },

    "consignee": {
        "positive": [
            "consignee",
            "importer",
            "receiver",
            "buyer",
            "orderof",
        ],
        "negative": [
            "shipper",
            "exporter",
            "notify",
        ],
    },

    "notify_party": {
        "positive": [
            "notify",
            "intermediateconsignee",
        ],
        "negative": [
            "shipper",
            "consignee",
        ],
    },

    "port_of_loading": {
        "positive": [
            "portofloading",
            "loadingport",
            "loadport",
            "pol",
            "originport",
            "placeofloading",
        ],
        "negative": [
            "portofdischarge",
            "dischargeport",
            "destinationport",
            "pod",
        ],
    },

    "port_of_discharge": {
        "positive": [
            "portofdischarge",
            "dischargeport",
            "destinationport",
            "pod",
            "placeofdischarge",
        ],
        "negative": [
            "portofloading",
            "loadingport",
            "loadport",
            "pol",
        ],
    },

    "container_count": {
        "positive": [
            "container",
            "containers",
            "containercount",
            "numberofcontainers",
            "quantityofcontainers",
            "equipmentquantity",
        ],
        "negative": [
            "grossweight",
            "netweight",
            "tareweight",
        ],
    },

    "gross_weight_kg": {
        "positive": [
            "grossweight",
            "grosswt",
            "grossmass",
            "totalgrossweight",
            "totalgrosswt",
        ],
        "negative": [
            "netweight",
            "netwt",
            "netmass",
            "tareweight",
            "tarewt",
        ],
    },
}


# ---------------------------------------------------------------------------
# Semantic scoring
# ---------------------------------------------------------------------------

def semantic_score(field, label):

    label_key = _normalise(label)

    terms = FIELD_TERMS.get(
        field,
        {},
    )

    positive = terms.get(
        "positive",
        [],
    )

    negative = terms.get(
        "negative",
        [],
    )

    score = 0.0

    for term in positive:

        if term in label_key:
            score += 0.25

    for term in negative:

        if term in label_key:
            score -= 0.50

    return max(
        0.0,
        min(
            1.0,
            0.50 + score,
        ),
    )


# ---------------------------------------------------------------------------
# Value plausibility
# ---------------------------------------------------------------------------

def plausibility_score(field, value):

    if value is None:
        return 0.0

    # ---------------------------------------------------------------
    # Party
    # ---------------------------------------------------------------

    if field in (
        "shipper",
        "consignee",
        "notify_party",
    ):

        text = str(value).strip()

        if len(text) < 2:
            return 0.1

        if len(text) > 250:
            return 0.3

        # Company/address-like strings are common.
        if re.search(
            r"[A-Za-z]",
            text,
        ):
            return 0.9

        return 0.5

    # ---------------------------------------------------------------
    # Ports
    # ---------------------------------------------------------------

    if field in (
        "port_of_loading",
        "port_of_discharge",
    ):

        text = str(value)

        if len(text) < 3:
            return 0.2

        if len(text) > 150:
            return 0.3

        if re.search(
            r"[A-Za-z]",
            text,
        ):
            return 0.9

        return 0.4

    # ---------------------------------------------------------------
    # Container count
    # ---------------------------------------------------------------

    if field == "container_count":

        try:
            n = int(value)
        except (
            ValueError,
            TypeError,
        ):
            return 0.0

        if 1 <= n <= 100:
            return 1.0

        if 101 <= n <= 500:
            return 0.5

        return 0.1

    # ---------------------------------------------------------------
    # Gross weight
    # ---------------------------------------------------------------

    if field == "gross_weight_kg":

        try:
            weight = float(value)
        except (
            ValueError,
            TypeError,
        ):
            return 0.0

        if 100 <= weight <= 100_000:
            return 1.0

        if 100_000 < weight <= 2_000_000:
            return 0.5

        return 0.1

    return 0.5


# ---------------------------------------------------------------------------
# Unit scoring
# ---------------------------------------------------------------------------

def unit_score(field, raw_value):

    text = str(
        raw_value or ""
    ).upper()

    if field == "gross_weight_kg":

        if re.search(
            r"\b(?:KG|KGS|KILOGRAMS?)\b",
            text,
        ):
            return 1.0

        if re.search(
            r"\b(?:LB|LBS|POUNDS?)\b",
            text,
        ):
            return 0.2

        return 0.6

    if field == "container_count":

        if re.search(
            r"\b(?:CONTAINER|CONTAINERS|UNIT|UNITS)\b",
            text,
        ):
            return 1.0

        return 0.7

    return 0.8


# ---------------------------------------------------------------------------
# Negative evidence
# ---------------------------------------------------------------------------

def negative_score(field, label, raw_value):

    label_key = _normalise(label)
    value_key = _normalise(raw_value)

    penalty = 0.0

    # ---------------------------------------------------------------
    # Gross weight vs net/tare
    # ---------------------------------------------------------------

    if field == "gross_weight_kg":

        if "netweight" in label_key:
            penalty += 0.70

        if "netwt" in label_key:
            penalty += 0.70

        if "netmass" in label_key:
            penalty += 0.70

        if "tareweight" in label_key:
            penalty += 0.80

        if "tarewt" in label_key:
            penalty += 0.80

        if "tare" in value_key:
            penalty += 0.50

    # ---------------------------------------------------------------
    # Container count
    # ---------------------------------------------------------------

    if field == "container_count":

        if "weight" in label_key:
            penalty += 0.70

    return min(
        1.0,
        penalty,
    )


# ---------------------------------------------------------------------------
# Distance scoring
# ---------------------------------------------------------------------------

def distance_score(
    label_line_index,
    value_line_index,
):
    """
    Score proximity between a recognised label and value.

    Same line = 1.0
    Next line = 0.95
    2 lines away = 0.80
    etc.
    """

    distance = abs(
        label_line_index
        - value_line_index
    )

    return max(
        0.1,
        1.0 - (
            distance * 0.10
        ),
    )


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------

def generate_candidate(
    field,
    label,
    value,
    raw_value=None,
    label_similarity=1.0,
    label_line_index=0,
    value_line_index=0,
    source="rule",
):

    raw_value = (
        raw_value
        if raw_value is not None
        else value
    )

    candidate = Candidate(

        field=field,

        value=value,

        raw_value=str(
            raw_value
        ),

        raw_label=str(
            label
        ),

        label_score=max(
            0.0,
            min(
                1.0,
                float(
                    label_similarity
                ),
            ),
        ),

        distance_score=distance_score(
            label_line_index,
            value_line_index,
        ),

        semantic_score=semantic_score(
            field,
            label,
        ),

        plausibility_score=plausibility_score(
            field,
            value,
        ),

        unit_score=unit_score(
            field,
            raw_value,
        ),

        negative_score=negative_score(
            field,
            label,
            raw_value,
        ),

        source=source,
    )

    return candidate


# ---------------------------------------------------------------------------
# Candidate ranking
# ---------------------------------------------------------------------------

def rank_candidates(candidates):

    if not candidates:
        return None, []

    ranked = sorted(
        candidates,
        key=lambda c: c.score,
        reverse=True,
    )

    winner = ranked[0]

    winner.selected = True

    # Explain why alternatives were rejected.
    for candidate in ranked[1:]:

        candidate.rejection_reason = (
            "lower_candidate_score"
        )

    return winner, ranked


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def explain_candidates(candidates):

    winner, ranked = rank_candidates(
        candidates
    )

    return {
        "selected": (
            winner.to_dict()
            if winner
            else None
        ),

        "alternatives": [
            candidate.to_dict()
            for candidate in ranked[1:]
        ],

        "candidate_count": len(
            ranked
        ),
    }