from collections import Counter

import pandas as pd
import streamlit as st


FIELD_LABELS = {
    "shipper": "Shipper",
    "consignee": "Consignee",
    "notify_party": "Notify Party",
    "port_of_loading": "Port of Loading",
    "port_of_discharge": "Port of Discharge",
    "container_count": "Container Count",
    "gross_weight_kg": "Gross Weight",
}


def _friendly_reason(reason):
    text = str(reason or "").strip()
    lower = text.lower()

    service_markers = (
        "google.rpc",
        "retryinfo",
        "resourceexhausted",
        "429",
        "quota",
        "rate limit",
        "service unavailable",
        "temporarily unavailable",
    )

    if any(marker in lower for marker in service_markers):
        return "Temporary AI service unavailable"

    if len(text) > 140:
        return "Processing issue requires review"

    return text.replace("_", " ").strip().title()


def _record_lookup(df):
    if df is None or df.empty:
        return {}

    lookup = {}

    for _, row in df.iterrows():
        record = row.to_dict()
        record_id = record.get("ID")

        if record_id is not None:
            lookup[str(record_id)] = record

    return lookup


def _result_status(result):
    status = str(
        result.get("status") or ""
    ).lower()

    if status == "mismatch":
        return "Mismatch"

    if status == "human_review":
        return "Needs Review"

    if status == "failed":
        return "Failed"

    return "No Issues"


def _field_issues(result):
    verification = result.get("verification") or {}
    field_results = verification.get("field_results") or {}

    issues = []

    for field_name, field_result in field_results.items():
        field_status = str(
            (field_result or {}).get("status") or ""
        ).upper()

        if field_status in {
            "MISMATCH",
            "REVIEW",
        }:
            issues.append({
                "field": field_name,
                "status": field_status,
            })

    return issues


def _collect_intelligence(df, full_results):
    records = _record_lookup(df)

    field_counts = Counter()
    mismatch_patterns = Counter()
    review_reasons = Counter()
    affected_rows = []

    mismatch_emails = 0
    review_emails = 0
    failed_emails = 0

    for result in full_results:
        if not isinstance(result, dict):
            continue

        email_id = str(
            result.get("email_id") or ""
        )

        status = _result_status(result)

        if status == "Mismatch":
            mismatch_emails += 1
        elif status == "Needs Review":
            review_emails += 1
        elif status == "Failed":
            failed_emails += 1

        issues = _field_issues(result)

        mismatch_fields = []

        for issue in issues:
            field_name = issue["field"]
            field_status = issue["status"]

            field_counts[field_name] += 1

            if field_status == "MISMATCH":
                mismatch_fields.append(field_name)

            record = records.get(email_id, {})

            affected_rows.append({
                "Email ID": email_id,
                "Subject": record.get("Subject", ""),
                "Field": FIELD_LABELS.get(
                    field_name,
                    field_name.replace("_", " ").title(),
                ),
                "Issue": (
                    "Mismatch"
                    if field_status == "MISMATCH"
                    else "Needs Review"
                ),
                "Shipment": record.get("Shipment", ""),
            })

        if len(mismatch_fields) >= 2:
            pattern = tuple(
                sorted(mismatch_fields)
            )
            mismatch_patterns[pattern] += 1

        review_reason = (
            (result.get("verification") or {}).get(
                "review_reason"
            )
            or result.get("review_reason")
            or result.get("reason")
        )

        if status == "Needs Review" and review_reason:
            review_reasons[str(review_reason)] += 1

    return {
        "processed": len(full_results),
        "mismatch_emails": mismatch_emails,
        "review_emails": review_emails,
        "failed_emails": failed_emails,
        "field_counts": field_counts,
        "patterns": mismatch_patterns,
        "review_reasons": review_reasons,
        "affected_rows": affected_rows,
    }


