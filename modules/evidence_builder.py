FIELDS = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]


def _build_side_evidence(document, field):
    if not document:
        return None

    provenance = document.get("provenance", {}).get(field)

    if not provenance:
        return None

    raw_label = provenance.get("raw_label")
    raw_value = provenance.get("raw_value")
    confidence = provenance.get("confidence")

    accepted_value = document.get("fields", {}).get(field)
    is_accepted = accepted_value is not None

    if raw_label and raw_value:
        snippet = f"{raw_label}: {raw_value}"
    elif raw_value:
        snippet = str(raw_value)
    else:
        snippet = None

    if snippet is None:
        evidence_status = "NO_EVIDENCE"
    elif not is_accepted:
        evidence_status = "CANDIDATE_ONLY"
    else:
        evidence_status = "ACCEPTED"

    return {
        "snippet": snippet,
        "raw_label": raw_label,
        "raw_value": raw_value,
        "accepted_value": accepted_value,
        "is_accepted": is_accepted,
        "evidence_status": evidence_status,
        "source": provenance.get("source"),
        "method": provenance.get("method"),
        "confidence": confidence,
        "document_source": document.get("source"),
    }


def build_field_evidence(result):
    documents = result.get("documents") or {}

    si_document = documents.get("si")
    bl_document = documents.get("bl")

    evidence = {}

    for field in FIELDS:
        evidence[field] = {
            "si": _build_side_evidence(si_document, field),
            "bl": _build_side_evidence(bl_document, field),
        }

    return evidence
