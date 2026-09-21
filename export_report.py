import csv
import io
from datetime import datetime

import streamlit as st


FIELD_LABELS = {
    "shipper": "Shipper",
    "consignee": "Consignee",
    "notify_party": "Notify Party",
    "port_of_loading": "Port of Loading",
    "port_of_discharge": "Port of Discharge",
    "container_count": "Container Count",
    "gross_weight_kg": "Gross Weight (KG)",
}


REPORT_COLUMNS = [
    "Email ID",
    "Subject",
    "Category",
    "Status",
    "Confidence",
    "Defect Fields",
    "Field",
    "SI Value",
    "BL Value",
    "SI Evidence",
    "BL Evidence",
    "SI Source",
    "BL Source",
    "Review Reason",
]


def _record_lookup(df):
    lookup = {}

    if df is None or getattr(df, "empty", True):
        return lookup

    for _, row in df.iterrows():
        record = row.to_dict()
        record_id = record.get("ID")

        if record_id is not None:
            lookup[str(record_id)] = record

    return lookup


def _display_value(value):
    if value is None:
        return "[missing]"

    text = str(value).strip()

    if not text:
        return "[missing]"

    return text


def _format_confidence(result, record):
    classification = result.get("classification") or {}

    confidence = classification.get("confidence")

    if confidence is None:
        confidence = result.get("classification_confidence")

    if confidence is None:
        confidence = record.get("Confidence")

    if isinstance(confidence, (int, float)):
        if 0 <= confidence <= 1:
            return f"{confidence:.0%}"

        return f"{confidence:.0f}%"

    return str(confidence or "")


def _result_status(result):
    verification = result.get("verification") or {}

    verification_status = str(
        verification.get("status") or ""
    ).upper()

    if verification_status in {
        "MISMATCH",
        "NEEDS_REVIEW",
    }:
        return verification_status

    pipeline_status = str(
        result.get("status") or ""
    ).lower()

    if pipeline_status == "mismatch":
        return "MISMATCH"

    if pipeline_status == "human_review":
        return "NEEDS_REVIEW"

    return None


def _evidence_details(result, field_name, side):
    field_evidence = (
        (result.get("evidence") or {})
        .get(field_name, {})
        .get(side)
        or {}
    )

    snippet = field_evidence.get("snippet") or ""

    source = (
        field_evidence.get("document_source")
        or field_evidence.get("source")
        or ""
    )

    return snippet, source


def _field_value(field_result, side):
    side_result = field_result.get(side) or {}

    value = side_result.get("raw")

    if value is None:
        value = side_result.get("normalized")

    return _display_value(value)


def _collect_results(full_results, pipeline_results):
    combined = {}

    for result in full_results or []:
        if not isinstance(result, dict):
            continue

        email_id = result.get("email_id")

        if email_id is not None:
            combined[str(email_id)] = result

    if isinstance(pipeline_results, dict):
        for email_id, result in pipeline_results.items():
            if not isinstance(result, dict):
                continue

            key = str(
                result.get("email_id")
                or email_id
            )

            if key not in combined:
                combined[key] = result

    return list(combined.values())