def _render_field_bars(field_counts):
    if not field_counts:
        st.info(
            "No field-level discrepancies are available yet."
        )
        return

    maximum = max(field_counts.values())

    for field_name, count in field_counts.most_common():
        label = FIELD_LABELS.get(
            field_name,
            field_name.replace("_", " ").title(),
        )

        width = (
            int(count / maximum * 100)
            if maximum
            else 0
        )

        st.markdown(
            f"""
            <div style="margin-bottom:13px;">
                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    margin-bottom:5px;
                    font-size:12px;
                ">
                    <span style="
                        font-weight:700;
                        color:var(--text-color);
                        -webkit-text-fill-color:var(--text-color);
                    ">
                        {label}
                    </span>
                    <span style="
                        font-weight:700;
                        opacity:.65;
                    ">
                        {count} cases
                    </span>
                </div>

                <div style="
                    height:8px;
                    border-radius:999px;
                    background:rgba(148,163,184,.18);
                    overflow:hidden;
                ">
                    <div style="
                        width:{width}%;
                        height:100%;
                        border-radius:999px;
                        background:linear-gradient(
                            90deg,
                            #2563eb,
                            #6366f1
                        );
                    "></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_intelligence_metric(
    container,
    label,
    value,
    subtitle=None,
    compact=False,
):
    value_size = "25px" if compact else "42px"

    subtitle_html = ""

    if subtitle:
        subtitle_html = f"""
        <div style="
            display:inline-block;
            margin-top:8px;
            padding:3px 8px;
            border-radius:999px;
            background:#174b35;
            color:#dff7e9;
            -webkit-text-fill-color:#dff7e9;
            font-size:11px;
            font-weight:700;
        ">
            {subtitle}
        </div>
        """

    with container:
        st.markdown(
            f"""
            <div style="
                min-height:132px;
                padding:15px 14px 13px;
                border-radius:14px;
                border:1px solid #34465c;
                background:#111c2d;
                box-sizing:border-box;
            ">
                <div style="
                    font-size:13px;
                    font-weight:600;
                    color:#a8bbcf;
                    -webkit-text-fill-color:#a8bbcf;
                    margin-bottom:7px;
                ">
                    {label}
                </div>

                <div style="
                    font-size:{value_size};
                    line-height:1.08;
                    font-weight:700;
                    color:#f4f8fc;
                    -webkit-text-fill-color:#f4f8fc;
                    white-space:normal;
                    overflow-wrap:anywhere;
                ">
                    {value}
                </div>

                {subtitle_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_discrepancy_intelligence(
    df,
    full_results,
    total_records=None,
):
    full_results = full_results or []

    total_records = (
        int(total_records)
        if total_records is not None
        else len(df)
    )

    st.markdown("### Discrepancy Intelligence")

    if not full_results:
        st.info(
            "Run Full Analysis to generate cross-email discrepancy intelligence."
        )
        return

    data = _collect_intelligence(
        df,
        full_results,
    )

    processed = data["processed"]

    if processed < total_records:
        st.caption(
            f"Live intelligence based on "
            f"{processed}/{total_records} processed emails."
        )
    else:
        st.caption(
            f"Analysis complete across "
            f"{processed} emails."
        )

    metric_cols = st.columns(4)

    _render_intelligence_metric(
        metric_cols[0],
        "Processed",
        processed,
    )

    _render_intelligence_metric(
        metric_cols[1],
        "Mismatch Emails",
        data["mismatch_emails"],
    )

    _render_intelligence_metric(
        metric_cols[2],
        "Needs Review",
        data["review_emails"],
    )

    most_common_field = (
        data["field_counts"].most_common(1)
    )

    if most_common_field:
        field_name, field_count = most_common_field[0]

        field_label = FIELD_LABELS.get(
            field_name,
            field_name.replace("_", " ").title(),
        )

        _render_intelligence_metric(
            metric_cols[3],
            "Top Issue",
            field_label,
            f"{field_count} cases",
            compact=True,
        )
    else:
        _render_intelligence_metric(
            metric_cols[3],
            "Top Issue",
            "None",
            compact=True,
        )

    st.write("")

    left_col, right_col = st.columns([1.35, 1])

    with left_col:
        st.markdown("#### Most frequent issue fields")

        _render_field_bars(
            data["field_counts"]
        )

    with right_col:
        st.markdown("#### Recurring patterns")

        if data["patterns"]:
            for pattern, count in data[
                "patterns"
            ].most_common(5):
                labels = [
                    FIELD_LABELS.get(
                        field,
                        field.replace("_", " ").title(),
                    )
                    for field in pattern
                ]

                st.markdown(
                    f"""
                    <div style="
                        padding:10px 12px;
                        margin-bottom:8px;
                        border-radius:10px;
                        border:1px solid
                        color-mix(
                            in srgb,
                            var(--text-color) 12%,
                            transparent
                        );
                    ">
                        <div style="
                            font-size:12px;
                            font-weight:750;
                        ">
                            {" + ".join(labels)}
                        </div>
                        <div style="
                            font-size:11px;
                            opacity:.6;
                            margin-top:3px;
                        ">
                            {count} affected email(s)
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption(
                "No recurring multi-field mismatch pattern detected yet."
            )

        st.markdown("#### Review reasons")

        if data["review_reasons"]:
            for reason, count in data[
                "review_reasons"
            ].most_common(5):
                readable_reason = _friendly_reason(reason)

                st.markdown(
                    f"**{readable_reason}** · {count} case(s)"
                )
        else:
            st.caption(
                "No human-review reasons recorded yet."
            )

    st.write("")

    render_smart_review_queue(
        df=df,
        full_results=full_results,
    )

    st.write("")
    st.markdown("#### Investigate affected emails")

    available_fields = sorted(
        {
            row["Field"]
            for row in data["affected_rows"]
        }
    )

    if not available_fields:
        st.caption(
            "No affected emails are available yet."
        )
        return

    selected_field = st.selectbox(
        "Issue field",
        ["All issue fields"] + available_fields,
        key="intelligence_field_filter",
    )

    filtered_rows = data["affected_rows"]

    if selected_field != "All issue fields":
        filtered_rows = [
            row
            for row in filtered_rows
            if row["Field"] == selected_field
        ]

    result_df = pd.DataFrame(filtered_rows)

    if result_df.empty:
        st.caption(
            "No emails match this issue field."
        )
        return

    st.dataframe(
        result_df,
        use_container_width=True,
        hide_index=True,
    )


def _build_review_queue(df, full_results):
    records = _record_lookup(df)
    queue = []

    for result in full_results or []:
        if not isinstance(result, dict):
            continue

        email_id = str(
            result.get("email_id") or ""
        )

        record = records.get(email_id, {})

        if record.get("Type") != "Document Check":
            continue

        raw_status = str(
            result.get("status") or ""
        ).lower()

        verification = (
            result.get("verification") or {}
        )

        field_results = (
            verification.get("field_results") or {}
        )

        mismatch_fields = []
        review_fields = []

        for field_name, field_result in field_results.items():
            field_status = str(
                (field_result or {}).get("status") or ""
            ).upper()

            label = FIELD_LABELS.get(
                field_name,
                field_name.replace("_", " ").title(),
            )

            if field_status == "MISMATCH":
                mismatch_fields.append(label)

            elif field_status == "REVIEW":
                review_fields.append(label)

        issue_count = (
            len(mismatch_fields)
            + len(review_fields)
        )

        if raw_status == "failed":
            priority_rank = 4
            priority = "Processing Error"

            reason = (
                result.get("reason")
                or "Pipeline processing failed"
            )

        elif raw_status == "human_review":
            priority_rank = 3
            priority = "Needs Review"

            reason = (
                verification.get("review_reason")
                or result.get("review_reason")
                or result.get("reason")
                or "Manual verification required"
            )

        elif (
            raw_status == "mismatch"
            and len(mismatch_fields) >= 2
        ):
            priority_rank = 2
            priority = "Multi-field Mismatch"

            reason = (
                f"{len(mismatch_fields)} discrepancies detected"
            )

        elif raw_status == "mismatch":
            priority_rank = 1
            priority = "Mismatch"

            reason = "1 discrepancy detected"

        else:
            continue

        issue_labels = (
            mismatch_fields
            + review_fields
        )

        queue.append({
            "email_id": email_id,
            "subject": record.get(
                "Subject",
                "Untitled email",
            ),
            "shipment": record.get(
                "Shipment",
                "",
            ),
            "priority": priority,
            "priority_rank": priority_rank,
            "reason": str(reason),
            "issue_fields": issue_labels,
            "issue_count": issue_count,
            "confidence": record.get(
                "Confidence",
                "",
            ),
        })

    queue.sort(
        key=lambda item: (
            -item["priority_rank"],
            -item["issue_count"],
            item["email_id"],
        )
    )

    return queue


def render_smart_review_queue(
    df,
    full_results,
    limit=8,
):
    queue = _build_review_queue(
        df,
        full_results,
    )

    st.markdown("#### Smart Review Queue")

    st.caption(
        "Cases are prioritised using real pipeline status, "
        "review requirements, and the number of affected fields."
    )

    if not queue:
        st.success(
            "No document cases currently require attention."
        )
        return

    st.markdown(
        f"**{len(queue)} case(s) require attention**"
    )

    st.write("")

    for index, item in enumerate(
        queue[:limit],
        start=1,
    ):
        left, right = st.columns(
            [5.5, 1.2]
        )

        with left:
            issue_text = (
                ", ".join(item["issue_fields"])
                if item["issue_fields"]
                else "Case-level review"
            )

            st.markdown(
                f"""
                <div style="
                    border:1px solid
                    color-mix(
                        in srgb,
                        var(--text-color) 11%,
                        transparent
                    );
                    border-radius:12px;
                    padding:12px 14px;
                    margin-bottom:5px;
                ">
                    <div style="
                        display:flex;
                        gap:10px;
                        align-items:center;
                        margin-bottom:5px;
                    ">
                        <span style="
                            font-size:11px;
                            opacity:.55;
                            font-weight:700;
                        ">
                            #{index}
                        </span>

                        <span style="
                            font-size:13px;
                            font-weight:800;
                            color:var(--text-color);
                            -webkit-text-fill-color:var(--text-color);
                        ">
                            {item["email_id"]}
                        </span>

                        <span style="
                            font-size:10px;
                            font-weight:800;
                            letter-spacing:.4px;
                            text-transform:uppercase;
                            opacity:.72;
                        ">
                            {item["priority"]}
                        </span>
                    </div>

                    <div style="
                        font-size:12px;
                        font-weight:650;
                        margin-bottom:3px;
                    ">
                        {issue_text}
                    </div>

                    <div style="
                        font-size:11px;
                        opacity:.62;
                    ">
                        {item["reason"]}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with right:
            st.write("")

            if st.button(
                "Open Case",
                key=(
                    f"smart_queue_"
                    f"{item['email_id']}"
                ),
                use_container_width=True,
            ):
                st.session_state[
                    "selected_record_id"
                ] = item["email_id"]

                st.session_state[
                    "case_view"
                ] = True

                st.session_state[
                    "page_override"
                ] = None

                st.rerun()

    if len(queue) > limit:
        st.caption(
            f"Showing the top {limit} of "
            f"{len(queue)} actionable cases."
        )
