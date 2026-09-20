"""
candidate_engine.py

Multi-evidence candidate ranking engine for shipping documents.

The extractor should never blindly trust the first value it encounters.

For every possible value we calculate:

    - label similarity
    - semantic relevance
    - document proximity
    - value plausibility
    - unit consistency
    - source reliability
    - OCR risk
    - negative evidence
    - structural evidence

The engine returns the best candidate AND keeps the rejected candidates.

This makes extraction explainable and auditable.
"""

from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
import re


# ============================================================================
# SOURCE RELIABILITY
# ============================================================================

SOURCE_RELIABILITY = {
    "text": 0.99,
    "pdf_text": 0.97,
    "docx": 0.97,
    "xlsx": 0.97,
    "rule": 0.96,
    "structural_fallback": 0.72,
    "ocr": 0.70,
    "ocr+ai": 0.95,
    "ai_text": 0.65,
    "ai_vision": 0.65,
}


# ============================================================================
# FIELD SEMANTICS
# ============================================================================

FIELD_TERMS = {

    "shipper": {
        "positive": (
            "shipper",
            "exporter",
            "consignor",
            "seller",
            "principalshipper",
        ),
        "negative": (
            "consignee",
            "notify",
            "importer",
            "buyer",
        ),
    },

    "consignee": {
        "positive": (
            "consignee",
            "importer",
            "receiver",
            "buyer",
            "orderof",
        ),
        "negative": (
            "shipper",
            "exporter",
            "notify",
        ),
    },

    "notify_party": {
        "positive": (
            "notify",
            "notifyparty",
            "intermediateconsignee",
        ),
        "negative": (
            "shipper",
            "consignee",
        ),
    },

    "port_of_loading": {
        "positive": (
            "portofloading",
            "loadingport",
            "loadport",
            "pol",
            "originport",
            "placeofloading",
            "portofshipment",
        ),
        "negative": (
            "portofdischarge",
            "dischargeport",
            "destinationport",
            "pod",
        ),
    },

    "port_of_discharge": {
        "positive": (
            "portofdischarge",
            "dischargeport",
            "destinationport",
            "pod",
            "finalport",
            "placeofdischarge",
        ),
        "negative": (
            "portofloading",
            "loadingport",
            "loadport",
            "pol",
        ),
    },

    "container_count": {
        "positive": (
            "container",
            "containers",
            "containercount",
            "numberofcontainers",
            "quantityofcontainers",
            "containerquantity",
            "equipmentquantity",
            "equipmentcount",
        ),
        "negative": (
            "grossweight",
            "netweight",
            "tareweight",
        ),
    },

    "gross_weight_kg": {
        "positive": (
            "grossweight",
            "grosswt",
            "grossmass",
            "totalgrossweight",
            "totalgrosswt",
            "cargogrossweight",
            "shipmentgrossweight",
        ),
        "negative": (
            "netweight",
            "netwt",
            "netmass",
            "tareweight",
            "tarewt",
            "taremass",
        ),
    },
}


# ============================================================================
# DATACLASS
# ============================================================================

@dataclass
class Candidate:

    field: str
    value: object

    raw_value: str
    raw_label: str

    source: str = "rule"

    label_score: float = 0.0
    semantic_score: float = 0.0
    proximity_score: float = 0.0
    plausibility_score: float = 0.0
    unit_score: float = 0.0
    source_score: float = 0.0

    negative_penalty: float = 0.0

    line_number: int = 0

    selected: bool = False

    rejection_reason: str | None = None

    @property
    def score(self):

        positive = (
            self.label_score * 0.28
            + self.semantic_score * 0.18
            + self.proximity_score * 0.14
            + self.plausibility_score * 0.18
            + self.unit_score * 0.10
            + self.source_score * 0.12
        )

        return round(
            max(
                0.0,
                min(
                    1.0,
                    positive - self.negative_penalty,
                ),
            ),
            4,
        )

    def to_dict(self):

        result = asdict(self)

        result["score"] = self.score

        return result


# ============================================================================
# NORMALISATION
# ============================================================================

def compact(value):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value or "").lower(),
    )