def build_discrepancy_report_rows(
    df,
    full_results=None,
    pipeline_results=None,
):
    records = _record_lookup(df)

    results = _collect_results(
        full_results,
        pipeline_results,
    )

    rows = []

    for result in results:
        email_id = str(
            result.get("email_id") or ""
        )

        status = _result_status(result)

        if status not in {
            "MISMATCH",
            "NEEDS_REVIEW",
        }:
            continue

        record = records.get(email_id, {})

        verification = (
            result.get("verification") or {}
        )

        field_results = (
            verification.get("field_results")
            or {}
        )

        defect_fields = (
            verification.get("defect_fields")
            or verification.get(
                "partial_defect_fields"
            )
            or []
        )

        defect_text = ", ".join(
            FIELD_LABELS.get(field, field)
            for field in defect_fields
        )

        category = (
            result.get("category")
            or verification.get("category")
            or ""
        )

        confidence = _format_confidence(
            result,
            record,
        )

        subject = record.get("Subject", "")

        review_reason = (
            verification.get("review_reason")
            or result.get("review_reason")
            or result.get("reason")
            or ""
        )

        issue_fields = []

        for field_name, field_result in field_results.items():
            field_status = str(
                field_result.get("status") or ""
            ).upper()

            if field_status in {
                "MISMATCH",
                "REVIEW",
            }:
                issue_fields.append(
                    (field_name, field_result)
                )

        if issue_fields:
            for field_name, field_result in issue_fields:
                si_evidence, si_source = (
                    _evidence_details(
                        result,
                        field_name,
                        "si",
                    )
                )

                bl_evidence, bl_source = (
                    _evidence_details(
                        result,
                        field_name,
                        "bl",
                    )
                )

                field_status = str(
                    field_result.get("status")
                    or ""
                ).upper()

                row_status = (
                    "MISMATCH"
                    if field_status == "MISMATCH"
                    else "NEEDS_REVIEW"
                )

                rows.append({
                    "Email ID": email_id,
                    "Subject": subject,
                    "Category": category,
                    "Status": row_status,
                    "Confidence": confidence,
                    "Defect Fields": defect_text,
                    "Field": FIELD_LABELS.get(
                        field_name,
                        field_name,
                    ),
                    "SI Value": _field_value(
                        field_result,
                        "si",
                    ),
                    "BL Value": _field_value(
                        field_result,
                        "bl",
                    ),
                    "SI Evidence": si_evidence,
                    "BL Evidence": bl_evidence,
                    "SI Source": si_source,
                    "BL Source": bl_source,
                    "Review Reason": (
                        field_result.get("reason")
                        or review_reason
                    ),
                })

        elif status == "NEEDS_REVIEW":
            rows.append({
                "Email ID": email_id,
                "Subject": subject,
                "Category": category,
                "Status": "NEEDS_REVIEW",
                "Confidence": confidence,
                "Defect Fields": defect_text,
                "Field": "Case-level review",
                "SI Value": "",
                "BL Value": "",
                "SI Evidence": "",
                "BL Evidence": "",
                "SI Source": "",
                "BL Source": "",
                "Review Reason": review_reason,
            })

    return rows


def build_discrepancy_csv(rows):
    output = io.StringIO()

    writer = csv.DictWriter(
        output,
        fieldnames=REPORT_COLUMNS,
    )

    writer.writeheader()
    writer.writerows(rows)

    return output.getvalue().encode("utf-8-sig")


def render_export_button(
    df,
    full_results=None,
    pipeline_results=None,
):
    full_results = full_results or []

    total_records = len(df) if df is not None else 0
    processed_records = len(full_results)

    if processed_records == 0:
        st.info(
            "Run Full Analysis to generate the complete discrepancy report."
        )
        return

    if processed_records < total_records:
        st.info(
            f"Full Analysis is {processed_records}/{total_records} processed. "
            "Complete the analysis to export the full discrepancy report."
        )
        return

    rows = build_discrepancy_report_rows(
        df=df,
        full_results=full_results,
        pipeline_results=pipeline_results,
    )

    if not rows:
        st.success(
            "No mismatch or review cases are available for export."
        )
        return

    csv_data = build_discrepancy_csv(rows)

    email_count = len({
        row["Email ID"]
        for row in rows
    })

    mismatch_count = sum(
        row["Status"] == "MISMATCH"
        for row in rows
    )

    review_count = sum(
        row["Status"] == "NEEDS_REVIEW"
        for row in rows
    )

    st.caption(
        f"{email_count} affected email(s) · "
        f"{mismatch_count} mismatch row(s) · "
        f"{review_count} review row(s)"
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M"
    )

    st.download_button(
        "Export Discrepancy Report CSV",
        data=csv_data,
        file_name=(
            "shipguard_discrepancy_report_"
            f"{timestamp}.csv"
        ),
        mime="text/csv",
        use_container_width=False,
        key="export_discrepancy_report",
    )
