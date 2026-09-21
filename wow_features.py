import html

import streamlit as st


def inject_wow_css():
    st.markdown(
        """
        <style>
        .sg-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            line-height: 1.2;
            white-space: nowrap;
            border: 1px solid transparent;
        }

        .sg-status-operational {
            color: #16a34a !important;
            -webkit-text-fill-color: #16a34a !important;
            background: rgba(22, 163, 74, 0.12);
            border-color: rgba(22, 163, 74, 0.24);
        }

        .sg-status-running {
            color: #3b82f6 !important;
            -webkit-text-fill-color: #3b82f6 !important;
            background: rgba(59, 130, 246, 0.12);
            border-color: rgba(59, 130, 246, 0.24);
        }

        .sg-status-paused {
            color: #d97706 !important;
            -webkit-text-fill-color: #d97706 !important;
            background: rgba(217, 119, 6, 0.12);
            border-color: rgba(217, 119, 6, 0.24);
        }

        .sg-status-complete {
            color: #16a34a !important;
            -webkit-text-fill-color: #16a34a !important;
            background: rgba(22, 163, 74, 0.12);
            border-color: rgba(22, 163, 74, 0.24);
        }

        .sg-status-dot {
            font-size: 11px;
            line-height: 1;
        }

        .sg-confidence-wrap {
            width: 100%;
            min-width: 95px;
            padding-top: 2px;
        }

        .sg-confidence-row {
            display: flex;
            align-items: center;
            gap: 7px;
        }

        .sg-confidence-track {
            flex: 1;
            height: 7px;
            min-width: 62px;
            overflow: hidden;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.24);
        }

        .sg-confidence-fill {
            height: 100%;
            border-radius: 999px;
        }

        .sg-confidence-high {
            background: #22c55e;
        }

        .sg-confidence-medium {
            background: #f59e0b;
        }

        .sg-confidence-low {
            background: #ef4444;
        }

        .sg-confidence-label {
            min-width: 44px;
            font-size: 10px;
            font-weight: 750;
            line-height: 1;
            color: var(--st-text-color) !important;
            -webkit-text-fill-color: var(--st-text-color) !important;
            opacity: 0.82;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_badge_html(
    status="idle",
    processed=0,
    total=0,
    summary=None,
):
    summary = summary or {}

    processed = int(processed or 0)
    total = int(total or 0)
    mismatch_count = int(summary.get("mismatch", 0) or 0)

    if status == "running":
        css_class = "sg-status-running"
        icon = "↻"
        label = f"Analysis running — {processed}/{total}"

    elif status == "paused":
        css_class = "sg-status-paused"
        icon = "Ⅱ"
        label = f"Analysis paused — {processed}/{total}"

    elif total > 0 and processed >= total:
        css_class = "sg-status-complete"
        icon = "●"
        label = f"Complete — {mismatch_count} mismatches found"

    else:
        css_class = "sg-status-operational"
        icon = "●"
        label = "System operational"

    return f"""
    <span class="sg-status-pill {css_class}">
        <span class="sg-status-dot">{html.escape(icon)}</span>
        <span>{html.escape(label)}</span>
    </span>
    """


def render_status_badge(
    status="idle",
    processed=0,
    total=0,
    summary=None,
):
    badge = status_badge_html(
        status=status,
        processed=processed,
        total=total,
        summary=summary,
    )

    st.markdown(
        f"""
        <div style="display:flex; justify-content:flex-end;">
            {badge}
        </div>
        """,
        unsafe_allow_html=True,
    )



def confidence_bar_html(value):
    confidence = str(value or "LOW").strip().upper()

    levels = {
        "HIGH": {
            "width": 100,
            "class": "sg-confidence-high",
            "label": "HIGH",
        },
        "MEDIUM": {
            "width": 66,
            "class": "sg-confidence-medium",
            "label": "MEDIUM",
        },
        "LOW": {
            "width": 33,
            "class": "sg-confidence-low",
            "label": "LOW",
        },
    }

    config = levels.get(
        confidence,
        levels["LOW"],
    )

    return f"""
    <div class="sg-confidence-wrap">
        <div class="sg-confidence-row">
            <div class="sg-confidence-track">
                <div
                    class="sg-confidence-fill {config['class']}"
                    style="width:{config['width']}%;"
                ></div>
            </div>
            <span class="sg-confidence-label">
                {html.escape(config['label'])}
            </span>
        </div>
    </div>
    """



PROCESSING_FIELD_LABELS = {
    "shipper": "Shipper",
    "consignee": "Consignee",
    "notify_party": "Notify Party",
    "port_of_loading": "Port of Loading",
    "port_of_discharge": "Port of Discharge",
    "container_count": "Container Count",
    "gross_weight_kg": "Gross Weight",
}


def _processing_log_entries(result):
    entries = []

    if not isinstance(result, dict):
        return entries

    for item in result.get("audit_log") or []:
        if not isinstance(item, dict):
            continue

        step = str(item.get("step") or "pipeline_step")
        message = str(
            item.get("message")
            or step.replace("_", " ").title()
        )

        state = "ok"
        message_lower = message.lower()

        if (
            step == "error"
            or "mismatch" in message_lower
            or "failed" in message_lower
        ):
            state = "error"
        elif (
            "human review" in message_lower
            or "requires human review" in message_lower
            or "needs review" in message_lower
        ):
            state = "review"

        entries.append({
            "state": state,
            "step": step.replace("_", " ").title(),
            "message": message,
        })

    verification = result.get("verification") or {}
    verification_status = str(
        verification.get("status") or ""
    ).upper()

    field_results = (
        verification.get("field_results") or {}
    )

    mismatch_fields = []
    review_fields = []

    for field_name, field_result in field_results.items():
        field_status = str(
            (field_result or {}).get("status") or ""
        ).upper()

        label = PROCESSING_FIELD_LABELS.get(
            field_name,
            field_name.replace("_", " ").title(),
        )

        if field_status == "MISMATCH":
            mismatch_fields.append(label)
        elif field_status == "REVIEW":
            review_fields.append(label)

    has_verification_entry = any(
        entry.get("step") == "Verification"
        for entry in entries
    )

    if verification_status and not has_verification_entry:
        if verification_status == "MISMATCH":
            entries.append({
                "state": "error",
                "step": "Verification",
                "message": (
                    "Mismatch detected"
                    + (
                        f": {', '.join(mismatch_fields)}"
                        if mismatch_fields
                        else ""
                    )
                ),
            })

        elif verification_status == "NEEDS_REVIEW":
            entries.append({
                "state": "review",
                "step": "Verification",
                "message": (
                    "Human review required"
                    + (
                        f": {', '.join(review_fields)}"
                        if review_fields
                        else ""
                    )
                ),
            })

        elif verification_status == "OK":
            entries.append({
                "state": "ok",
                "step": "Verification",
                "message": "All required fields verified",
            })

    final_status = str(
        result.get("status") or "unknown"
    ).replace("_", " ").title()

    final_state = "ok"

    if str(result.get("status") or "").lower() == "mismatch":
        final_state = "error"
    elif str(result.get("status") or "").lower() == "human_review":
        final_state = "review"
    elif str(result.get("status") or "").lower() == "failed":
        final_state = "error"

    entries.append({
        "state": final_state,
        "step": "Final Result",
        "message": final_status,
    })

    return entries


def render_processing_log(result, email_id):
    with st.expander(
        f"Processing Log — {email_id}",
        expanded=False,
    ):
        if not isinstance(result, dict):
            st.info(
                "No processing trace is available yet. "
                "Run Full Analysis or open an analysed case first."
            )
            return

        entries = _processing_log_entries(result)

        if not entries:
            st.info(
                "No processing trace is available for this email."
            )
            return

        for index, entry in enumerate(entries, start=1):
            state = entry["state"]

            if state == "error":
                icon = "✕"
                color = "#dc2626"
            elif state == "review":
                icon = "!"
                color = "#d97706"
            else:
                icon = "✓"
                color = "#16a34a"

            st.markdown(
                f"""
                <div style="
                    display:grid;
                    grid-template-columns:34px 120px 1fr;
                    gap:10px;
                    align-items:start;
                    padding:9px 4px;
                    border-bottom:1px solid
                    color-mix(
                        in srgb,
                        var(--st-text-color) 10%,
                        transparent
                    );
                ">
                    <div style="
                        font-size:11px;
                        opacity:.55;
                        padding-top:2px;
                    ">
                        {index:02d}
                    </div>

                    <div style="
                        font-size:11px;
                        font-weight:750;
                        color:{color};
                        -webkit-text-fill-color:{color};
                    ">
                        {html.escape(icon)}
                        {html.escape(entry["step"])}
                    </div>

                    <div style="
                        font-size:12px;
                        line-height:1.45;
                        color:var(--st-text-color);
                        -webkit-text-fill-color:var(--st-text-color);
                    ">
                        {html.escape(entry["message"])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
