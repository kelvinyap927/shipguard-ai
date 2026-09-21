import json
from pathlib import Path

import streamlit as st


SNAPSHOT_PATH = Path("demo_snapshot.json")


def save_demo_snapshot(results, summary, total_records):
    results = results or []
    summary = summary or {}

    if len(results) != total_records:
        return False, (
            f"Snapshot requires {total_records} analysed records. "
            f"Current result count is {len(results)}."
        )

    payload = {
        "version": 1,
        "total_records": total_records,
        "summary": summary,
        "results": results,
    }

    SNAPSHOT_PATH.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    return True, "Demo snapshot saved successfully."


def load_demo_snapshot(total_records):
    if not SNAPSHOT_PATH.exists():
        return None

    try:
        payload = json.loads(
            SNAPSHOT_PATH.read_text()
        )
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    if int(
        payload.get("total_records", 0)
    ) != int(total_records):
        return None

    results = payload.get("results") or []
    summary = payload.get("summary") or {}

    if len(results) != total_records:
        return None

    return {
        "results": results,
        "summary": summary,
    }


def restore_demo_snapshot(total_records):
    snapshot = load_demo_snapshot(
        total_records
    )

    if snapshot is None:
        return False

    existing_results = (
        st.session_state.get(
            "full_analysis_results"
        )
        or []
    )

    if len(existing_results) >= total_records:
        return False

    st.session_state[
        "full_analysis_results"
    ] = snapshot["results"]

    st.session_state[
        "full_analysis_summary"
    ] = snapshot["summary"]

    st.session_state[
        "full_analysis_index"
    ] = total_records

    counts = {
        "OK": int(
            snapshot["summary"].get(
                "ok",
                0,
            )
        ),
        "MISMATCH": int(
            snapshot["summary"].get(
                "mismatch",
                0,
            )
        ),
        "NEEDS_REVIEW": int(
            snapshot["summary"].get(
                "needs_review",
                0,
            )
        ),
    }

    st.session_state[
        "full_analysis_counts"
    ] = counts

    st.session_state[
        "full_analysis_failures"
    ] = int(
        snapshot["summary"].get(
            "failed",
            0,
        )
    )

    st.session_state[
        "full_analysis_status"
    ] = "complete"

    return True