def similarity(a, b):

    a = compact(a)
    b = compact(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


# ============================================================================
# SEMANTIC SCORING
# ============================================================================

def calculate_semantic_score(
    field,
    label,
):

    key = compact(label)

    rules = FIELD_TERMS.get(
        field,
        {},
    )

    positive = rules.get(
        "positive",
        (),
    )

    negative = rules.get(
        "negative",
        (),
    )

    score = 0.50

    for term in positive:

        if term in key:

            score += 0.15

    for term in negative:

        if term in key:

            score -= 0.30

    return max(
        0.0,
        min(
            1.0,
            score,
        ),
    )


# ============================================================================
# PROXIMITY
# ============================================================================

def calculate_proximity(
    label_line,
    value_line,
):

    distance = abs(
        label_line
        - value_line
    )

    if distance == 0:
        return 1.0

    if distance == 1:
        return 0.95

    if distance == 2:
        return 0.85

    if distance == 3:
        return 0.70

    if distance == 4:
        return 0.50

    return 0.30


# ============================================================================
# VALUE PLAUSIBILITY
# ============================================================================

def calculate_plausibility(
    field,
    value,
):

    if value is None:
        return 0.0

    # ------------------------------------------------------------------------
    # PARTY
    # ------------------------------------------------------------------------

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

        if not re.search(
            r"[A-Za-z]",
            text,
        ):
            return 0.2

        return 0.95

    # ------------------------------------------------------------------------
    # PORT
    # ------------------------------------------------------------------------

    if field in (
        "port_of_loading",
        "port_of_discharge",
    ):

        text = str(value).strip()

        if len(text) < 3:
            return 0.2

        if len(text) > 150:
            return 0.4

        if re.search(
            r"[A-Za-z]",
            text,
        ):
            return 0.95

        return 0.3

    # ------------------------------------------------------------------------
    # CONTAINER COUNT
    # ------------------------------------------------------------------------

    if field == "container_count":

        try:

            number = int(value)

        except (
            ValueError,
            TypeError,
        ):

            return 0.0

        if 1 <= number <= 100:
            return 1.0

        if 101 <= number <= 500:
            return 0.5

        return 0.1

    # ------------------------------------------------------------------------
    # GROSS WEIGHT
    # ------------------------------------------------------------------------

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
            return 0.55

        return 0.1

    return 0.5


# ============================================================================
# UNIT ANALYSIS
# ============================================================================

def calculate_unit_score(
    field,
    raw_value,
):

    text = str(
        raw_value or ""
    ).upper()

    if field == "gross_weight_kg":

        if re.search(
            r"\bKG\b|\bKGS\b|\bKILOGRAM",
            text,
        ):
            return 1.0

        if re.search(
            r"\bLB\b|\bLBS\b|\bPOUND",
            text,
        ):
            return 0.25

        return 0.65

    if field == "container_count":

        if re.search(
            r"CONTAINER|UNIT|EQUIPMENT",
            text,
        ):
            return 1.0

        return 0.70

    return 0.85


# ============================================================================
# NEGATIVE EVIDENCE
# ============================================================================

def calculate_negative_penalty(
    field,
    label,
    raw_value,
):

    label_key = compact(label)
    value_key = compact(raw_value)

    penalty = 0.0

    if field == "gross_weight_kg":

        forbidden = (
            "netweight",
            "netwt",
            "netmass",
            "tareweight",
            "tarewt",
            "taremass",
        )

        for term in forbidden:

            if term in label_key:

                penalty += (
                    0.75
                    if "tare" not in term
                    else 0.85
                )

        if "tare" in value_key:
            penalty += 0.40

    if field == "container_count":

        if "weight" in label_key:
            penalty += 0.75

    return min(
        1.0,
        penalty,
    )


# ============================================================================
# CANDIDATE CREATION
# ============================================================================

def make_candidate(
    field,
    value,
    raw_value,
    raw_label,
    *,
    label_score=1.0,
    label_line=0,
    value_line=0,
    source="rule",
):

    return Candidate(

        field=field,

        value=value,

        raw_value=str(
            raw_value or ""
        ),

        raw_label=str(
            raw_label or ""
        ),

        source=source,

        label_score=max(
            0.0,
            min(
                1.0,
                label_score,
            ),
        ),

        semantic_score=calculate_semantic_score(
            field,
            raw_label,
        ),

        proximity_score=calculate_proximity(
            label_line,
            value_line,
        ),

        plausibility_score=calculate_plausibility(
            field,
            value,
        ),

        unit_score=calculate_unit_score(
            field,
            raw_value,
        ),

        source_score=SOURCE_RELIABILITY.get(
            source,
            0.75,
        ),

        negative_penalty=calculate_negative_penalty(
            field,
            raw_label,
            raw_value,
        ),

        line_number=value_line,
    )


# ============================================================================
# RANKING
# ============================================================================

def rank_candidates(
    candidates,
):

    if not candidates:

        return {
            "winner": None,
            "candidates": [],
            "margin": 0.0,
            "ambiguous": False,
        }

    ranked = sorted(
        candidates,
        key=lambda candidate: candidate.score,
        reverse=True,
    )

    winner = ranked[0]

    winner.selected = True

    for candidate in ranked[1:]:

        candidate.rejection_reason = (
            "lower_score"
        )

    margin = (
        winner.score
        - ranked[1].score
        if len(ranked) > 1
        else 1.0
    )

    ambiguous = (
        len(ranked) > 1
        and margin < 0.08
    )

    if ambiguous:

        winner.rejection_reason = None

        for candidate in ranked[1:]:

            if (
                winner.score
                - candidate.score
                < 0.08
            ):

                candidate.rejection_reason = (
                    "near_tie_requires_review"
                )

    return {
        "winner": winner,
        "candidates": ranked,
        "margin": round(
            margin,
            4,
        ),
        "ambiguous": ambiguous,
    }


# ============================================================================
# SERIALISATION
# ============================================================================

def ranking_to_dict(
    ranking,
):

    return {
        "winner": (
            ranking["winner"].to_dict()
            if ranking["winner"]
            else None
        ),

        "candidates": [
            candidate.to_dict()
            for candidate in ranking[
                "candidates"
            ]
        ],

        "margin": ranking[
            "margin"
        ],

        "ambiguous": ranking[
            "ambiguous"
        ],
    }