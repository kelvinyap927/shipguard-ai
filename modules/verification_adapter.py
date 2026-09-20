from modules.schema import FIELDS


def build_verification_payload(extraction):

    payload = {}

    for side in ("si", "bl"):

        document = extraction.get(side) or {}
        fields = document.get("fields") or {}
        evidence = document.get("evidence") or {}

        payload[side] = {}

        for field in FIELDS:

            field_evidence = evidence.get(field) or {}

            payload[side][field] = {
                "value": fields.get(field),
                "confidence": field_evidence.get("confidence"),
                "source": field_evidence.get("source"),
            }

        status = str(document.get("status") or "").lower()

        payload[f"{side}_meta"] = {
            "document_type": (
                document.get("detected_type")
                or document.get("expected_type")
            ),
            "readable": status not in {
                "unreadable",
                "parse_error",
                "error",
                "failed",
            },
            "status": document.get("status"),
            "read_method": document.get("read_method"),
        }

    return payload
