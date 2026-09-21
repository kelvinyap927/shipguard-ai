import streamlit as st
import pandas as pd
from datetime import datetime
import html
import re
from modules.inbox import load_inbox
from modules.classifier import classify_email
from modules.pipeline import process_email
from modules.batch_processor import process_batch
from modules.result_aggregator import aggregate_result
from modules.verification_adapter import build_verification_payload
from member_c_verifier import apply_human_correction
from theme import inject_theme_css
from wow_features import inject_wow_css, status_badge_html, confidence_bar_html, render_processing_log
from export_report import render_export_button
from discrepancy_intelligence import render_discrepancy_intelligence
from demo_snapshot import restore_demo_snapshot, save_demo_snapshot

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="ShipGuard AI",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------
# HTML rendering compatibility fix.
# Multiline HTML passed to st.markdown can accidentally become a Markdown
# code block when Python indentation is preserved. The wrapper below removes
# leading whitespace only for unsafe HTML blocks, so cards and badges render
# consistently without changing normal Markdown behaviour.
# ------------------------------------------------------------
_original_markdown = st._main.markdown


def _dedented_markdown(body="", *args, **kwargs):
    if kwargs.get("unsafe_allow_html") and isinstance(body, str):
        body = "\n".join(
            line.lstrip()
            for line in body.split("\n")
        )

    return _original_markdown(
        body,
        *args,
        **kwargs,
    )


st.markdown = _dedented_markdown


inject_wow_css()


# ============================================================
# USER CONFIGURATION
# ============================================================

USER_NAME = "user"
USER_ROLE = "Operations Executive"
USER_INITIALS = "SY"
APP_VERSION = "2.0"
APP_STATUS = "Operational"


# ============================================================
# THEME / CSS
# ============================================================

st.markdown(
    """
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html,
body,
[class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: var(--st-background-color);
}

.block-container {
    max-width: 1500px;
    padding-top: 1.1rem;
    padding-bottom: 2rem;
}

/* ============================================================
   SIDEBAR
   ============================================================ */

section[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #102d4b 0%,
        #0a2038 55%,
        #081b30 100%
    ) !important;

    border-right: 1px solid rgba(255,255,255,.06);
}

section[data-testid="stSidebar"] > div {
    padding: 0.9rem 0.75rem 0.8rem;
}

section[data-testid="stSidebar"] .stRadio > label {
    display: none;
}

section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
    display: none;
}

section[data-testid="stSidebar"] div[role="radiogroup"] {
    gap: 4px;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label {
    border-radius: 8px;
    padding: 9px 10px !important;
    margin: 0 !important;
    min-height: 38px;
    background: transparent;
    transition: all .15s ease;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
    background: rgba(255,255,255,.075);
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] {
    background: linear-gradient(
        90deg,
        #1e67a8 0%,
        #236eae 100%
    );

    box-shadow:
        inset 0 0 0 1px rgba(255,255,255,.07),
        0 5px 15px rgba(0,0,0,.13);
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label > div:first-child {
    display: none;
}

/* Sidebar navigation text */

section[data-testid="stSidebar"] div[role="radiogroup"] > label,
section[data-testid="stSidebar"] div[role="radiogroup"] > label p,
section[data-testid="stSidebar"] div[role="radiogroup"] > label span,
section[data-testid="stSidebar"] div[role="radiogroup"] > label div,
section[data-testid="stSidebar"] div[role="radiogroup"] > label * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-size: 13px !important;
    font-weight: 500 !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"],
section[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] p,
section[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* Brand */

.shipguard-brand {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 8px 18px;
}

.shipguard-logo {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    background: rgba(255,255,255,.1);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,.08);
    color: #ffffff;
}

.shipguard-name {
    color: #ffffff;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -.3px;
}

.shipguard-subtitle {
    color: #91a9c1;
    font-size: 10px;
    margin-top: 1px;
}

.sidebar-divider {
    height: 1px;
    background: rgba(255,255,255,.10);
    margin: 8px 3px 13px;
}

.sidebar-section {
    color: #ffffff !important;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: .8px;
    text-transform: uppercase;
    padding: 3px 9px 7px;
}

/* User */

.sidebar-user-box {
    margin: 12px 3px 2px;
    padding: 8px;
    border-radius: 10px;
    background: rgba(255,255,255,.055);
}

/* Keep the account controls visible during long dashboard views. */
section[data-testid="stSidebar"] > div {
    padding-bottom: 150px !important;
}

.st-key-sidebar_account_footer {
    position: fixed !important;
    left: 12px;
    bottom: 12px;
    width: 292px;
    z-index: 1000;
    padding: 10px 10px 7px;
    border: 1px solid rgba(255,255,255,.10);
    border-radius: 14px;
    background: linear-gradient(
        180deg,
        rgba(13, 42, 69, .98),
        rgba(8, 29, 51, .99)
    );
    box-shadow: 0 -8px 28px rgba(0,0,0,.18);
    backdrop-filter: blur(12px);
}

.st-key-sidebar_account_footer [data-testid="stPopover"] {
    margin-top: 3px;
}

.sidebar-avatar {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: #eef5fb;
    color: #183653;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
}

.sidebar-user-name {
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
}

.sidebar-user-role {
    color: #8ea7c0;
    font-size: 9px;
    margin-top: 1px;
}

.sidebar-status {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #2fc58b;
    box-shadow: 0 0 0 3px rgba(47,197,139,.12);
}

/* ============================================================
   GENERAL
   ============================================================ */

h1,
h2,
h3 {
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
}

h1 {
    font-weight: 700;
}

h2,
h3 {
    font-weight: 600;
}

p,
li,
.stMarkdown,
.stCaption,
.stTextInput,
.stSelectbox,
.stButton {
    font-size: 14px;
}

.small-muted {
    color: #71839b;
    font-size: 0.82rem;
}

.panel {
    background: #f8fafc;
    border: 1px solid #e3ebf5;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 4px 18px rgba(23, 54, 90, .045);
}

.panel-title {
    font-weight: 700;
    color: #18304f;
    margin-bottom: 4px;
    font-size: 14px;
}

hr {
    border: none;
    border-top: 1px solid #e8eef5;
    margin: 12px 0;
}

/* ============================================================
   OVERVIEW CARDS
   ============================================================ */

.overview-title {
    color: #18304f;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 8px;
}

.metric-strip {
    display: flex;
    gap: 10px;
    width: 100%;
    margin-bottom: 18px;
}

.metric-card {
    width: 100%;
    min-height: 92px;
    background: #f8fafc;
    border: 1px solid #e3ebf5;
    border-radius: 12px;
    padding: 11px 13px;
    box-shadow: 0 3px 13px rgba(23, 54, 90, .04);
    box-sizing: border-box;
}

.metric-title {
    font-size: 11px;
    color: #657992;
    margin-bottom: 4px;
    white-space: nowrap;
}

.metric-value {
    font-size: 21px;
    font-weight: 700;
    color: #142a47;
}

.metric-label {
    font-size: 10px;
    margin-top: 2px;
    color: #71839b;
}

.type-document {
    border-top: 3px solid #8b5cf6;
}

.type-si {
    border-top: 3px solid #f97316;
}

.type-invoice {
    border-top: 3px solid #3b82f6;
}

.type-operational {
    border-top: 3px solid #10b981;
}

.type-spam {
    border-top: 3px solid #ef4444;
}

/* ============================================================
   TABLE
   ============================================================ */

.priority-wrapper {
    background: #f8fafc;
    border: 1px solid #e3ebf5;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 4px 18px rgba(23, 54, 90, .045);
}

.priority-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 14px;
}

.priority-title {
    font-size: 16px;
    font-weight: 700;
    color: #18304f;
}

.table-box {
    border: 1px solid #e2e9f1;
    border-radius: 11px;
    overflow: hidden;
    background: #f8fafc;
}

.table-head {
    background: #f7f9fc;
    border-bottom: 1px solid #e2e9f1;
    padding: 9px 12px;
    color: #71839b;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: .4px;
}

.priority-row {
    padding: 11px 12px;
    border-bottom: 1px solid #edf1f5;
}

.priority-row:last-child {
    border-bottom: none;
}

.subject-text {
    color: #233b57;
    font-size: 13px;
    font-weight: 500;
}

.shipment-text {
    color: #71839b;
    font-size: 11px;
}

.received-text {
    color: #667b93;
    font-size: 11px;
}

/* ============================================================
   BADGES
   ============================================================ */

.type-badge {
    display: inline-block;
    border-radius: 999px;
    padding: 4px 8px;
    font-size: 10px;
    font-weight: 600;
}

.type-badge-document {
    background: #8b5cf6;
    color: #ffffff;
}

.type-badge-si {
    background: #f97316;
    color: #ffffff;
}

.type-badge-invoice {
    background: #3b82f6;
    color: #ffffff;
}

.type-badge-operational {
    background: #10b981;
    color: #ffffff;
}

.type-badge-spam {
    background: #ef4444;
    color: #ffffff;
}

.badge {
    display: inline-block;
    border-radius: 999px;
    padding: 4px 9px;
    font-size: 10px;
    font-weight: 600;
}

.badge-red {
    background: #ef4444;
    color: #ffffff;
}

.badge-orange {
    background: #f59e0b;
    color: #ffffff;
}

.badge-green {
    background: #10b981;
    color: #ffffff;
}

.badge-blue {
    background: #3b82f6;
    color: #ffffff;
}

/* ============================================================
   CASE PAGE
   ============================================================ */

.case-banner {
    background: linear-gradient(90deg, #eef6ff, #ffffff);
    border: 1px solid #dce9f7;
    border-radius: 14px;
    padding: 17px 20px;
}

.discrepancy {
    background: #fff4f4;
    border: 1px solid #ef4444;
    border-radius: 12px;
    padding: 15px;
}

.info-box {
    background: #f8fbff;
    border: 1px solid #e5eef8;
    border-radius: 12px;
    padding: 14px;
}

.action-box {
    background: #f8fafc;
    border: 1px solid #e1eaf4;
    border-radius: 12px;
    padding: 14px;
}

/* ============================================================
   AI SUMMARY
   ============================================================ */

.ai-summary {
    background: #f8fbff;
    border: 1px solid #dfeaf7;
    border-radius: 12px;
    padding: 14px;
}

.ai-summary-title {
    color: #18304f;
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 10px;
}

.ai-summary-label {
    color: #71839b;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: .5px;
    font-weight: 700;
}

.ai-summary-value {
    color: #233b57;
    font-size: 13px;
    font-weight: 600;
    margin-top: 2px;
}

/* ============================================================
   ACTIVITY
   ============================================================ */

.activity-item {
    padding: 11px 0;
    border-bottom: 1px solid #edf1f5;
}

.activity-item:last-child {
    border-bottom: none;
}

.activity-title {
    color: #233b57;
    font-size: 12px;
    font-weight: 600;
}

.activity-meta {
    color: #71839b;
    font-size: 10px;
    margin-top: 3px;
}

/* ============================================================
   DOCUMENT CARD
   ============================================================ */

.doc-card {
    border: 1px solid #dfe9f5;
    border-radius: 14px;
    padding: 14px;
    background: linear-gradient(
        135deg,
        #ffffff 0%,
        #f8fbff 100%
    );
    box-shadow: 0 5px 20px rgba(36,76,120,.06);
}

/* ============================================================
   OTHER
   ============================================================ */

.page-accent {
    height: 4px;
    width: 72px;
    border-radius: 999px;
    background: linear-gradient(
        90deg,
        #3b82f6,
        #8b5cf6,
        #ec4899
    );
    margin: 0 0 16px 0;
}

.status-card {
    border-radius: 10px;
    padding: 9px 10px;
    background: rgba(59,130,246,.08);
    border: 1px solid rgba(59,130,246,.15);
    margin-top: 8px;
}

.status-label {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: .7px;
    font-weight: 700;
    color: #71839b;
}

.status-value {
    font-size: 16px;
    font-weight: 700;
    color: #2563eb;
}

div[data-testid="stButton"] > button {
    border-radius: 9px;
    border: 1px solid #dbe7f3;
    font-weight: 500;
}

/* Sidebar account button */

section[data-testid="stSidebar"] div[data-testid="stPopover"] button {
    color: #ffffff !important;
}

/* ============================================================
   LOGGED OUT
   ============================================================ */

.logout-box {
    max-width: 520px;
    margin: 100px auto;
    background: #f8fafc;
    border: 1px solid #e3ebf5;
    border-radius: 16px;
    padding: 35px;
    text-align: center;
    box-shadow: 0 8px 30px rgba(23,54,90,.08);
}



/* ============================================================
   ACCESSIBILITY + ADVANCED UI
   ============================================================ */

section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] small,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: #c9d8e8 !important;
    opacity: 1 !important;
}

section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] [data-testid="stText"],
section[data-testid="stSidebar"] label {
    color: #f4f8fc !important;
}

section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] textarea {
    color: #10243b !important;
    background: #f7fbff !important;
}

.small-muted,
.metric-label,
.shipment-text,
.received-text,
.activity-meta,
.status-label,
.ai-summary-label {
    color: #526b86 !important;
}

.sidebar-subtle {
    color: #c9d8e8 !important;
}

.command-strip {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    margin: 0 0 18px 0;
}

.command-chip {
    background: linear-gradient(135deg, #ffffff 0%, #f4f8fd 100%);
    border: 1px solid #d5e2ef;
    border-radius: 12px;
    padding: 11px 13px;
    box-shadow: 0 4px 16px rgba(23,54,90,.05);
}

.command-chip-label {
    color: #526b86;
    font-size: 9px;
    font-weight: 800;
    letter-spacing: .7px;
    text-transform: uppercase;
}

.command-chip-value {
    color: #102b48;
    font-size: 17px;
    font-weight: 800;
    margin-top: 2px;
}

.health-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #16a878;
    box-shadow: 0 0 0 4px rgba(22,168,120,.12);
    margin-right: 6px;
}

.confidence-high {
    color: #087f5b !important;
    background: #e7f8f1;
    border-color: #bdebdc;
}
.confidence-medium {
    color: #9a6700 !important;
    background: #fff7db;
    border-color: #f4df9c;
}
.confidence-low {
    color: #a33a3a !important;
    background: #fff0f0;
    border-color: #f2c7c7;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    color: #10243b !important;
    background: #f7fbff !important;
    border-color: #d7e4f0 !important;
}

section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {
    color: #ffffff !important;
    border-color: #4f8fbd !important;
    background: #174d79 !important;
}

div[data-testid="stButton"] > button:hover {
    border-color: #9db8d2;
    box-shadow: 0 4px 12px rgba(32,73,116,.08);
}

div[data-testid="stMetric"] {
    background: #f8fafc;
    border: 1px solid #dce7f1;
    border-radius: 12px;
    padding: 10px 12px;
}

@media (max-width: 900px) {
    .command-strip { grid-template-columns: repeat(2, 1fr); }
}


/* ============================================================
   COMPETITION-READY UI LAYER
   ============================================================ */
.sg-section-label {
    color:#355b7d !important;
    font-size:11px;
    font-weight:800;
    letter-spacing:.85px;
    text-transform:uppercase;
    margin:2px 0 9px;
}
.sg-insight-grid {
    display:grid;
    grid-template-columns:1.25fr 1fr 1fr;
    gap:12px;
    margin:0 0 20px;
}
.sg-insight-card {
    position:relative;
    overflow:hidden;
    min-height:118px;
    padding:15px 16px;
    border:1px solid #d8e5f0;
    border-radius:14px;
    background:linear-gradient(145deg,#ffffff 0%,#f6faff 100%);
    box-shadow:0 6px 22px rgba(24,59,92,.055);
}
.sg-insight-card:after {
    content:""; position:absolute; width:90px; height:90px;
    right:-30px; bottom:-38px; border-radius:50%;
    background:rgba(38,116,176,.055);
}
.sg-insight-title { color:#526b86; font-size:10px; font-weight:800; letter-spacing:.55px; text-transform:uppercase; }
.sg-insight-value { color:#102943; font-size:26px; line-height:1.05; font-weight:800; margin-top:6px; }
.sg-insight-copy { color:#526b86; font-size:11px; line-height:1.45; margin-top:5px; max-width:92%; }
.sg-progress { height:6px; margin-top:11px; background:#e7eef5; border-radius:999px; overflow:hidden; }
.sg-progress > span { display:block; height:100%; border-radius:999px; background:linear-gradient(90deg,#1c6aa5,#4a9bd0); }
.sg-ai-callout {
    margin:0 0 18px; padding:12px 14px; border:1px solid #d5e5f2;
    border-radius:12px; background:linear-gradient(90deg,#f2f8fd,#ffffff);
    display:flex; align-items:center; justify-content:space-between; gap:12px;
}
.sg-ai-callout-title { color:#173a5b; font-size:12px; font-weight:800; }
.sg-ai-callout-copy { color:#526b86; font-size:10px; margin-top:2px; }
.sg-ai-badge {
    white-space:nowrap; padding:6px 9px; border-radius:999px;
    background:#eaf5ff; color:#1769aa; border:1px solid #cfe3f4;
    font-size:9px; font-weight:800;
}
.sg-kpi-icon {
    width:28px; height:28px; border-radius:8px; display:flex;
    align-items:center; justify-content:center; background:#edf5fb;
    color:#1769aa; font-size:12px; font-weight:800; margin-bottom:7px;
}
@media (max-width: 900px) {
    .sg-insight-grid { grid-template-columns:1fr; }
    .sg-ai-callout { align-items:flex-start; flex-direction:column; }
}

/* ============================================================
   ADVANCED PRODUCT UI OVERRIDES
   ============================================================ */
:root {
    --sg-navy: #0b1f35;
    --sg-blue: #1769aa;
    --sg-blue-2: #2b7bbb;
    --sg-ink: #14263d;
    --sg-muted: #526b86;
    --sg-border: #d8e4ef;
    --sg-surface: #ffffff;
    --sg-surface-2: #f5f8fc;
    --sg-success: #087f5b;
    --sg-warning: #9a6700;
    --sg-danger: #b42318;
}

.stApp {
    background:
        radial-gradient(circle at 90% -10%, rgba(39,119,190,.08), transparent 28%),
        linear-gradient(180deg, #f7faff 0%, #f2f6fb 100%);
}

.block-container {
    max-width: 1540px !important;
    padding-left: clamp(1rem, 2.2vw, 2.2rem) !important;
    padding-right: clamp(1rem, 2.2vw, 2.2rem) !important;
}

/* Make all normal text comfortably readable. */
.stMarkdown, .stText, p, li, label, [data-testid="stCaptionContainer"] {
    color: var(--sg-ink);
}

[data-testid="stCaptionContainer"] {
    color: var(--sg-muted) !important;
    opacity: 1 !important;
}

/* Inputs */
div[data-baseweb="input"] > div,
div[data-baseweb="select"] > div,
textarea,
input {
    border-radius: 10px !important;
    border-color: #cbd9e7 !important;
}

div[data-baseweb="input"] > div:focus-within,
div[data-baseweb="select"] > div:focus-within,
textarea:focus,
input:focus {
    border-color: #4c91c7 !important;
    box-shadow: 0 0 0 3px rgba(76,145,199,.13) !important;
}

/* Buttons */
div[data-testid="stButton"] > button,
[data-testid="baseButton-secondary"],
[data-testid="baseButton-primary"] {
    min-height: 38px;
    border-radius: 10px !important;
    font-weight: 650 !important;
    letter-spacing: -.05px;
    transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
}

div[data-testid="stButton"] > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 7px 18px rgba(31,73,112,.11);
}

/* Modern top utility bar */
.sg-topbar {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:18px;
    padding:10px 14px;
    margin:0 0 18px;
    background:rgba(255,255,255,.92);
    border:1px solid #dbe6f0;
    border-radius:14px;
    box-shadow:0 5px 22px rgba(31,65,98,.055);
    backdrop-filter:blur(10px);
}
.sg-topbar-left { display:flex; align-items:center; gap:10px; min-width:0; }
.sg-topbar-mark {
    width:32px; height:32px; border-radius:9px;
    display:flex; align-items:center; justify-content:center;
    color:#fff; font-size:11px; font-weight:800;
    background:linear-gradient(135deg,#124d7f,#2b7bbb);
    box-shadow:0 5px 14px rgba(28,93,145,.18);
}
.sg-topbar-title { font-size:13px; font-weight:800; color:#102943; }
.sg-topbar-path { font-size:10px; color:#667e96; margin-top:1px; }
.sg-topbar-right { display:flex; align-items:center; gap:8px; }
.sg-live-pill {
    display:flex; align-items:center; gap:7px;
    padding:7px 10px; border-radius:999px;
    background:#eef9f5; border:1px solid #ccecdf;
    color:#087f5b; font-size:10px; font-weight:750;
}
.sg-live-dot { width:7px; height:7px; border-radius:50%; background:#12a66b; box-shadow:0 0 0 3px rgba(18,166,107,.12); }
.sg-shortcut {
    padding:7px 10px; border-radius:8px;
    background:#f5f8fc; border:1px solid #dbe5ef;
    color:#526b86; font-size:10px; font-weight:650;
}

/* Hero / page header */
.sg-hero {
    position:relative;
    overflow:hidden;
    padding:22px 24px;
    margin-bottom:18px;
    border:1px solid #d9e5ef;
    border-radius:16px;
    background:linear-gradient(135deg,#ffffff 0%,#f4f9fe 72%,#eef6fd 100%);
    box-shadow:0 7px 26px rgba(28,65,100,.055);
}
.sg-hero:after {
    content:""; position:absolute; width:180px; height:180px; right:-70px; top:-95px;
    border-radius:50%; background:rgba(44,124,187,.08);
}
.sg-eyebrow { color:#3675a3; font-size:10px; font-weight:800; letter-spacing:1px; text-transform:uppercase; }
.sg-hero-title { color:#102943; font-size:28px; line-height:1.15; font-weight:800; margin-top:4px; }
.sg-hero-copy { color:#526b86; font-size:13px; margin-top:7px; max-width:760px; }

/* Cards feel like a real operations product */
.metric-card, .priority-wrapper, .panel, .action-box, .doc-card, .ai-summary {
    box-shadow:0 6px 24px rgba(24,59,92,.055) !important;
}

.metric-card:hover, .doc-card:hover {
    border-color:#bfd3e5;
    box-shadow:0 9px 26px rgba(24,59,92,.085) !important;
}

/* Better table rows */
.priority-row, .table-box { background:#fff; }
.priority-row:hover { background:#f8fbfe; }
.table-head { color:#536c85 !important; background:#f3f7fb !important; }
.subject-text { color:#183653 !important; font-weight:650 !important; }
.shipment-text, .received-text { color:#526b86 !important; }

/* Streamlit metrics */
div[data-testid="stMetric"] label,
div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
    color:#526b86 !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color:#102943 !important;
}

/* Expander / tabs */
details[data-testid="stExpander"] {
    border:1px solid #dbe5ef !important;
    border-radius:12px !important;
    background:#fff !important;
}
button[data-baseweb="tab"] { color:#526b86 !important; font-weight:650 !important; }
button[data-baseweb="tab"][aria-selected="true"] { color:#1769aa !important; }

/* Sidebar: high contrast and polished */
section[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#0c2945 0%,#081d33 100%) !important;
}
section[data-testid="stSidebar"] .shipguard-subtitle,
section[data-testid="stSidebar"] .sidebar-user-role,
section[data-testid="stSidebar"] .sidebar-subtle { color:#c5d7e8 !important; }
section[data-testid="stSidebar"] .sidebar-section { color:#f2f7fb !important; opacity:1 !important; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label:hover { background:rgba(255,255,255,.10) !important; }
section[data-testid="stSidebar"] div[role="radiogroup"] > label[data-checked="true"] {
    background:linear-gradient(90deg,#1b68a5,#287ab9) !important;
    box-shadow:inset 0 0 0 1px rgba(255,255,255,.10),0 7px 18px rgba(0,0,0,.18) !important;
}

/* Accessibility */
*:focus-visible { outline:3px solid rgba(46,126,190,.28) !important; outline-offset:2px; }
@media (max-width: 900px) {
    .sg-topbar-right .sg-shortcut { display:none; }
    .sg-hero-title { font-size:23px; }
}


/* ============================================================
   DOCUMENT REVIEW READABILITY — HIGH CONTRAST
   Never use white text on light review surfaces.
   ============================================================ */
.case-banner,
.case-banner h1,
.case-banner h2,
.case-banner h3,
.case-banner p,
.case-banner span,
.case-banner div {
    color: #102943;
}
.case-banner h2 {
    color: #0f2942 !important;
    font-size: 24px !important;
    line-height: 1.28 !important;
    font-weight: 800 !important;
}
.case-banner > div:first-child {
    color: #42627e !important;
}
.case-banner .small-muted,
.case-banner [style*="color:#70839a"] {
    color: #526b86 !important;
}

/* Light review cards always use dark readable text. */
.panel,
.panel *:not(.badge):not(.type-badge),
.info-box,
.info-box *:not(.badge):not(.type-badge),
.action-box,
.action-box *:not(.badge):not(.type-badge),
.ai-summary,
.ai-summary *:not(.badge):not(.type-badge),
.discrepancy,
.discrepancy *:not(.badge):not(.type-badge) {
    -webkit-text-fill-color: currentColor;
}
.panel,
.panel p,
.panel li,
.panel span,
.panel div,
.panel label,
.info-box,
.info-box p,
.info-box span,
.info-box div,
.action-box,
.action-box p,
.action-box span,
.action-box div,
.ai-summary,
.ai-summary p,
.ai-summary span,
.ai-summary div {
    color: #183653 !important;
}
.panel-title {
    color: #102943 !important;
    font-weight: 800 !important;
}

/* Discrepancy warning: dark ink on pale warning background. */
.discrepancy {
    background: #fff8f7 !important;
    border: 1px solid #e7a29a !important;
    color: #172b40 !important;
}
.discrepancy b,
.discrepancy strong {
    color: #9f2d23 !important;
    font-weight: 800 !important;
}
.discrepancy .small-muted,
.discrepancy span.small-muted {
    color: #38536d !important;
    font-size: 12px !important;
    line-height: 1.55 !important;
}
.discrepancy span[style] {
    color: #203b54 !important;
    line-height: 1.55 !important;
}

/* Suggested actions: readable text and stronger visual affordance. */
.action-box {
    background: #f5f9fd !important;
    border: 1px solid #d3e1ee !important;
    color: #173853 !important;
    font-size: 13px !important;
    line-height: 1.55 !important;
    font-weight: 550 !important;
}
.action-box:hover {
    background: #edf5fb !important;
    border-color: #b9d2e6 !important;
}

/* AI explanation and comparison values. */
.ai-summary-label {
    color: #49657f !important;
    opacity: 1 !important;
}
.ai-summary-value {
    color: #16334e !important;
    font-weight: 700 !important;
}

/* Comparison tabs and their content. */
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    border-bottom: 1px solid #d8e4ef;
}
.stTabs [data-baseweb="tab"] {
    color: #45617b !important;
    font-weight: 700 !important;
    opacity: 1 !important;
}
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span {
    color: #45617b !important;
}
.stTabs [aria-selected="true"],
.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span {
    color: #145f99 !important;
}

/* Streamlit captions are often too faint on document-review screens. */
.stTabs [data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] {
    color: #4d6780 !important;
    opacity: 1 !important;
    font-weight: 500 !important;
}

/* Review-page native text inputs/text areas. */
.stTextInput label,
.stTextArea label,
.stSelectbox label,
.stMultiSelect label {
    color: #243f59 !important;
    font-weight: 700 !important;
}
.stTextInput input,
.stTextArea textarea,
.stSelectbox [data-baseweb="select"] * {
    color: #102943 !important;
    -webkit-text-fill-color: #102943 !important;
}

/* Record list/table: every field remains readable on white rows. */
.table-box,
.table-box * {
    color: #183653;
}
.table-head,
.table-head * {
    color: #3f5d77 !important;
}
.priority-row .subject-text,
.priority-row .shipment-text,
.priority-row .received-text {
    color: #183653 !important;
    opacity: 1 !important;
}
.priority-row .shipment-text,
.priority-row .received-text {
    color: #506b85 !important;
}

/* Native Streamlit success/info messages: readable dark text. */
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span {
    color: #183653 !important;
    opacity: 1 !important;
}

/* Keep intentional coloured badges readable. */
.badge,
.type-badge,
.badge *,
.type-badge * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* Accessibility and interaction polish */
.stApp { color: #0f172a; }
[data-testid="stSidebar"] { background: #0f172a !important; border-right: 1px solid #334155 !important; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
[data-testid="stSidebar"] label { color: #e2e8f0 !important; opacity: 1 !important; }
[data-testid="stSidebar"] button { color: #e2e8f0 !important; background: transparent !important; border-color: transparent !important; }
[data-testid="stSidebar"] button:hover { background: #1e293b !important; color: #ffffff !important; }
button[kind="secondary"], button[kind="primary"] { transition: background .15s ease, border-color .15s ease, transform .15s ease; }
button[kind="secondary"]:hover { background: #e0e7ff !important; color: #1e3a8a !important; border-color: #93c5fd !important; }
button[kind="primary"]:hover { background: #1d4ed8 !important; color: #ffffff !important; border-color: #2563eb !important; }
[data-testid="stButton"] button { min-height: 42px; font-weight: 650; }
[data-testid="stMetric"] { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 14px; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea { color: #0f172a !important; background: #ffffff !important; }
[data-baseweb="select"] * { color: #0f172a !important; }
/* FINAL INTERACTION + TOP-CHROME CONTRAST PASS */
/* View/action buttons start quiet and become blue only on hover/focus. */
div[data-testid="stButton"] > button {
    background: #f8fbfe !important;
    color: #173653 !important;
    -webkit-text-fill-color: #173653 !important;
    border: 1px solid #d5e3ef !important;
    box-shadow: none !important;
}
div[data-testid="stButton"] > button:hover,
div[data-testid="stButton"] > button:focus-visible,
div[data-testid="stButton"] > button:active {
    background: #2f7fba !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-color: #2f7fba !important;
    box-shadow: 0 6px 16px rgba(47,127,186,.20) !important;
}
/* Sidebar controls use the same readable dark-on-light idle state. */
section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
    background: rgba(255,255,255,.08) !important;
    color: #f4f8fc !important;
    -webkit-text-fill-color: #f4f8fc !important;
    border-color: rgba(255,255,255,.16) !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover,
section[data-testid="stSidebar"] div[data-testid="stButton"] > button:focus-visible {
    background: #2f7fba !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border-color: #5ba1d2 !important;
}
/* Keep the Streamlit sidebar arrow visible, but remove the dark chrome. */
header[data-testid="stHeader"] {
    background: #f7fbff !important;
    height: 52px !important;
    border-bottom: 1px solid #dbe7f1 !important;
}
button[data-testid="stSidebarCollapseButton"] {
    background: #eaf4fc !important;
    color: #174b70 !important;
    border: 1px solid #c7deee !important;
    border-radius: 9px !important;
    box-shadow: 0 2px 8px rgba(28,74,110,.08) !important;
}
button[data-testid="stSidebarCollapseButton"] svg {
    color: #174b70 !important;
    fill: #174b70 !important;
    stroke: #174b70 !important;
}
button[data-testid="stSidebarCollapseButton"]:hover {
    background: #dceefb !important;
    color: #123f5e !important;
}
/* Give the application enough breathing room below Streamlit's header. */
.block-container { padding-top: 2.25rem !important; }
/* Top utility bar remains fully visible on every page. */
.sg-topbar { min-height: 54px; }
.sg-topbar-title, .sg-topbar-path, .sg-shortcut, .sg-live-pill { opacity: 1 !important; }
.sg-topbar-title { color: #102943 !important; }
.sg-topbar-path, .sg-shortcut { color: #526b86 !important; }
.sg-live-pill { color: #087f5b !important; }
/* Account popover: obvious text on a light menu surface. */
section[data-testid="stSidebar"] div[data-testid="stPopover"] {
    color: #173653 !important;
}
section[data-testid="stSidebar"] div[data-testid="stPopover"] button {
    background: #ffffff !important;
    color: #173653 !important;
    -webkit-text-fill-color: #173653 !important;
    border-color: #d6e3ee !important;
}
section[data-testid="stSidebar"] div[data-testid="stPopover"] button:hover {
    background: #eaf4fc !important;
    color: #155b8d !important;
    -webkit-text-fill-color: #155b8d !important;
}
/* Settings navigation button. */
button[key="settings_back"] {
    background: #f8fbfe !important;
    color: #173653 !important;
    -webkit-text-fill-color: #173653 !important;
}
button[key="settings_back"]:hover {
    background: #2f7fba !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* Final contrast pass */
.stCaption, .stCaption p, [data-testid="stCaptionContainer"] p {
    color:#526b86 !important;
    opacity:1 !important;
}
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stTextArea"] label,
div[data-testid="stToggle"] label {
    color:#294663 !important;
    font-weight:650 !important;
}

</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
/* ============================================================
   STREAMLIT THEME SYNC
   Uses Streamlit theme variables so the full app follows the
   Light / Dark choice from the Streamlit menu.
   ============================================================ */

.stApp,
[data-testid="stAppViewContainer"] {
    background: var(--st-background-color) !important;
    color: var(--st-text-color) !important;
}

.block-container {
    color: var(--st-text-color) !important;
}

.sg-topbar {
    background: var(--st-background-color) !important;
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 14%,
        transparent
    ) !important;
}

.sg-topbar-title,
.sg-topbar-path,
.sg-shortcut {
    color: var(--st-text-color) !important;
}

.sg-hero {
    background: linear-gradient(
        135deg,
        var(--st-background-color) 0%,
        var(--st-secondary-background-color) 100%
    ) !important;
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 14%,
        transparent
    ) !important;
    box-shadow: 0 8px 28px rgba(0, 0, 0, .10) !important;
}

.sg-hero:after {
    background: color-mix(
        in srgb,
        var(--st-primary-color) 12%,
        transparent
    ) !important;
}

.sg-eyebrow {
    color: var(--st-primary-color) !important;
}

.sg-hero-title {
    color: var(--st-text-color) !important;
}

.sg-hero-copy {
    color: color-mix(
        in srgb,
        var(--st-text-color) 72%,
        transparent
    ) !important;
}

.panel,
.metric-card,
.status-card,
.action-box,
.table-box,
.document-summary,
.review-panel,
.priority-wrapper,
.doc-card,
.ai-summary,
.case-banner {
    background: var(--st-secondary-background-color) !important;
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 14%,
        transparent
    ) !important;
    color: var(--st-text-color) !important;
}

.metric-value,
.status-value,
.panel h1,
.panel h2,
.panel h3,
.panel p,
.document-summary *,
.review-panel *,
.action-box * {
    color: var(--st-text-color) !important;
}

.metric-label,
.status-label,
.sidebar-subtle,
.sg-hero-copy {
    color: color-mix(
        in srgb,
        var(--st-text-color) 70%,
        transparent
    ) !important;
}

[data-testid="stMetric"] {
    background: var(--st-secondary-background-color) !important;
    color: var(--st-text-color) !important;
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 14%,
        transparent
    ) !important;
}

[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p,
.stCaption,
.stCaption p {
    color: color-mix(
        in srgb,
        var(--st-text-color) 68%,
        transparent
    ) !important;
    opacity: 1 !important;
}

[data-testid="stToggle"] [data-testid="stWidgetLabel"],
[data-testid="stToggle"] [data-testid="stWidgetLabel"] p,
[data-testid="stToggle"] label,
[data-testid="stToggle"] label p,
[data-testid="stToggle"] label span,
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stTextArea"] label {
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
    opacity: 1 !important;
}

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div {
    background: var(--st-secondary-background-color) !important;
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 18%,
        transparent
    ) !important;
}

[data-testid="stButton"] > button {
    background: var(--st-secondary-background-color) !important;
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 18%,
        transparent
    ) !important;
}

[data-testid="stButton"] > button:hover,
[data-testid="stButton"] > button:focus-visible {
    background: color-mix(
        in srgb,
        var(--st-secondary-background-color) 80%,
        var(--st-primary-color) 20%
    ) !important;
    color: var(--st-text-color) !important;
    border-color: var(--st-primary-color) !important;
}

.stTabs [data-baseweb="tab-list"] {
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 14%,
        transparent
    ) !important;
}

.stTabs [data-baseweb="tab"],
.stTabs [data-baseweb="tab"] p,
.stTabs [data-baseweb="tab"] span {
    color: color-mix(
        in srgb,
        var(--st-text-color) 72%,
        transparent
    ) !important;
}

.stTabs [aria-selected="true"],
.stTabs [aria-selected="true"] p,
.stTabs [aria-selected="true"] span {
    color: var(--st-primary-color) !important;
}

div[data-testid="stAlert"] {
    background: var(--st-secondary-background-color) !important;
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 16%,
        transparent
    ) !important;
}

div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span {
    color: var(--st-text-color) !important;
}

.priority-row {
    background: var(--st-background-color) !important;
    color: var(--st-text-color) !important;
}

.priority-row:hover {
    background: var(--st-secondary-background-color) !important;
}

.table-head {
    background: var(--st-secondary-background-color) !important;
    color: var(--st-text-color) !important;
}

.sg-shortcut {
    background: var(--st-secondary-background-color) !important;
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 14%,
        transparent
    ) !important;
}

/* Keep status badges intentionally coloured. */
.badge,
.type-badge,
.badge *,
.type-badge * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* Overview metric accents */
.metric-card.type-document .metric-value {
    color: #8b5cf6 !important;
}

.metric-card.type-si .metric-value {
    color: #f97316 !important;
}

.metric-card.type-invoice .metric-value {
    color: #3b82f6 !important;
}

.metric-card.type-general .metric-value {
    color: #10b981 !important;
}

.metric-card.type-spam .metric-value {
    color: #ef4444 !important;
}

/* Final dashboard theme polish */

/* Keep main headings readable in both themes */
[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3,
[data-testid="stMain"] h4,
[data-testid="stMain"] h5,
[data-testid="stMain"] h6 {
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
}

/* Dashboard cards follow the selected Streamlit theme */
.sg-insight-card,
.sg-ai-callout,
.metric-card,
.panel,
.action-box,
.table-box,
.document-summary,
.review-panel,
.priority-wrapper,
.doc-card,
.ai-summary,
.status-card {
    background: var(--st-secondary-background-color) !important;
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 14%,
        transparent
    ) !important;
}

/* Dashboard text contrast */
.sg-insight-value,
.sg-ai-callout-title,
.metric-value,
.status-value {
    color: var(--st-text-color) !important;
}

.sg-insight-title,
.sg-insight-copy,
.sg-ai-callout-copy,
.metric-title,
.metric-label,
.status-label {
    color: color-mix(
        in srgb,
        var(--st-text-color) 72%,
        transparent
    ) !important;
}

/* Theme-aware progress tracks */
.sg-progress {
    background: color-mix(
        in srgb,
        var(--st-text-color) 12%,
        transparent
    ) !important;
}

/* Preserve category accent colours */
.metric-card.type-document .metric-value {
    color: #8b5cf6 !important;
}

.metric-card.type-si .metric-value {
    color: #f97316 !important;
}

.metric-card.type-invoice .metric-value {
    color: #3b82f6 !important;
}

.metric-card.type-general .metric-value,
.metric-card.type-update .metric-value {
    color: #10b981 !important;
}

.metric-card.type-spam .metric-value {
    color: #ef4444 !important;
}

/* Main analysis CTA */
button[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-primary"],
[data-testid="stButton"] button[kind="primary"] {
    background: #2563eb !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: 1px solid #2563eb !important;
    font-weight: 700 !important;
    box-shadow: 0 6px 18px rgba(37, 99, 235, .22) !important;
}

button[data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primary"]:hover,
[data-testid="stButton"] button[kind="primary"]:hover {
    background: #1d4ed8 !important;
    border-color: #1d4ed8 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    transform: translateY(-1px);
}

/* Keep coloured badges readable */
.badge,
.type-badge,
.badge *,
.type-badge * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

/* Top bar contrast in both themes */
.sg-topbar,
.sg-topbar-title,
.sg-topbar-title *,
.sg-topbar-path,
.sg-topbar-path *,
.sg-shortcut,
.sg-shortcut * {
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
    opacity: 1 !important;
}

.sg-shortcut {
    background: var(--st-secondary-background-color) !important;
    border-color: color-mix(
        in srgb,
        var(--st-text-color) 20%,
        transparent
    ) !important;
}

/* Keep the operational status pill green */
.sg-live-pill,
.sg-live-pill * {
    color: #087f5b !important;
    -webkit-text-fill-color: #087f5b !important;
    opacity: 1 !important;
}
</style>
""",
    unsafe_allow_html=True,
)


st.markdown(
    """
<style>
/* FINAL THEME CONTRAST OVERRIDES */

/* Top application bar */
.sg-topbar {
    background: var(--st-background-color) !important;
    border-color: var(--st-border-color) !important;
}

.sg-topbar-title,
.sg-topbar-title *,
.sg-topbar-path,
.sg-topbar-path *,
.sg-shortcut,
.sg-shortcut * {
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
    opacity: 1 !important;
}

.sg-shortcut {
    background: var(--st-secondary-background-color) !important;
    border-color: var(--st-border-color) !important;
}

/* Main page headings */
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
}

/* AI overview and workspace intelligence */
.sg-ai-callout-title,
.sg-ai-callout-copy,
.sg-insight-title,
.sg-insight-value,
.sg-insight-copy {
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
}

.sg-insight-copy,
.sg-ai-callout-copy {
    opacity: .72 !important;
}

/* Search and text inputs */
[data-testid="stTextInput"] input {
    background: var(--st-secondary-background-color) !important;
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
    border-color: var(--st-border-color) !important;
}

[data-testid="stTextInput"] input::placeholder {
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
    opacity: .55 !important;
}

/* Overview labels */
.metric-title,
.metric-label {
    color: var(--st-text-color) !important;
    -webkit-text-fill-color: var(--st-text-color) !important;
    opacity: .72 !important;
}

/* Keep the live status intentionally green */
.sg-live-pill,
.sg-live-pill * {
    color: #087f5b !important;
    -webkit-text-fill-color: #087f5b !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# FINAL THEME INJECTION
# ============================================================



# ============================================================
# FINAL THEME INJECTION
# ============================================================

inject_theme_css()


# ============================================================
# INITIAL DATA
# ============================================================

DEFAULT_CASES = [
    {
        "ID": "DOC-001",
        "Type": "Document Check",
        "Subject": "Please check draft BL for SI-2026-0821",
        "Shipment": "SI-2026-0821",
        "Priority": "Urgent",
        "Received": "10:24 AM",
        "Shipment Type": "International",
        "Status": "Under Review",
        "Confidence": "HIGH",
    },
    {
        "ID": "SI-001",
        "Type": "SI Request",
        "Subject": "Prepare shipping instruction for...",
        "Shipment": "SHP-2026-0456",
        "Priority": "Normal",
        "Received": "09:51 AM",
        "Shipment Type": "International",
        "Status": "Under Review",
        "Confidence": "HIGH",
    },
    {
        "ID": "INV-001",
        "Type": "Invoice Question",
        "Subject": "Invoice amount seems incorrect",
        "Shipment": "INV-2026-1120",
        "Priority": "Normal",
        "Received": "09:32 AM",
        "Shipment Type": "Domestic",
        "Status": "Done",
        "Confidence": "HIGH",
    },
    {
        "ID": "OPS-001",
        "Type": "Operational Update",
        "Subject": "Vessel departure update - MV Ocean Star",
        "Shipment": "VES-2026-0789",
        "Priority": "Low",
        "Received": "08:45 AM",
        "Shipment Type": "International",
        "Status": "Done",
        "Confidence": "HIGH",
    },
    {
        "ID": "DOC-002",
        "Type": "Document Check",
        "Subject": "Check attached BL for shipment",
        "Shipment": "SI-2026-0777",
        "Priority": "Urgent",
        "Received": "08:15 AM",
        "Shipment Type": "Domestic",
        "Status": "Under Review",
        "Confidence": "HIGH",
    },
    {
        "ID": "SPAM-001",
        "Type": "Spam",
        "Subject": "Congratulations! You've won a prize...",
        "Shipment": "-",
        "Priority": "Low",
        "Received": "07:50 AM",
        "Shipment Type": "International",
        "Status": "Done",
        "Confidence": "HIGH",
    },
]


DEFAULT_COMPARISON = [
    {
        "Shipment": "SI-2026-0821",
        "Field": "Shipper",
        "Shipping Instruction (SI)": "ABC Trading Ltd.",
        "Draft Bill of Lading (BL)": "ABC Trading Ltd.",
    },
    {
        "Shipment": "SI-2026-0821",
        "Field": "Consignee",
        "Shipping Instruction (SI)": "XYZ Logistics Pte. Ltd.",
        "Draft Bill of Lading (BL)": "XYZ Logistics Pte. Ltd.",
    },
    {
        "Shipment": "SI-2026-0821",
        "Field": "Notify Party",
        "Shipping Instruction (SI)": "XYZ Logistics Pte. Ltd.",
        "Draft Bill of Lading (BL)": "XYZ Logistics Pte. Ltd.",
    },
    {
        "Shipment": "SI-2026-0821",
        "Field": "Port of Loading",
        "Shipping Instruction (SI)": "Shanghai",
        "Draft Bill of Lading (BL)": "Load Port: Shanghai",
    },
    {
        "Shipment": "SI-2026-0821",
        "Field": "Port of Discharge",
        "Shipping Instruction (SI)": "Singapore",
        "Draft Bill of Lading (BL)": "Discharge Port: Singapore",
    },
    {
        "Shipment": "SI-2026-0821",
        "Field": "Container Count",
        "Shipping Instruction (SI)": "1",
        "Draft Bill of Lading (BL)": "1",
    },
    {
        "Shipment": "SI-2026-0821",
        "Field": "Gross Weight",
        "Shipping Instruction (SI)": "12,500 KG",
        "Draft Bill of Lading (BL)": "12,050 KG",
    },
]


REQUIRED_RECORD_COLUMNS = [
    "ID", "Type", "Subject", "From", "Shipment", "Priority",
    "Received", "Shipment Type", "Status", "Confidence"
]


def ensure_record_schema(frame):
    """Guarantee a stable record schema for every data source."""
    if frame is None or not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame()

    frame = frame.copy()

    for column in REQUIRED_RECORD_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""

    defaults = {
        "ID": "UNKNOWN",
        "Type": "Operational Update",
        "Subject": "Untitled record",
        "From": "",
        "Shipment": "-",
        "Priority": "Normal",
        "Received": "-",
        "Shipment Type": "International",
        "Status": "Under Review",
        "Confidence": "LOW",
    }

    for column, default in defaults.items():
        frame[column] = frame[column].fillna(default).replace("", default)

    return frame[REQUIRED_RECORD_COLUMNS + [c for c in frame.columns if c not in REQUIRED_RECORD_COLUMNS]]


def load_backend_records():
    category_map = {
        "document_comparison": "Document Check",
        "new_si_request": "SI Request",
        "invoice_query": "Invoice Question",
        "general": "Operational Update",
        "spam": "Spam",
    }

    rows = []

    # Keep the frontend resilient when the local/backend inbox is unavailable.
    # The demo must never break because an input file, classifier, or connector
    # temporarily fails.
    try:
        inbox = load_inbox()
        emails = list(inbox) if inbox is not None else []
    except Exception:
        emails = []

    # Fall back to the built-in demo records when the local inbox is empty
    # or unavailable. This keeps the dashboard usable even without source
    # email files or external backend data.
    st.session_state["demo_mode"] = not bool(emails)

    if not emails:
        return ensure_record_schema(pd.DataFrame(DEFAULT_CASES))

    for email in emails:
        try:
            classification = classify_email(email)
            category = classification.get("category", "general")
        except Exception:
            # A malformed email should not prevent the rest of the workspace
            # from loading.
            classification = {"category": "general", "confidence": "LOW"}
            category = "general"

        rows.append({
            "ID": email["email_id"],
            "Type": category_map.get(category, "Operational Update"),
            "Subject": email["subject"],
            "From": email["from"],
            "Shipment": email["email_id"],
            "Priority": "Normal",
            "Received": "-",
            "Shipment Type": "International",
            "Status": (
                "Under Review"
                if category == "document_comparison"
                else "Done"
            ),
            "Confidence": classification.get("confidence", "LOW"),
        })

    return ensure_record_schema(pd.DataFrame(rows))


def load_backend_comparison():
    return pd.DataFrame(DEFAULT_COMPARISON)



@st.cache_data(show_spinner=False)
def process_backend_email(email_id):
    try:
        inbox = load_inbox()

        email = next(
            (
                item
                for item in inbox
                if str(item.get("email_id")) == str(email_id)
            ),
            None,
        )

        if email is None:
            return {
                "status": "email_not_found",
                "reason": f"Email {email_id} was not found.",
            }

        pipeline_result = process_email(email)

        return aggregate_result(
            email,
            pipeline_result,
        )

    except Exception as exc:
        return {
            "status": "failed",
            "reason": str(exc),
            "errors": [str(exc)],
        }


def get_effective_backend_result(email_id):
    base_result = process_backend_email(email_id)

    correction_result = (
        st.session_state
        .get("human_correction_results", {})
        .get(str(email_id))
    )

    if not correction_result:
        return base_result

    result = dict(base_result)
    result["verification"] = correction_result
    result["human_review"] = correction_result.get(
        "human_review"
    )

    status_map = {
        "OK": "verified",
        "MISMATCH": "mismatch",
        "NEEDS_REVIEW": "human_review",
    }

    result["status"] = status_map.get(
        correction_result.get("status"),
        result.get("status"),
    )

    result["review_reason"] = correction_result.get(
        "review_reason"
    )

    result["reason"] = correction_result.get(
        "message",
        result.get("reason"),
    )

    return result


def apply_record_human_correction(
    email_id,
    si_corrections,
    bl_corrections,
    reviewer,
    note,
):
    inbox = load_inbox()

    email = next(
        (
            item
            for item in inbox
            if str(item.get("email_id")) == str(email_id)
        ),
        None,
    )

    if email is None:
        raise ValueError(
            f"Email {email_id} was not found."
        )

    pipeline_result = process_email(email)
    extraction = pipeline_result.get("extraction") or {}

    payload = build_verification_payload(extraction)

    key = str(email_id)

    saved_values = (
        st.session_state["human_correction_values"]
        .get(
            key,
            {
                "si": {},
                "bl": {},
            },
        )
    )

    all_si_corrections = dict(
        saved_values.get("si") or {}
    )

    all_bl_corrections = dict(
        saved_values.get("bl") or {}
    )

    all_si_corrections.update(
        si_corrections or {}
    )

    all_bl_corrections.update(
        bl_corrections or {}
    )

    result = apply_human_correction(
        payload,
        si_corrections=all_si_corrections,
        bl_corrections=all_bl_corrections,
        email_id=email_id,
        category="BL_COMPARISON",
        reviewer=reviewer,
        note=note,
    )

    st.session_state["human_correction_values"][key] = {
        "si": all_si_corrections,
        "bl": all_bl_corrections,
    }

    st.session_state["human_correction_results"][key] = result

    return result


def verification_to_comparison(email_id, pipeline_result):
    verification = pipeline_result.get("verification") or {}
    field_results = verification.get("field_results") or {}

    columns = [
        "Shipment",
        "Field",
        "Shipping Instruction (SI)",
        "Draft Bill of Lading (BL)",
        "Status",
        "Verification Reason",
        "SI Confidence",
        "BL Confidence",
        "SI Source",
        "BL Source",
        "SI Normalized",
        "BL Normalized",
    ]

    if not field_results:
        return pd.DataFrame(columns=columns)

    field_labels = {
        "shipper": "Shipper",
        "consignee": "Consignee",
        "notify_party": "Notify Party",
        "port_of_loading": "Port of Loading",
        "port_of_discharge": "Port of Discharge",
        "container_count": "Container Count",
        "gross_weight_kg": "Gross Weight (KG)",
    }

    status_map = {
        "MATCH": "Match",
        "MISMATCH": "Discrepancy",
        "REVIEW": "Needs Review",
    }

    rows = []

    for field_name, field_result in field_results.items():
        si = field_result.get("si") or {}
        bl = field_result.get("bl") or {}

        si_raw = si.get("raw")
        bl_raw = bl.get("raw")

        rows.append(
            {
                "Shipment": email_id,
                "Field": field_labels.get(field_name, field_name),
                "Shipping Instruction (SI)": (
                    "Missing" if si_raw is None else str(si_raw)
                ),
                "Draft Bill of Lading (BL)": (
                    "Missing" if bl_raw is None else str(bl_raw)
                ),
                "Status": status_map.get(
                    field_result.get("status"),
                    "Needs Review",
                ),
                "Verification Reason": field_result.get("reason"),
                "SI Confidence": si.get("confidence"),
                "BL Confidence": bl.get("confidence"),
                "SI Source": si.get("source"),
                "BL Source": bl.get("source"),
                "SI Normalized": si.get("normalized"),
                "BL Normalized": bl.get("normalized"),
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# SESSION STATE
# ============================================================

if "df" not in st.session_state:
    st.session_state["df"] = load_backend_records()

st.session_state["df"] = ensure_record_schema(st.session_state["df"])

if "comparison_df" not in st.session_state:
    st.session_state["comparison_df"] = load_backend_comparison()

if "selected_record_id" not in st.session_state:
    st.session_state["selected_record_id"] = None

if "case_view" not in st.session_state:
    st.session_state["case_view"] = False

if "page_override" not in st.session_state:
    st.session_state["page_override"] = None

if "main_nav" not in st.session_state:
    st.session_state["main_nav"] = "Home"

if "insights_nav" not in st.session_state:
    st.session_state["insights_nav"] = None

if "system_nav" not in st.session_state:
    st.session_state["system_nav"] = None

if "activity_log" not in st.session_state:
    st.session_state["activity_log"] = []

if "activity_ids" not in st.session_state:
    st.session_state["activity_ids"] = set()

if "review_notes" not in st.session_state:
    st.session_state["review_notes"] = {}

if "human_correction_results" not in st.session_state:
    st.session_state["human_correction_results"] = {}

if "human_correction_values" not in st.session_state:
    st.session_state["human_correction_values"] = {}

if st.session_state.get("human_correction_logic_version") != 3:
    st.session_state["human_correction_results"] = {}
    st.session_state["human_correction_values"] = {}

    correction_widget_prefixes = (
        "correct_si_",
        "correct_bl_",
        "reference_si_",
        "reviewer_",
        "correction_note_",
    )

    for state_key in list(st.session_state.keys()):
        if state_key.startswith(correction_widget_prefixes):
            del st.session_state[state_key]

    st.session_state["human_correction_logic_version"] = 3

if "logged_out" not in st.session_state:
    st.session_state["logged_out"] = False

if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""

if "_pending_nav" not in st.session_state:
    st.session_state["_pending_nav"] = None


# ------------------------------------------------------------
# NAVIGATION STATE FIX
# ------------------------------------------------------------
# Streamlit radio widgets own their session_state keys after creation.
# Writing to those keys later in the same run can raise StreamlitAPIException.
# Buttons therefore place navigation changes into _pending_nav and trigger a
# rerun. The queued values are applied before the radio widgets are created.

if st.session_state["_pending_nav"]:

    _pending = st.session_state.pop("_pending_nav")

    for _key in (
        "main_nav",
        "insights_nav",
        "system_nav",
        "page_override",
        "case_view",
        "selected_record_id",
    ):

        if _key in _pending:
            st.session_state[_key] = _pending[_key]



def go_to(
    main_nav=None,
    insights_nav="__unset__",
    system_nav="__unset__",
    page_override="__unset__",
    case_view=None,
    selected_record_id="__unset__",
):
    pending = {}

    if main_nav is not None:
        pending["main_nav"] = main_nav

    if insights_nav != "__unset__":
        pending["insights_nav"] = insights_nav

    if system_nav != "__unset__":
        pending["system_nav"] = system_nav

    if page_override != "__unset__":
        pending["page_override"] = page_override

    if case_view is not None:
        pending["case_view"] = case_view

    if selected_record_id != "__unset__":
        pending["selected_record_id"] = selected_record_id

    st.session_state["_pending_nav"] = pending
    st.rerun()


df = st.session_state["df"]
comparison_df = st.session_state["comparison_df"]

backup_demo = (
    str(st.query_params.get("backup", "")).lower()
    in {"1", "true", "yes"}
)

fresh_demo = not backup_demo

if fresh_demo:
    if not st.session_state.get(
        "_fresh_demo_initialized",
        False,
    ):
        st.session_state["full_analysis_status"] = "idle"
        st.session_state["full_analysis_index"] = 0
        st.session_state["full_analysis_counts"] = {
            "OK": 0,
            "MISMATCH": 0,
            "NEEDS_REVIEW": 0,
        }
        st.session_state["full_analysis_failures"] = 0
        st.session_state["full_analysis_results"] = []
        st.session_state["full_analysis_summary"] = {}
        st.session_state["_fresh_demo_initialized"] = True
else:
    st.session_state.pop(
        "_fresh_demo_initialized",
        None,
    )

    restore_demo_snapshot(len(df))

snapshot_results = (
    st.session_state.get("full_analysis_results")
    or []
)

snapshot_summary = (
    st.session_state.get("full_analysis_summary")
    or {}
)

if (
    not fresh_demo
    and len(snapshot_results) == len(df)
    and snapshot_summary
):
    save_demo_snapshot(
        results=snapshot_results,
        summary=snapshot_summary,
        total_records=len(df),
    )


# ============================================================
# HELPERS
# ============================================================

def safe_text(value):
    return html.escape(str(value))


def type_badge(text):
    classes = {
        "Document Check": "type-badge-document",
        "SI Request": "type-badge-si",
        "Invoice Question": "type-badge-invoice",
        "Operational Update": "type-badge-operational",
        "Spam": "type-badge-spam",
    }

    return f"""
    <span class="type-badge {classes.get(text, 'type-badge-invoice')}">
        {safe_text(text)}
    </span>
    """


def priority_badge(text):
    classes = {
        "Urgent": "badge-red",
        "Normal": "badge-orange",
        "Low": "badge-green",
    }

    return f"""
    <span class="badge {classes.get(text, 'badge-blue')}">
        {safe_text(text)}
    </span>
    """


def status_badge(text):
    classes = {
        "Done": "badge-green",
        "Verified": "badge-green",
        "Discrepancy": "badge-red",
        "Needs Review": "badge-orange",
        "Under Review": "badge-orange",
        "Processing Error": "badge-red",
    }

    cls = classes.get(text, "badge-blue")

    return f"""
    <span class="badge {cls}">
        {safe_text(text)}
    </span>
    """


def get_record_display_status(record):
    current_status = record.get("Status")

    if record.get("Type") != "Document Check":
        return current_status or "Done"

    record_id = record.get("ID")

    if record_id is None:
        return current_status or "Under Review"

    pipeline_result = get_effective_backend_result(record_id)

    status_map = {
        "verified": "Verified",
        "mismatch": "Discrepancy",
        "human_review": "Needs Review",
        "failed": "Processing Error",
    }

    return status_map.get(
        pipeline_result.get("status"),
        current_status or "Under Review",
    )


def confidence_badge(value):
    """Render the classifier confidence as a compact accessible badge."""
    confidence = str(value or "LOW").upper()
    css_class = {
        "HIGH": "confidence-high",
        "MEDIUM": "confidence-medium",
        "LOW": "confidence-low",
    }.get(confidence, "confidence-low")
    return f'<span class="badge {css_class}">{safe_text(confidence)} confidence</span>'


def get_record_by_id(record_id):
    if record_id is None:
        return None

    matches = df[df["ID"] == record_id]

    if not matches.empty:
        return matches.iloc[0].to_dict()

    return None


def get_record_by_shipment(shipment):
    matches = df[df["Shipment"] == shipment]

    if not matches.empty:
        return matches.iloc[0].to_dict()

    return None


def open_record(record):
    record_id = record.get("ID")

    if record_id is None:
        return

    st.session_state["selected_record_id"] = record_id
    st.session_state["case_view"] = True
    st.session_state["page_override"] = None
    st.rerun()


def add_activity(title, shipment, activity_type, event_key=None):

    if event_key is None:
        event_key = (
            f"{title}|{shipment}|{activity_type}|"
            f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        )

    if event_key in st.session_state["activity_ids"]:
        return

    st.session_state["activity_ids"].add(event_key)

    timestamp = datetime.now().strftime("%I:%M %p")

    st.session_state["activity_log"].insert(
        0,
        {
            "event_id": event_key,
            "title": title,
            "shipment": shipment,
            "time": timestamp,
            "type": activity_type,
        },
    )


def parse_received_time(value):

    if pd.isna(value):
        return pd.Timestamp.min

    text = str(value).strip()

    formats = [
        "%I:%M %p",
        "%H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
    ]

    for fmt in formats:
        try:
            return pd.to_datetime(text, format=fmt)
        except (ValueError, TypeError):
            continue

    parsed = pd.to_datetime(text, errors="coerce")

    if pd.isna(parsed):
        return pd.Timestamp.min

    return parsed


def search_dataframe(input_df, query):

    if input_df.empty:
        return input_df.copy()

    query = str(query).strip().lower()

    if not query:
        return input_df.copy()

    searchable_columns = [
        column
        for column in [
            "ID",
            "Subject",
            "Shipment",
            "Type",
            "Priority",
            "Shipment Type",
            "Status",
            "From",
            "Confidence",
        ]
        if column in input_df.columns
    ]

    mask = pd.Series(
        False,
        index=input_df.index,
    )

    for column in searchable_columns:
        mask = (
            mask
            |
            input_df[column]
            .astype(str)
            .str.lower()
            .str.contains(
                query,
                na=False,
                regex=False,
            )
        )

    return input_df.loc[mask].copy()


def sort_records(input_df, sort_option):

    if input_df.empty:
        return input_df.copy()

    result = input_df.copy()

    result["_received_sort"] = result["Received"].apply(
        parse_received_time
    )

    if sort_option == "Newest":

        result = result.sort_values(
            "_received_sort",
            ascending=False,
            kind="stable",
        )

    elif sort_option == "Oldest":

        result = result.sort_values(
            "_received_sort",
            ascending=True,
            kind="stable",
        )

    elif sort_option == "Priority":

        priority_order = {
            "Urgent": 0,
            "Normal": 1,
            "Low": 2,
        }

        result["_priority_order"] = (
            result["Priority"]
            .map(priority_order)
            .fillna(99)
        )

        result = result.sort_values(
            ["_priority_order", "_received_sort"],
            ascending=[True, False],
            kind="stable",
        )

    result = result.drop(
        columns=[
            column
            for column in [
                "_received_sort",
                "_priority_order",
            ]
            if column in result.columns
        ]
    )

    return result


def update_record_status(record_id, new_status):

    matches = st.session_state["df"]["ID"] == record_id

    st.session_state["df"].loc[
        matches,
        "Status",
    ] = new_status


def save_review_note(record_id, note):

    st.session_state["review_notes"][record_id] = note


def get_review_note(record_id):

    return st.session_state["review_notes"].get(
        record_id,
        "",
    )


def get_comparison_for_record(record):
    shipment = record.get("Shipment")

    if st.session_state.get("demo_mode", False):
        if comparison_df.empty:
            return pd.DataFrame(
                columns=[
                    "Field",
                    "Shipping Instruction (SI)",
                    "Draft Bill of Lading (BL)",
                ]
            )

        if "Shipment" in comparison_df.columns:
            return comparison_df[
                comparison_df["Shipment"].astype(str)
                == str(shipment)
            ].copy()

        return comparison_df.copy()

    record_id = record.get("ID")

    if record_id is not None:
        pipeline_result = get_effective_backend_result(
            record_id
        )

        return verification_to_comparison(
            record_id,
            pipeline_result,
        )

    if comparison_df.empty:
        return pd.DataFrame(
            columns=[
                "Field",
                "Shipping Instruction (SI)",
                "Draft Bill of Lading (BL)",
            ]
        )

    if "Shipment" in comparison_df.columns:
        return comparison_df[
            comparison_df["Shipment"].astype(str)
            == str(shipment)
        ].copy()

    return comparison_df.copy()

def normalize_comparison_value(value):

    value = str(value).strip().lower()

    prefixes = [
        "load port:",
        "discharge port:",
        "port of loading:",
        "port of discharge:",
    ]

    for prefix in prefixes:

        if value.startswith(prefix):

            value = value[len(prefix):].strip()

    value = re.sub(r"\s+", " ", value)

    return value


def comparison_status(si_value, bl_value):

    si_normalized = normalize_comparison_value(si_value)
    bl_normalized = normalize_comparison_value(bl_value)

    if si_normalized == bl_normalized:
        return "Match"

    return "Discrepancy"


def build_comparison_statuses(comp_df):

    if comp_df.empty:
        return comp_df.copy()

    result = comp_df.copy()

    result["Status"] = result.apply(
        lambda row: comparison_status(
            row["Shipping Instruction (SI)"],
            row["Draft Bill of Lading (BL)"],
        ),
        axis=1,
    )

    return result


def parse_numeric_value(value):

    text = str(value).replace(",", "")

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def format_difference(si_value, bl_value):

    si_num = parse_numeric_value(si_value)
    bl_num = parse_numeric_value(bl_value)

    if si_num is None or bl_num is None:
        return None

    difference = abs(si_num - bl_num)

    if difference.is_integer():
        return f"{int(difference):,}"

    return f"{difference:,.2f}"


def get_discrepancies(comp_df):

    if comp_df.empty:
        return comp_df.copy()

    return comp_df[
        comp_df["Status"] == "Discrepancy"
    ].copy()


def render_page_header(title, caption=None):
    st.markdown(
        f"""
        <div class="sg-hero">
            <div class="sg-eyebrow">ShipGuard AI · Operations</div>
            <div class="sg-hero-title">{safe_text(title)}</div>
            <div class="sg-hero-copy">{safe_text(caption or "Manage shipping operations from one workspace.")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_filtered_records(
    record_df,
    empty_message="No records found.",
    search_key=None,
    show_search=True,
):

    working_df = record_df.copy()

    # SHARED RECORD PAGINATION
    # All records remain available; only a small page is rendered.
    page_size = 20

    page_scope = (
        search_key
        if search_key
        else "filtered_records"
    )

    page_state_key = f"{page_scope}_page"
    query_state_key = f"{page_scope}_last_query"

    if show_search:

        query = st.text_input(
            "Search",
            placeholder=(
                "Search subject, shipment, type or priority..."
            ),
            label_visibility="collapsed",
            key=search_key,
        )

        # Return to page 1 when the search changes.
        previous_query = st.session_state.get(
            query_state_key,
            None,
        )

        if previous_query != query:
            st.session_state[page_state_key] = 1
            st.session_state[query_state_key] = query

        working_df = search_dataframe(
            working_df,
            query,
        )

    if working_df.empty:

        st.markdown(
            f"""
            <div class="panel">
                <div style="
                    padding:25px;
                    text-align:center;
                    color:#71839b;
                    font-size:13px;
                ">
                    {safe_text(empty_message)}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        return

    total_records = len(working_df)

    total_pages = max(
        1,
        (total_records + page_size - 1)
        // page_size,
    )

    if page_state_key not in st.session_state:
        st.session_state[page_state_key] = 1

    st.session_state[page_state_key] = min(
        max(
            int(st.session_state[page_state_key]),
            1,
        ),
        total_pages,
    )

    current_page = int(
        st.session_state[page_state_key]
    )

    start_index = (
        (current_page - 1)
        * page_size
    )

    end_index = min(
        start_index + page_size,
        total_records,
    )

    page_df = working_df.iloc[
        start_index:end_index
    ]

    def _previous_records_page():
        st.session_state[page_state_key] = max(
            1,
            int(st.session_state.get(page_state_key, 1)) - 1,
        )

    def _next_records_page():
        st.session_state[page_state_key] = min(
            total_pages,
            int(st.session_state.get(page_state_key, 1)) + 1,
        )

    info_col, previous_col, next_col = st.columns(
        [4.0, 1.0, 1.0]
    )

    with info_col:
        st.markdown(
            f"""
            <div class="small-muted" style="margin-bottom:10px;">
                Showing {start_index + 1}–{end_index}
                of {total_records} record(s)
                · Page {current_page} of {total_pages}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with previous_col:
        st.button(
            "← Previous",
            key=f"{page_scope}_previous_page",
            use_container_width=True,
            disabled=current_page <= 1,
            on_click=_previous_records_page,
        )

    with next_col:
        st.button(
            "Next →",
            key=f"{page_scope}_next_page",
            use_container_width=True,
            disabled=current_page >= total_pages,
            on_click=_next_records_page,
        )

    for row_index, row in page_df.iterrows():

        st.markdown(
            '<div class="doc-card">',
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4, c5 = st.columns(
            [1.05, 2.75, 1.0, 1.25, .7]
        )

        with c1:

            st.markdown(
                type_badge(row["Type"]),
                unsafe_allow_html=True,
            )

        with c2:

            st.markdown(
                f"""
                <div class="subject-text">
                    {safe_text(row["Subject"])}
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.caption(
                f'{row["Shipment"]} · '
                f'{row["Shipment Type"]} · '
                f'Received {row["Received"]}'
            )

        with c3:

            st.markdown(
                priority_badge(row["Priority"]),
                unsafe_allow_html=True,
            )

            st.write("")

            st.markdown(
                status_badge(row["Status"]),
                unsafe_allow_html=True,
            )

        with c4:

            st.markdown(
                confidence_bar_html(
                    row.get("Confidence", "LOW")
                ),
                unsafe_allow_html=True,
            )

        with c5:

            if st.button(
                "View",
                key=f"filtered_view_{row_index}_{row['ID']}",
                use_container_width=False,
            ):

                open_record(row.to_dict())

        st.markdown(
            '</div>',
            unsafe_allow_html=True,
        )

        st.write("")


# ============================================================
# LOGGED OUT SCREEN
# ============================================================

if st.session_state["logged_out"]:

    st.markdown(
        """
        <div class="logout-box">
            <div style="
                font-size:34px;
                color:#183653;
                font-weight:700;
            ">
                SG
            </div>

            <h2>Signed out</h2>

            <p style="color:#71839b;">
                You have been signed out of the ShipGuard AI frontend.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, center, _ = st.columns([2, 1, 2])

    with center:

        if st.button(
            "Return to ShipGuard AI",
            use_container_width=True,
        ):

            st.session_state["logged_out"] = False
            st.session_state["page_override"] = None
            st.session_state["case_view"] = False
            st.session_state["main_nav"] = "Home"
            st.session_state["insights_nav"] = None
            st.session_state["system_nav"] = None
            st.rerun()

    st.stop()


if "full_analysis_results" not in st.session_state:
    st.session_state["full_analysis_results"] = None

if "full_analysis_summary" not in st.session_state:
    st.session_state["full_analysis_summary"] = {
        "processed": 0,
        "total": len(df),
        "ok": 0,
        "mismatch": 0,
        "needs_review": 0,
        "failed": 0,
    }


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        f"""
        <div class="shipguard-brand">

            <div class="shipguard-logo">
                SG
            </div>

            <div>
                <div class="shipguard-name">
                    ShipGuard AI
                </div>

                <div class="shipguard-subtitle">
                    Shipping Operations
                </div>
            </div>

        </div>

        <div class="sidebar-divider"></div>

        <div class="sidebar-section">
            Workspace
        </div>
        """,
        unsafe_allow_html=True,
    )

    main_options = [
        "Home",
        "Inbox",
        "Document Checks",
        "SI Requests",
        "Invoices",
        "Operational Updates",
        "Spam",
        "Recent Activity",
    ]

    def _on_main_nav_change():
        st.session_state["page_override"] = None
        st.session_state["case_view"] = False
        st.session_state["selected_record_id"] = None
        st.session_state["insights_nav"] = None
        st.session_state["system_nav"] = None

    main_choice = st.radio(
        "Navigation",
        main_options,
        index=main_options.index(
            st.session_state["main_nav"]
        ),
        key="main_nav",
        label_visibility="collapsed",
        on_change=_on_main_nav_change,
    )

    st.markdown(
        """
        <div class="sidebar-divider"></div>

        <div class="sidebar-section">
            Insights
        </div>
        """,
        unsafe_allow_html=True,
    )

    insights_options = [
        "Analytics",
        "Reports",
    ]

    insights_current = st.session_state["insights_nav"]

    if insights_current not in insights_options:
        insights_current = None

    def _on_insights_nav_change():
        st.session_state["page_override"] = None
        st.session_state["case_view"] = False
        st.session_state["selected_record_id"] = None
        st.session_state["main_nav"] = "Home"
        st.session_state["system_nav"] = None

    insights_choice = st.radio(
        "Insights",
        insights_options,
        index=(
            insights_options.index(insights_current)
            if insights_current in insights_options
            else None
        ),
        key="insights_nav",
        label_visibility="collapsed",
        on_change=_on_insights_nav_change,
    )

    st.markdown(
        """
        <div class="sidebar-divider"></div>

        <div class="sidebar-section">
            System
        </div>
        """,
        unsafe_allow_html=True,
    )

    system_options = [
        "Settings",
    ]

    system_current = st.session_state["system_nav"]

    if system_current not in system_options:
        system_current = None

    def _on_system_nav_change():
        st.session_state["page_override"] = None
        st.session_state["case_view"] = False
        st.session_state["selected_record_id"] = None
        st.session_state["main_nav"] = "Home"
        st.session_state["insights_nav"] = None

    system_choice = st.radio(
        "System",
        system_options,
        index=(
            system_options.index(system_current)
            if system_current in system_options
            else None
        ),
        key="system_nav",
        label_visibility="collapsed",
        on_change=_on_system_nav_change,
    )

    st.markdown(
        """
        <div class="sidebar-divider"></div>

        <div class="sidebar-section">
            Review Status
        </div>
        """,
        unsafe_allow_html=True,
    )

    sidebar_summary = st.session_state.get("full_analysis_summary") or {}

    under_review = int(
        sidebar_summary.get("needs_review", 0)
    )

    done = int(
        sidebar_summary.get("processed", 0)
    )

    status_c1, status_c2 = st.columns(2)

    with status_c1:

        st.markdown(
            f"""
            <div class="status-card">
                <div class="status-label">
                    Needs review
                </div>

                <div class="status-value">
                    {under_review}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with status_c2:

        st.markdown(
            f"""
            <div class="status-card">
                <div class="status-label">
                    Analysed
                </div>

                <div class="status-value">
                    {done}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="sidebar-divider"></div>',
        unsafe_allow_html=True,
    )

    with st.container(key="sidebar_account_footer"):

        user_col1, user_col2 = st.columns([1, 3])

        with user_col1:

            st.markdown(
                f"""
                <div class="sidebar-avatar">
                    {safe_text(USER_INITIALS)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with user_col2:

            st.markdown(
                f"""
                <div class="sidebar-user-name">
                    {safe_text(USER_NAME)}
                </div>

                <div class="sidebar-user-role">
                    {safe_text(USER_ROLE)}
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.popover(
            "Account",
            use_container_width=True,
        ):

            st.markdown(f"**{USER_NAME}**")
            st.caption(USER_ROLE)

            if st.button(
                "Settings",
                use_container_width=True,
                key="account_settings",
            ):

                go_to(
                    main_nav="Home",
                    insights_nav=None,
                    system_nav=None,
                    page_override="Settings",
                    case_view=False,
                    selected_record_id=None,
                )

            if st.button(
                "Log out",
                use_container_width=True,
                key="account_logout",
            ):

                st.session_state["logged_out"] = True
                st.session_state["case_view"] = False
                st.session_state["selected_record_id"] = None
                st.rerun()

        st.markdown(
            f'<div class="sidebar-subtle" style="text-align:right;font-size:9px;">v{APP_VERSION}</div>',
            unsafe_allow_html=True,
        )


def render_global_topbar(page_name):
    """Render a compact product-style utility bar above page content."""
    analysis_status = st.session_state.get(
        "full_analysis_status",
        "idle",
    )

    analysis_summary = (
        st.session_state.get("full_analysis_summary") or {}
    )

    processed = int(
        st.session_state.get(
            "full_analysis_index",
            analysis_summary.get("processed", 0),
        )
        or 0
    )

    total = len(st.session_state.get("df", []))

    status_html = status_badge_html(
        status=analysis_status,
        processed=processed,
        total=total,
        summary=analysis_summary,
    )

    st.markdown(
        f"""
        <div class="sg-topbar">
            <div class="sg-topbar-left">
                <div class="sg-topbar-mark">SG</div>
                <div>
                    <div class="sg-topbar-title">ShipGuard AI</div>
                    <div class="sg-topbar-path">Operations / {safe_text(page_name)}</div>
                </div>
            </div>
            <div class="sg-topbar-right">
                <div class="sg-shortcut">AI-assisted review</div>
                {status_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# EFFECTIVE PAGE
# ============================================================

if st.session_state["case_view"]:

    page_to_show = "Document Check Case"

elif st.session_state.get("page_override"):

    page_to_show = st.session_state["page_override"]

elif insights_choice is not None:

    page_to_show = insights_choice

elif system_choice is not None:

    page_to_show = system_choice

else:

    page_to_show = main_choice


render_global_topbar(page_to_show)


# ============================================================
# HOME
# ============================================================

if page_to_show == "Home":

    head_left, head_right = st.columns([3.2, 1.5])

    with head_left:

        st.markdown(
            f"# Good morning, {safe_text(USER_NAME)}"
        )

    with head_right:

        st.markdown(
            "<div style='height:8px'></div>",
            unsafe_allow_html=True,
        )

        search = st.text_input(
            "Search",
            placeholder="Search shipment, email, document...",
            label_visibility="collapsed",
            key="home_search",
        )

        st.session_state["search_query"] = search

    st.write("")

    analysis_total_hint = len(df)
    demo_mode = bool(
        st.session_state.get("demo_mode", False)
    )

    if "full_analysis_status" not in st.session_state:
        st.session_state["full_analysis_status"] = "idle"

    if "full_analysis_index" not in st.session_state:
        st.session_state["full_analysis_index"] = 0

    if "full_analysis_counts" not in st.session_state:
        st.session_state["full_analysis_counts"] = {
            "OK": 0,
            "MISMATCH": 0,
            "NEEDS_REVIEW": 0,
        }

    if "full_analysis_failures" not in st.session_state:
        st.session_state["full_analysis_failures"] = 0

    if "full_analysis_results" not in st.session_state:
        st.session_state["full_analysis_results"] = []

    analysis_status = st.session_state.get(
        "full_analysis_status",
        "idle",
    )

    existing_summary = (
        st.session_state.get("full_analysis_summary") or {}
    )

    existing_processed = int(
        existing_summary.get(
            "processed",
            st.session_state.get("full_analysis_index", 0),
        )
    )

    run_full_analysis = False
    cancel_analysis = False
    continue_analysis = False
    end_analysis = False

    if analysis_status == "paused" and not demo_mode:
        continue_col, end_col, analysis_info_col = st.columns(
            [1.3, 1.3, 3.4]
        )

        with continue_col:
            continue_analysis = st.button(
                "Continue Analysis",
                type="primary",
                use_container_width=True,
                key="continue_full_analysis",
            )

        with end_col:
            end_analysis = st.button(
                "End Analysis",
                use_container_width=True,
                key="end_full_analysis",
            )

    else:
        run_col, analysis_info_col = st.columns([1.5, 3.5])

        with run_col:
            if demo_mode:
                st.button(
                    "Full Analysis unavailable in Demo Mode",
                    disabled=True,
                    use_container_width=True,
                    key="run_full_analysis_demo",
                )

            elif analysis_status == "running":
                cancel_analysis = st.button(
                    "Cancel Analysis",
                    use_container_width=True,
                    key="cancel_full_analysis",
                )

            elif (
                not fresh_demo
                and analysis_status == "complete"
                and existing_processed >= analysis_total_hint
            ):
                st.button(
                    f"Analysis Complete — {existing_processed}/{analysis_total_hint}",
                    disabled=True,
                    use_container_width=True,
                    key="analysis_complete_snapshot",
                )

            else:
                run_full_analysis = st.button(
                    f"Run Full Analysis — {analysis_total_hint} emails",
                    type="primary",
                    use_container_width=True,
                    key="run_full_analysis",
                )

    with analysis_info_col:
        if demo_mode:
            st.caption(
                "Demo Mode: source inbox data is unavailable. "
                "Built-in sample records are shown for interface demonstration."
            )

        elif analysis_status == "running":
            st.caption(
                f"Analysis running · {existing_processed}/"
                f"{analysis_total_hint} emails processed"
            )

        elif analysis_status == "paused":
            st.caption(
                f"Analysis paused at {existing_processed}/"
                f"{analysis_total_hint}. Continue from this checkpoint "
                "or end the analysis and reset."
            )

        elif existing_processed:
            st.caption(
                "Latest analysis: "
                f"{existing_processed}/"
                f"{existing_summary.get('total', analysis_total_hint)} processed · "
                f"{existing_summary.get('ok', 0)} OK · "
                f"{existing_summary.get('mismatch', 0)} mismatch · "
                f"{existing_summary.get('needs_review', 0)} needs review · "
                f"{existing_summary.get('failed', 0)} failed"
            )

        else:
            st.caption(
                "Run the end-to-end pipeline across the complete inbox."
            )

    if run_full_analysis:
        # Start each new analysis from a fresh inbox snapshot.
        st.session_state.pop("analysis_emails_cache", None)
        st.session_state["full_analysis_status"] = "running"
        st.session_state["full_analysis_index"] = 0
        st.session_state["full_analysis_counts"] = {
            "OK": 0,
            "MISMATCH": 0,
            "NEEDS_REVIEW": 0,
        }
        st.session_state["full_analysis_failures"] = 0
        st.session_state["full_analysis_results"] = []
        st.session_state["full_analysis_summary"] = {
            "processed": 0,
            "total": analysis_total_hint,
            "ok": 0,
            "mismatch": 0,
            "needs_review": 0,
            "failed": 0,
        }
        st.rerun()

    if cancel_analysis:
        st.session_state["full_analysis_status"] = "paused"
        st.rerun()

    if continue_analysis:
        st.session_state["full_analysis_status"] = "running"
        st.rerun()

    if end_analysis:
        st.session_state["full_analysis_status"] = "idle"
        st.session_state["full_analysis_index"] = 0
        st.session_state["full_analysis_counts"] = {
            "OK": 0,
            "MISMATCH": 0,
            "NEEDS_REVIEW": 0,
        }
        st.session_state["full_analysis_failures"] = 0
        st.session_state["full_analysis_results"] = []
        st.session_state["full_analysis_summary"] = {
            "processed": 0,
            "total": analysis_total_hint,
            "ok": 0,
            "mismatch": 0,
            "needs_review": 0,
            "failed": 0,
        }
        st.rerun()

    analysis_status = st.session_state.get(
        "full_analysis_status",
        "idle",
    )

    if analysis_status in {"running", "paused"}:
        current_processed = int(
            st.session_state.get("full_analysis_index", 0)
        )

        current_counts = (
            st.session_state.get("full_analysis_counts") or {}
        )

        current_failures = int(
            st.session_state.get("full_analysis_failures", 0)
        )

        progress_percentage = (
            int(current_processed / analysis_total_hint * 100)
            if analysis_total_hint
            else 0
        )

        progress_bar = st.progress(
            min(progress_percentage, 100)
        )

        progress_text = st.empty()

        if analysis_status == "paused":
            progress_text.caption(
                f"Paused at {current_processed}/"
                f"{analysis_total_hint} emails"
            )
        else:
            progress_text.caption(
                f"Processing {current_processed}/"
                f"{analysis_total_hint} emails"
            )

        metric_columns = st.columns(5)

        processed_metric = metric_columns[0].empty()
        clear_metric = metric_columns[1].empty()
        mismatch_metric = metric_columns[2].empty()
        review_metric = metric_columns[3].empty()
        failed_metric = metric_columns[4].empty()

        processed_metric.metric(
            "Processed",
            current_processed,
        )
        clear_metric.metric(
            "No Issues",
            int(current_counts.get("OK", 0)),
        )
        mismatch_metric.metric(
            "Mismatch",
            int(current_counts.get("MISMATCH", 0)),
        )
        review_metric.metric(
            "Needs Review",
            int(current_counts.get("NEEDS_REVIEW", 0)),
        )
        failed_metric.metric(
            "Failed",
            current_failures,
        )

    if analysis_status == "running":
        try:
            # ANALYSIS PERFORMANCE CACHE
            # Load the 520-email inbox once for this analysis run,
            # then reuse it across Streamlit reruns.
            if "analysis_emails_cache" not in st.session_state:
                st.session_state["analysis_emails_cache"] = list(
                    load_inbox()
                )

            analysis_emails = st.session_state[
                "analysis_emails_cache"
            ]
            analysis_total = len(analysis_emails)

            start_index = int(
                st.session_state.get(
                    "full_analysis_index",
                    0,
                )
            )

            initial_counts = (
                st.session_state.get(
                    "full_analysis_counts"
                )
                or {
                    "OK": 0,
                    "MISMATCH": 0,
                    "NEEDS_REVIEW": 0,
                }
            )

            initial_failures = int(
                st.session_state.get(
                    "full_analysis_failures",
                    0,
                )
            )

            latest_progress = {
                "processed": start_index,
                "total": analysis_total,
                "counts": initial_counts.copy(),
                "pipeline_failures": initial_failures,
            }

            def update_analysis_progress(event):
                latest_progress.update(event)

                processed = int(
                    event.get("processed", start_index)
                )

                total = int(
                    event.get("total", analysis_total)
                )

                counts = event.get("counts") or {}
                failures = int(
                    event.get("pipeline_failures", 0)
                )

                percentage = (
                    int(processed / total * 100)
                    if total
                    else 0
                )

                progress_bar.progress(
                    min(percentage, 100)
                )

                progress_text.caption(
                    f"Processing {processed}/{total} emails"
                )

                processed_metric.metric(
                    "Processed",
                    processed,
                )
                clear_metric.metric(
                    "No Issues",
                    int(counts.get("OK", 0)),
                )
                mismatch_metric.metric(
                    "Mismatch",
                    int(counts.get("MISMATCH", 0)),
                )
                review_metric.metric(
                    "Needs Review",
                    int(counts.get("NEEDS_REVIEW", 0)),
                )
                failed_metric.metric(
                    "Failed",
                    failures,
                )

            chunk_results = process_batch(
                analysis_emails,
                progress_callback=update_analysis_progress,
                start_index=start_index,
                batch_size=10,
                initial_counts=initial_counts,
                initial_failures=initial_failures,
            )

            saved_results = list(
                st.session_state.get(
                    "full_analysis_results",
                    []
                )
            )

            saved_results.extend(chunk_results)

            final_counts = (
                latest_progress.get("counts") or {}
            )

            new_processed = int(
                latest_progress.get(
                    "processed",
                    start_index,
                )
            )

            new_failures = int(
                latest_progress.get(
                    "pipeline_failures",
                    initial_failures,
                )
            )

            st.session_state["full_analysis_results"] = (
                saved_results
            )

            st.session_state["full_analysis_index"] = (
                new_processed
            )

            st.session_state["full_analysis_counts"] = {
                "OK": int(final_counts.get("OK", 0)),
                "MISMATCH": int(
                    final_counts.get("MISMATCH", 0)
                ),
                "NEEDS_REVIEW": int(
                    final_counts.get(
                        "NEEDS_REVIEW",
                        0,
                    )
                ),
            }

            st.session_state["full_analysis_failures"] = (
                new_failures
            )

            st.session_state["full_analysis_summary"] = {
                "processed": new_processed,
                "total": analysis_total,
                "ok": int(final_counts.get("OK", 0)),
                "mismatch": int(
                    final_counts.get("MISMATCH", 0)
                ),
                "needs_review": int(
                    final_counts.get(
                        "NEEDS_REVIEW",
                        0,
                    )
                ),
                "failed": new_failures,
            }

            if new_processed >= analysis_total:
                st.session_state["full_analysis_status"] = (
                    "complete"
                )
            else:
                st.session_state["full_analysis_status"] = (
                    "running"
                )

            st.rerun()

        except Exception as exc:
            st.session_state["full_analysis_status"] = "paused"
            st.error(
                f"Full analysis paused because of an error: {exc}"
            )

    if analysis_status == "complete":
        st.success(
            "Full inbox analysis completed successfully."
        )

    total_records = len(df)
    analysis_summary = (
        st.session_state.get("full_analysis_summary") or {}
    )

    processed_count = int(
        analysis_summary.get("processed", 0)
    )
    ok_count = int(
        analysis_summary.get("ok", 0)
    )
    mismatch_count = int(
        analysis_summary.get("mismatch", 0)
    )
    review_count = int(
        analysis_summary.get("needs_review", 0)
    )
    failed_count = int(
        analysis_summary.get("failed", 0)
    )

    action_queue = mismatch_count + review_count

    completion_rate = (
        (processed_count / total_records * 100)
        if total_records else 0
    )

    system_status_html = status_badge_html(
        status=st.session_state.get("full_analysis_status", "idle"),
        processed=processed_count,
        total=total_records,
        summary=analysis_summary,
    )

    st.markdown(
        f"""
        <div class="command-strip">
            <div class="command-chip">
                <div class="command-chip-label">System status</div>
                <div class="command-chip-value">
                    {system_status_html}
                </div>
            </div>
            <div class="command-chip">
                <div class="command-chip-label">Records monitored</div>
                <div class="command-chip-value">{total_records}</div>
            </div>
            <div class="command-chip">
                <div class="command-chip-label">Action queue</div>
                <div class="command-chip-value">{action_queue}</div>
            </div>
            <div class="command-chip">
                <div class="command-chip-label">Analysis coverage</div>
                <div class="command-chip-value">{completion_rate:.0f}%</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


    # AI-assisted triage summary: informative rather than button-heavy.
    ai_open = review_count
    urgent_count = int((df["Priority"] == "Urgent").sum())
    high_confidence = int((df["Confidence"].astype(str).str.upper() == "HIGH").sum())
    confidence_rate = (high_confidence / total_records * 100) if total_records else 0
    attention_rate = (ai_open / total_records * 100) if total_records else 0

    st.markdown(
        f"""
        <div class="sg-ai-callout">
            <div>
                <div class="sg-ai-callout-title">AI-assisted operations overview</div>
                <div class="sg-ai-callout-copy">
                    ShipGuard has prioritised {urgent_count} urgent record(s) and
                    {ai_open} case(s) currently requiring human review.
                </div>
            </div>
            <div class="sg-ai-badge">TRIAGE READY · {confidence_rate:.0f}% HIGH CONFIDENCE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sg-section-label">Workspace intelligence</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="sg-insight-grid">
            <div class="sg-insight-card">
                <div class="sg-kpi-icon">!</div>
                <div class="sg-insight-title">Needs attention</div>
                <div class="sg-insight-value">{ai_open}</div>
                <div class="sg-insight-copy">Records are waiting for an operations decision.</div>
                <div class="sg-progress"><span style="width:{min(attention_rate,100):.0f}%"></span></div>
            </div>
            <div class="sg-insight-card">
                <div class="sg-kpi-icon">AI</div>
                <div class="sg-insight-title">AI confidence</div>
                <div class="sg-insight-value">{confidence_rate:.0f}%</div>
                <div class="sg-insight-copy">Classifications currently marked HIGH confidence.</div>
                <div class="sg-progress"><span style="width:{min(confidence_rate,100):.0f}%"></span></div>
            </div>
            <div class="sg-insight-card">
                <div class="sg-kpi-icon">✓</div>
                <div class="sg-insight-title">Processing complete</div>
                <div class="sg-insight-value">{completion_rate:.0f}%</div>
                <div class="sg-insight-copy">All records have completed automated analysis.</div>
                <div class="sg-progress"><span style="width:{min(completion_rate,100):.0f}%"></span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="overview-title">Overview</div>',
        unsafe_allow_html=True,
    )

    type_counts = df["Type"].value_counts()

    overview_cards = [
        (
            "Document Checks",
            type_counts.get("Document Check", 0),
            "type-document",
        ),
        (
            "SI Requests",
            type_counts.get("SI Request", 0),
            "type-si",
        ),
        (
            "Invoice Questions",
            type_counts.get("Invoice Question", 0),
            "type-invoice",
        ),
        (
            "Operational Updates",
            type_counts.get("Operational Update", 0),
            "type-operational",
        ),
        (
            "Spam",
            type_counts.get("Spam", 0),
            "type-spam",
        ),
    ]

    overview_cols = st.columns(5)

    for col, (title, value, css_class) in zip(
        overview_cols,
        overview_cards,
    ):

        with col:

            st.markdown(
                f"""
                <div class="metric-card {css_class}">
                    <div class="metric-title">
                        {safe_text(title)}
                    </div>

                    <div class="metric-value">
                        {value}
                    </div>

                    <div class="metric-label">
                        records
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    left_space, priority_col, filter_col, sort_col = st.columns(
        [2.2, 1.0, 1.0, 1.0]
    )

    with priority_col:
        priority_filter = st.selectbox(
            "Priority",
            ["All Priorities", "Urgent", "Normal", "Low"],
            label_visibility="collapsed",
            key="home_priority_filter",
        )

    with filter_col:
        shipment_filter = st.selectbox(
            "Shipment",
            [
                "All Shipments",
                "International",
                "Domestic",
            ],
            label_visibility="collapsed",
            key="home_shipment_filter",
        )

    with sort_col:
        priority_sort = st.selectbox(
            "Sort",
            [
                "Priority",
                "Newest",
                "Oldest",
            ],
            label_visibility="collapsed",
            key="home_sort",
        )

    filtered_df = search_dataframe(
        df,
        st.session_state.get(
            "search_query",
            "",
        ),
    )

    if priority_filter != "All Priorities":
        filtered_df = filtered_df[
            filtered_df["Priority"] == priority_filter
        ]

    if shipment_filter != "All Shipments":

        filtered_df = filtered_df[
            filtered_df["Shipment Type"]
            == shipment_filter
        ]

    filtered_df = sort_records(
        filtered_df,
        priority_sort,
    )

    # HOME TABLE PAGINATION
    # Only render a small number of records at once.
    # This keeps the dashboard responsive even with 520+ emails.
    home_page_size = 20
    home_total_records = len(filtered_df)
    home_total_pages = max(
        1,
        (home_total_records + home_page_size - 1)
        // home_page_size,
    )

    if "home_table_page" not in st.session_state:
        st.session_state["home_table_page"] = 1

    # Clamp page number when filters/search reduce the result count.
    st.session_state["home_table_page"] = min(
        max(
            int(st.session_state["home_table_page"]),
            1,
        ),
        home_total_pages,
    )

    def _home_previous_page():
        st.session_state["home_table_page"] = max(
            1,
            int(st.session_state.get("home_table_page", 1)) - 1,
        )

    def _home_next_page():
        st.session_state["home_table_page"] = min(
            home_total_pages,
            int(st.session_state.get("home_table_page", 1)) + 1,
        )

    home_current_page = int(
        st.session_state["home_table_page"]
    )

    home_start = (
        (home_current_page - 1)
        * home_page_size
    )

    home_end = min(
        home_start + home_page_size,
        home_total_records,
    )

    home_page_df = filtered_df.iloc[
        home_start:home_end
    ]

    st.markdown(
        """
        <div class="priority-header">
            <div>
                <div class="priority-title">
                    Today's Priorities
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="table-head">
            <div style="
                display:grid;
                grid-template-columns:
                1fr 2.55fr 1.1fr .8fr .8fr 1.1fr .7fr;
                gap:12px;
            ">
                <div>Type</div>
                <div>Subject</div>
                <div>Shipment</div>
                <div>Priority</div>
                <div>Received</div>
                <div>Confidence</div>
                <div>Action</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if filtered_df.empty:

        st.markdown(
            """
            <div class="table-box">
                <div style="
                    padding:28px;
                    text-align:center;
                    color:#71839b;
                    font-size:13px;
                ">
                    No matching records found.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        page_info_col, prev_col, next_col = st.columns(
            [4.0, 1.0, 1.0]
        )

        with page_info_col:
            if home_total_records:
                st.caption(
                    f"Showing {home_start + 1}–{home_end} "
                    f"of {home_total_records} records · "
                    f"Page {home_current_page} "
                    f"of {home_total_pages}"
                )

        with prev_col:
            st.button(
                "← Previous",
                key="home_previous_page",
                use_container_width=True,
                disabled=home_current_page <= 1,
                on_click=_home_previous_page,
            )

        with next_col:
            st.button(
                "Next →",
                key="home_next_page",
                use_container_width=True,
                disabled=home_current_page >= home_total_pages,
                on_click=_home_next_page,
            )

        for index, row in home_page_df.iterrows():

            row_cols = st.columns(
                [1.0, 2.55, 1.1, .8, .8, 1.1, .7]
            )

            with row_cols[0]:

                st.markdown(
                    type_badge(row["Type"]),
                    unsafe_allow_html=True,
                )

            with row_cols[1]:

                st.markdown(
                    f"""
                    <div class="subject-text">
                        {safe_text(row["Subject"])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with row_cols[2]:

                st.markdown(
                    f"""
                    <div class="shipment-text">
                        {safe_text(row["Shipment"])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with row_cols[3]:

                st.markdown(
                    priority_badge(row["Priority"]),
                    unsafe_allow_html=True,
                )

            with row_cols[4]:

                st.markdown(
                    f"""
                    <div class="received-text">
                        {safe_text(row["Received"])}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with row_cols[5]:

                st.markdown(
                    confidence_bar_html(
                        row.get("Confidence", "LOW")
                    ),
                    unsafe_allow_html=True,
                )

            with row_cols[6]:

                if st.button(
                    "View",
                    key=f"home_view_{row['ID']}_{index}",
                    use_container_width=False,
                ):

                    open_record(row.to_dict())

            st.divider()


# ============================================================
# ANALYTICS
# ============================================================

elif page_to_show == "Analytics":

    render_page_header(
        "Analytics",
        "Operational overview and document activity.",
    )

    if st.button(
        "← Back to Home",
        key="analytics_back_home",
    ):
        go_to(
            main_nav="Home",
            insights_nav=None,
            system_nav=None,
            page_override=None,
            case_view=False,
            selected_record_id=None,
        )

    st.write("")

    render_discrepancy_intelligence(
        df=st.session_state["df"],
        full_results=(
            st.session_state.get(
                "full_analysis_results"
            )
            or []
        ),
        total_records=len(
            st.session_state["df"]
        ),
    )

    st.write("")

    total_emails = len(df)

    analysis_summary = (
        st.session_state.get("full_analysis_summary") or {}
    )

    analysis_results = (
        st.session_state.get("full_analysis_results")
        or []
    )

    mismatch_count = int(
        analysis_summary.get("mismatch", 0)
    )

    review_count = int(
        analysis_summary.get("needs_review", 0)
    )

    failed_count = int(
        analysis_summary.get("failed", 0)
    )

    no_issue_count = int(
        analysis_summary.get("ok", 0)
    )

    action_required = (
        mismatch_count
        + review_count
        + failed_count
    )

    record_types = {
        str(row["ID"]): row["Type"]
        for _, row in df.iterrows()
    }

    open_document_checks = sum(
        1
        for result in analysis_results
        if (
            record_types.get(
                str(result.get("email_id"))
            ) == "Document Check"
            and str(
                result.get("status") or ""
            ).lower()
            in {
                "mismatch",
                "human_review",
                "failed",
            }
        )
    )

    a, b, c, d = st.columns(4)

    a.metric(
        "Total Records",
        total_emails,
    )

    b.metric(
        "Action Required",
        action_required,
    )

    c.metric(
        "Open Document Checks",
        open_document_checks,
    )

    d.metric(
        "No Issues",
        no_issue_count,
    )

    st.write("")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">
                    Email Classification
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        email_df = (
            df["Type"]
            .value_counts()
            .rename_axis("Category")
            .reset_index(name="Count")
        )

        email_chart = {
            "mark": {
                "type": "bar",
                "cornerRadiusTopLeft": 6,
                "cornerRadiusTopRight": 6,
            },
            "encoding": {
                "x": {
                    "field": "Category",
                    "type": "nominal",
                    "axis": {
                        "labelAngle": -20,
                    },
                },
                "y": {
                    "field": "Count",
                    "type": "quantitative",
                },
                "color": {
                    "value": "#7dd3fc",
                },
                "tooltip": [
                    {
                        "field": "Category",
                        "type": "nominal",
                    },
                    {
                        "field": "Count",
                        "type": "quantitative",
                    },
                ],
            },
        }

        st.vega_lite_chart(
            email_df,
            email_chart,
            use_container_width=True,
        )

    with col2:

        st.markdown(
            """
            <div class="panel">
                <div class="panel-title">
                    Shipment Type
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        ship_df = (
            df["Shipment Type"]
            .value_counts()
            .rename_axis("Shipment Type")
            .reset_index(name="Count")
        )

        ship_chart = {
            "mark": {
                "type": "bar",
                "cornerRadiusTopLeft": 6,
                "cornerRadiusTopRight": 6,
            },
            "encoding": {
                "x": {
                    "field": "Shipment Type",
                    "type": "nominal",
                },
                "y": {
                    "field": "Count",
                    "type": "quantitative",
                },
                "color": {
                    "value": "#93c5fd",
                },
                "tooltip": [
                    {
                        "field": "Shipment Type",
                        "type": "nominal",
                    },
                    {
                        "field": "Count",
                        "type": "quantitative",
                    },
                ],
            },
        }

        st.vega_lite_chart(
            ship_df,
            ship_chart,
            use_container_width=True,
        )

    st.write("")

    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">
                Priority Distribution
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    p_df = (
        df["Priority"]
        .value_counts()
        .rename_axis("Priority")
        .reset_index(name="Cases")
    )

    priority_chart = {
        "mark": {
            "type": "arc",
            "innerRadius": 48,
            "stroke": "#ffffff",
            "strokeWidth": 2,
        },
        "encoding": {
            "theta": {
                "field": "Cases",
                "type": "quantitative",
            },
            "color": {
                "field": "Priority",
                "type": "nominal",
                "scale": {
                    "range": [
                        "#ef4444",
                        "#f59e0b",
                        "#10b981",
                    ],
                },
                "legend": {
                    "orient": "right",
                },
            },
            "tooltip": [
                {
                    "field": "Priority",
                    "type": "nominal",
                },
                {
                    "field": "Cases",
                    "type": "quantitative",
                },
            ],
        },
        "width": 420,
        "height": 260,
    }

    st.vega_lite_chart(
        p_df,
        priority_chart,
        use_container_width=True,
    )


# ============================================================
# RECENT ACTIVITY
# ============================================================

elif page_to_show == "Recent Activity":

    render_page_header(
        "Recent Activity",
        "Search recent activity and open any record directly.",
    )

    activity_search = st.text_input(
        "Search recent activity",
        placeholder=(
            "Search document name, shipment or category..."
        ),
        label_visibility="collapsed",
        key="activity_search",
    )

    activities = []

    for _, row in df.sort_values(
        "Received",
        key=lambda s: s.apply(parse_received_time),
        ascending=False,
    ).iterrows():

        activities.append(
            {
                "event_id": f"record_received_{row['ID']}",
                "title": (
                    "Document discrepancy found"
                    if row["Type"] == "Document Check"
                    else f"{row['Type']} received"
                ),
                "shipment": row["Shipment"],
                "time": row["Received"],
                "type": row["Type"],
            }
        )

    activities = (
        st.session_state["activity_log"]
        + activities
    )

    if activity_search.strip():

        q = activity_search.strip().lower()

        activities = [
            item
            for item in activities
            if q in " ".join(
                [
                    str(item.get("title", "")),
                    str(item.get("shipment", "")),
                    str(item.get("type", "")),
                    str(item.get("time", "")),
                ]
            ).lower()
        ]

    unique_activities = []
    seen_activity_ids = set()

    for item in activities:

        event_id = item.get(
            "event_id",
            f"{item.get('title')}|{item.get('shipment')}|{item.get('time')}",
        )

        if event_id in seen_activity_ids:
            continue

        seen_activity_ids.add(event_id)
        unique_activities.append(item)

    activities = unique_activities

    st.markdown(
        '<div class="panel">',
        unsafe_allow_html=True,
    )

    if not activities:

        st.info(
            "No recent activity matches your search."
        )

    for activity_index, item in enumerate(activities):

        title = item["title"]
        shipment = item["shipment"]
        time = item["time"]
        category = item["type"]

        record = (
            get_record_by_shipment(shipment)
            or
            {
                "ID": f"activity_{activity_index}",
                "Subject": title,
                "Shipment": shipment,
                "Type": category,
                "Priority": "Normal",
                "Received": time,
                "Shipment Type": "International",
                "Status": "Done",
            }
        )

        c1, c2, c3, c4 = st.columns(
            [3.7, 1.25, 1.05, .75]
        )

        with c1:

            st.markdown(
                f"""
                <div class="subject-text">
                    {safe_text(title)}
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.caption(
                f"{shipment} · {time}"
            )

        with c2:

            st.markdown(
                type_badge(category),
                unsafe_allow_html=True,
            )

        with c3:

            st.markdown(
                status_badge(
                    record.get(
                        "Status",
                        "Done",
                    )
                ),
                unsafe_allow_html=True,
            )

        with c4:

            if st.button(
                "View",
                key=(
                    f"activity_view_"
                    f"{item.get('event_id', activity_index)}"
                ),
                use_container_width=False,
            ):

                open_record(record)

        st.divider()

    st.markdown(
        '</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# DOCUMENT CHECKS
# ============================================================

elif page_to_show == "Document Checks":

    render_page_header(
        "Document Checks",
        (
            "Review shipping documents and identify "
            "discrepancies before finalising them."
        ),
    )

    document_checks_df = df[
        df["Type"] == "Document Check"
    ].copy()

    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">
                Open Document Checks
            </div>

            <div class="small-muted">
                Each record can be opened as a full review screen.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")

    render_export_button(
        df=st.session_state["df"],
        full_results=(
            st.session_state.get(
                "full_analysis_results"
            )
            or []
        ),
        pipeline_results=(
            st.session_state.get(
                "pipeline_results",
                {},
            )
        ),
    )

    st.write("")

    render_filtered_records(
        document_checks_df,
        "No document checks found.",
        search_key="document_checks_search",
    )


# ============================================================
# DOCUMENT CHECK CASE
# ============================================================

elif page_to_show == "Document Check Case":

    record = get_record_by_id(
        st.session_state.get(
            "selected_record_id"
        )
    )

    if record is None:

        record = get_record_by_shipment(
            "SI-2026-0821"
        )

    if record is None and not df.empty:

        record = df.iloc[0].to_dict()

    if record is None:

        st.error("No record is available.")
        st.stop()

    if st.button(
        "Back to Document Checks",
        key="case_back",
    ):

        go_to(
            main_nav="Document Checks",
            insights_nav=None,
            system_nav=None,
            case_view=False,
            selected_record_id=None,
        )

    st.markdown(
        '<div class="page-accent"></div>',
        unsafe_allow_html=True,
    )

    header_html = f"""
    <div class="case-banner">

        <div style="
            font-size:12px;
            color:#5d7590;
            font-weight:700;
            letter-spacing:.4px;
        ">
            {safe_text(record["Type"].upper())}
            ·
            DOCUMENT REVIEW
        </div>

        <h2 style="margin:4px 0 8px; color:#0f2942 !important;">
            {safe_text(record["Subject"])}
        </h2>

        {priority_badge(record["Priority"])}

        {status_badge(get_record_display_status(record))}

        <span style="
            color:#70839a;
            font-size:12px;
            margin-left:6px;
        ">
            {safe_text(record["Shipment"])}
            ·
            {safe_text(record["Shipment Type"])}
            ·
            Received {safe_text(record["Received"])}
        </span>

    </div>
    """

    st.markdown(
        header_html,
        unsafe_allow_html=True,
    )

    st.write("")

    if record["Type"] == "Document Check":

        main, side = st.columns(
            [2.2, 1],
            gap="large",
        )

        with main:

            tab1, tab2, tab3 = st.tabs(
                [
                    "Comparison",
                    "Email & Documents",
                    "Review Notes",
                ]
            )

            with tab1:

                st.markdown(
                    """
                    <div class="panel-title">
                        Shipment Details Comparison
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.caption(
                    "The system highlights fields that differ "
                    "between the shipping instruction and draft BL."
                )

                comp = get_comparison_for_record(record)

                comp = build_comparison_statuses(comp)

                if comp.empty:

                    st.info(
                        "No comparison data is currently available "
                        "for this record."
                    )

                else:

                    for _, r in comp.iterrows():

                        c1, c2, c3, c4 = st.columns(
                            [1.05, 1.35, 1.35, .7]
                        )

                        c1.write(r["Field"])

                        c2.caption(
                            r["Shipping Instruction (SI)"]
                        )

                        c3.caption(
                            r["Draft Bill of Lading (BL)"]
                        )

                        if r["Status"] == "Discrepancy":

                            c4.markdown(
                                """
                                <span class="badge badge-red">
                                    Discrepancy
                                </span>
                                """,
                                unsafe_allow_html=True,
                            )

                        else:

                            c4.markdown(
                                """
                                <span class="badge badge-green">
                                    Match
                                </span>
                                """,
                                unsafe_allow_html=True,
                            )

                        st.divider()

                discrepancies = get_discrepancies(comp)

                if not discrepancies.empty:

                    for _, discrepancy in discrepancies.iterrows():

                        field_name = discrepancy["Field"]

                        si_value = discrepancy[
                            "Shipping Instruction (SI)"
                        ]

                        bl_value = discrepancy[
                            "Draft Bill of Lading (BL)"
                        ]

                        difference = format_difference(
                            si_value,
                            bl_value,
                        )

                        difference_text = ""

                        if difference is not None:

                            difference_text = (
                                f" · Difference: {difference}"
                            )

                        st.markdown(
                            f"""
                            <div class="discrepancy">

                                <b>
                                    WARNING: {safe_text(field_name)}
                                    Discrepancy
                                </b>

                                <br>

                                <span class="small-muted">
                                    SI states
                                    {safe_text(si_value)}
                                    ·
                                    BL states
                                    {safe_text(bl_value)}
                                    {safe_text(difference_text)}
                                </span>

                                <br><br>

                                <span style="font-size:13px;">
                                    Please confirm the correct
                                    {safe_text(field_name).lower()}
                                    with the customer before
                                    finalising the BL.
                                </span>

                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.write("")

                else:

                    st.success(
                        "No discrepancies detected in the "
                        "current comparison data."
                    )

            processing_result = None

            for analysis_result in (
                st.session_state.get(
                    "full_analysis_results"
                )
                or []
            ):
                if str(
                    analysis_result.get("email_id")
                ) == str(record.get("ID")):
                    processing_result = analysis_result
                    break

            if processing_result is None:
                processing_result = (
                    st.session_state.get(
                        "pipeline_results",
                        {},
                    ).get(record.get("ID"))
                )

            render_processing_log(
                processing_result,
                record.get("ID"),
            )

            st.write("")


            with tab2:

                st.markdown(
                    """
                    <div class="panel">
                        <div class="panel-title">
                            Email Details
                        </div>

                        <div style="
                            margin-top:14px;
                            border:1px solid #e3ebf5;
                            border-radius:10px;
                            background:#ffffff;
                            overflow:hidden;
                        ">

                            <div style="
                                padding:11px 14px;
                                border-bottom:1px solid #edf1f5;
                                display:flex;
                                gap:14px;
                            ">
                                <div style="
                                    width:75px;
                                    color:#71839b;
                                    font-size:11px;
                                    font-weight:600;
                                ">
                                    From
                                </div>

                                <div style="
                                    color:#233b57;
                                    font-size:12px;
                                ">
                                    customer@abcshipping.com
                                </div>
                            </div>

                            <div style="
                                padding:11px 14px;
                                border-bottom:1px solid #edf1f5;
                                display:flex;
                                gap:14px;
                            ">
                                <div style="
                                    width:75px;
                                    color:#71839b;
                                    font-size:11px;
                                    font-weight:600;
                                ">
                                    To
                                </div>

                                <div style="
                                    color:#233b57;
                                    font-size:12px;
                                ">
                                    operations@yourcompany.com
                                </div>
                            </div>

                            <div style="
                                padding:11px 14px;
                                border-bottom:1px solid #edf1f5;
                                display:flex;
                                gap:14px;
                            ">
                                <div style="
                                    width:75px;
                                    color:#71839b;
                                    font-size:11px;
                                    font-weight:600;
                                ">
                                    Subject
                                </div>

                                <div style="
                                    color:#233b57;
                                    font-size:12px;
                                ">
                                    {safe_text(record["Subject"])}
                                </div>
                            </div>

                            <div style="
                                padding:11px 14px;
                                display:flex;
                                gap:14px;
                            ">
                                <div style="
                                    width:75px;
                                    color:#71839b;
                                    font-size:11px;
                                    font-weight:600;
                                ">
                                    Attachments
                                </div>

                                <div style="
                                    color:#233b57;
                                    font-size:12px;
                                ">
                                    2 documents
                                </div>
                            </div>

                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.write("")

                st.markdown(
                    """
                    <div class="panel">
                        <div class="panel-title">
                            Attached Documents
                        </div>

                        <div style="
                            margin-top:12px;
                            display:flex;
                            flex-direction:column;
                            gap:10px;
                        ">

                            <div style="
                                border:1px solid #dfe9f5;
                                border-radius:10px;
                                padding:12px 14px;
                                background:#f8fbff;
                                display:flex;
                                align-items:center;
                                justify-content:space-between;
                            ">
                                <div style="
                                    display:flex;
                                    align-items:center;
                                    gap:11px;
                                ">
                                    <div style="
                                        width:34px;
                                        height:34px;
                                        border-radius:8px;
                                        background:#eef2ff;
                                        display:flex;
                                        align-items:center;
                                        justify-content:center;
                                        font-size:12px;
                                        color:#3b82f6;
                                        font-weight:700;
                                    ">
                                        PDF
                                    </div>

                                    <div>
                                        <div style="
                                            color:#233b57;
                                            font-size:12px;
                                            font-weight:600;
                                        ">
                                            SI_2026_0821.pdf
                                        </div>

                                        <div style="
                                            color:#71839b;
                                            font-size:10px;
                                            margin-top:2px;
                                        ">
                                            Shipping Instruction
                                        </div>
                                    </div>
                                </div>

                                <span class="badge badge-blue">
                                    PDF
                                </span>
                            </div>

                            <div style="
                                border:1px solid #dfe9f5;
                                border-radius:10px;
                                padding:12px 14px;
                                background:#f8fbff;
                                display:flex;
                                align-items:center;
                                justify-content:space-between;
                            ">
                                <div style="
                                    display:flex;
                                    align-items:center;
                                    gap:11px;
                                ">
                                    <div style="
                                        width:34px;
                                        height:34px;
                                        border-radius:8px;
                                        background:#eef2ff;
                                        display:flex;
                                        align-items:center;
                                        justify-content:center;
                                        font-size:12px;
                                        color:#3b82f6;
                                        font-weight:700;
                                    ">
                                        PDF
                                    </div>

                                    <div>
                                        <div style="
                                            color:#233b57;
                                            font-size:12px;
                                            font-weight:600;
                                        ">
                                            Draft_BL_2026_0821.pdf
                                        </div>

                                        <div style="
                                            color:#71839b;
                                            font-size:10px;
                                            margin-top:2px;
                                        ">
                                            Draft Bill of Lading
                                        </div>
                                    </div>
                                </div>

                                <span class="badge badge-blue">
                                    PDF
                                </span>
                            </div>

                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.caption(
                    "BACKEND INTEGRATION POINT: "
                    "Replace demo email metadata and attachment "
                    "list with backend document/email data."
                )

            with tab3:

                existing_note = get_review_note(
                    record["ID"]
                )

                review_note = st.text_area(
                    "Review note",
                    value=existing_note,
                    placeholder=(
                        "Add a short note for the operations team..."
                    ),
                    key=f"review_note_{record['ID']}",
                )

                if st.button(
                    "Save note",
                    key=f"save_note_{record['ID']}",
                ):

                    save_review_note(
                        record["ID"],
                        review_note,
                    )

                    add_activity(
                        "Review note saved",
                        record["Shipment"],
                        record["Type"],
                        event_key=(
                            f"review_note_saved_{record['ID']}_"
                            f"{review_note.strip()}"
                        ),
                    )

                    st.success(
                        "Review note saved."
                    )

                st.markdown("---")
                st.markdown("### Human Correction & Re-verification")

                review_comp = build_comparison_statuses(
                    get_comparison_for_record(record)
                )

                review_discrepancies = get_discrepancies(
                    review_comp
                )

                if st.session_state.get("demo_mode", False):
                    st.info(
                        "Human correction and re-verification require the live source inbox."
                    )
                    review_discrepancies = pd.DataFrame()

                correction_field_map = {
                    "Shipper": "shipper",
                    "Consignee": "consignee",
                    "Notify Party": "notify_party",
                    "Port of Loading": "port_of_loading",
                    "Port of Discharge": "port_of_discharge",
                    "Container Count": "container_count",
                    "Gross Weight (KG)": "gross_weight_kg",
                }

                correction_inputs = []

                if not review_discrepancies.empty:

                    st.caption(
                        "Correct extracted values and run the same verification logic again."
                    )

                    with st.form(
                        key=f"human_correction_form_{record['ID']}"
                    ):

                        for _, correction_row in review_discrepancies.iterrows():

                            correction_field = correction_row[
                                "Field"
                            ]

                            canonical_field = (
                                correction_field_map.get(
                                    correction_field
                                )
                            )

                            if not canonical_field:
                                continue

                            original_si = str(
                                correction_row[
                                    "Shipping Instruction (SI)"
                                ]
                            )

                            original_bl = str(
                                correction_row[
                                    "Draft Bill of Lading (BL)"
                                ]
                            )

                            st.markdown(
                                f"**{correction_field}**"
                            )

                            edit_si_col, edit_bl_col = st.columns(2)

                            with edit_si_col:
                                st.text_input(
                                    "Shipping Instruction (reference)",
                                    value=original_si,
                                    disabled=True,
                                    key=(
                                        f"reference_si_v3_"
                                        f"{record['ID']}_"
                                        f"{canonical_field}"
                                    ),
                                )

                                edited_si = original_si

                            with edit_bl_col:
                                edited_bl = st.text_input(
                                    "Draft Bill of Lading",
                                    value=original_bl,
                                    key=(
                                        f"correct_bl_v3_"
                                        f"{record['ID']}_"
                                        f"{canonical_field}"
                                    ),
                                )

                            correction_inputs.append(
                                {
                                    "field": canonical_field,
                                    "original_si": original_si,
                                    "original_bl": original_bl,
                                    "edited_si": edited_si,
                                    "edited_bl": edited_bl,
                                }
                            )

                        reviewer_name = st.text_input(
                            "Reviewer",
                            value=USER_NAME,
                            key=f"reviewer_{record['ID']}",
                        )

                        correction_note = st.text_area(
                            "Correction note",
                            placeholder=(
                                "Explain why the correction was made..."
                            ),
                            key=f"correction_note_{record['ID']}",
                        )

                        apply_correction = st.form_submit_button(
                            "Apply & Re-verify",
                            type="primary",
                            use_container_width=True,
                        )

                    if apply_correction:

                        si_corrections = {}
                        bl_corrections = {}

                        for correction_item in correction_inputs:

                            field = correction_item["field"]

                            if (
                                correction_item["edited_si"].strip()
                                != correction_item["original_si"].strip()
                            ):
                                si_corrections[field] = (
                                    correction_item["edited_si"].strip()
                                )

                            if (
                                correction_item["edited_bl"].strip()
                                != correction_item["original_bl"].strip()
                            ):
                                bl_corrections[field] = (
                                    correction_item["edited_bl"].strip()
                                )

                        if not si_corrections and not bl_corrections:
                            st.warning(
                                "Change at least one value before re-verifying."
                            )

                        else:
                            correction_result = (
                                apply_record_human_correction(
                                    record["ID"],
                                    si_corrections,
                                    bl_corrections,
                                    reviewer_name,
                                    correction_note,
                                )
                            )

                            st.success(
                                "Re-verification completed: "
                                f"{correction_result.get('status')}"
                            )

                            st.rerun()

                correction_result = (
                    st.session_state[
                        "human_correction_results"
                    ].get(
                        str(record["ID"])
                    )
                )

                if correction_result:

                    human_review = (
                        correction_result.get(
                            "human_review"
                        ) or {}
                    )

                    st.markdown("#### Audit Trail")

                    st.caption(
                        "Reviewer: "
                        f"{human_review.get('reviewer') or 'Unknown'}"
                        " · "
                        "Reviewed at: "
                        f"{human_review.get('reviewed_at') or 'Unknown'}"
                    )

                    for change in human_review.get(
                        "changes",
                        [],
                    ):
                        st.write(
                            f"{change.get('side')}.{change.get('field')}: "
                            f"{change.get('before')} → "
                            f"{change.get('after')}"
                        )

                    correction_status = correction_result.get(
                        "status"
                    )

                    if correction_status == "OK":
                        st.success(
                            "Re-verification passed. No mismatch detected."
                        )
                    elif correction_status == "MISMATCH":
                        st.error(
                            "Re-verification completed. Discrepancies remain."
                        )
                    else:
                        st.warning(
                            "This case still requires human review."
                        )

        with side:

            backend_result = get_effective_backend_result(
                record.get("ID")
            )

            evidence_map = (
                backend_result.get("evidence") or {}
            )

            evidence_field_map = {
                "Shipper": "shipper",
                "Consignee": "consignee",
                "Notify Party": "notify_party",
                "Port of Loading": "port_of_loading",
                "Port of Discharge": "port_of_discharge",
                "Container Count": "container_count",
                "Gross Weight (KG)": "gross_weight_kg",
            }

            comp = build_comparison_statuses(
                get_comparison_for_record(record)
            )

            discrepancies = get_discrepancies(comp)

            discrepancy_count = len(discrepancies)

            plural_text = (
                "discrepancy"
                if discrepancy_count == 1
                else "discrepancies"
            )

            st.markdown(
                f"""
                <div class="ai-summary">

                    <div class="ai-summary-title">
                        AI Review Summary
                    </div>

                    <div class="ai-summary-label">
                        Issues detected
                    </div>

                    <div class="ai-summary-value">
                        {discrepancy_count} {plural_text}
                    </div>
                """,
                unsafe_allow_html=True,
            )

            if not discrepancies.empty:

                for _, discrepancy in discrepancies.iterrows():

                    field_name = discrepancy["Field"]

                    si_value = discrepancy[
                        "Shipping Instruction (SI)"
                    ]

                    bl_value = discrepancy[
                        "Draft Bill of Lading (BL)"
                    ]

                    difference = format_difference(
                        si_value,
                        bl_value,
                    )

                    evidence_key = evidence_field_map.get(
                        field_name
                    )

                    field_evidence = (
                        evidence_map.get(evidence_key, {})
                        if evidence_key
                        else {}
                    )

                    si_evidence = (
                        field_evidence.get("si") or {}
                    )

                    bl_evidence = (
                        field_evidence.get("bl") or {}
                    )

                    st.markdown(
                        f"""
                        <hr>

                        <div class="ai-summary-label">
                            Field
                        </div>

                        <div class="ai-summary-value">
                            {safe_text(field_name)}
                        </div>

                        <br>

                        <div class="ai-summary-label">
                            Shipping Instruction
                        </div>

                        <div class="ai-summary-value">
                            {safe_text(si_value)}
                        </div>

                        <br>

                        <div class="ai-summary-label">
                            Draft Bill of Lading
                        </div>

                        <div class="ai-summary-value">
                            {safe_text(bl_value)}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if si_evidence or bl_evidence:

                        si_confidence = si_evidence.get(
                            "confidence"
                        )
                        bl_confidence = bl_evidence.get(
                            "confidence"
                        )

                        si_confidence_text = (
                            f"{float(si_confidence) * 100:.0f}%"
                            if si_confidence is not None
                            else "N/A"
                        )

                        bl_confidence_text = (
                            f"{float(bl_confidence) * 100:.0f}%"
                            if bl_confidence is not None
                            else "N/A"
                        )

                        st.markdown(
                            """
                            <div class="ai-summary-label">
                                Evidence Grounding
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        with st.expander(
                            f"View evidence for {field_name}"
                        ):

                            st.markdown(
                                "**Shipping Instruction evidence**"
                            )

                            st.write(
                                si_evidence.get(
                                    "snippet",
                                    "No evidence available.",
                                )
                            )

                            st.caption(
                                "Confidence: "
                                f"{si_confidence_text} · "
                                "Source: "
                                f"{si_evidence.get('source', 'N/A')} · "
                                "Method: "
                                f"{si_evidence.get('method', 'N/A')}"
                            )

                            st.markdown(
                                "**Draft Bill of Lading evidence**"
                            )

                            st.write(
                                bl_evidence.get(
                                    "snippet",
                                    "No evidence available.",
                                )
                            )

                            st.caption(
                                "Confidence: "
                                f"{bl_confidence_text} · "
                                "Source: "
                                f"{bl_evidence.get('source', 'N/A')} · "
                                "Method: "
                                f"{bl_evidence.get('method', 'N/A')}"
                            )

                    if difference is not None:

                        st.markdown(
                            f"""
                            <br>

                            <div class="ai-summary-label">
                                Difference
                            </div>

                            <div class="ai-summary-value">
                                {safe_text(difference)}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

            st.write("")

            st.markdown(
                """
                <div class="panel">

                    <div class="panel-title">
                        AI Explanation
                    </div>
                """,
                unsafe_allow_html=True,
            )

            if not discrepancies.empty:

                st.write(
                    "The system found discrepancy data in "
                    "the current document comparison."
                )

                st.markdown(
                    "<ul style='font-size:12px;color:#60748d;'>",
                    unsafe_allow_html=True,
                )

                for _, discrepancy in discrepancies.iterrows():

                    st.markdown(
                        f"""
                        <li>
                            <b>{safe_text(discrepancy["Field"])}</b>:
                            SI =
                            {safe_text(discrepancy["Shipping Instruction (SI)"])}
                            · BL =
                            {safe_text(discrepancy["Draft Bill of Lading (BL)"])}
                        </li>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown(
                    "</ul>",
                    unsafe_allow_html=True,
                )

            else:

                st.write(
                    "No discrepancy is currently detected "
                    "from the comparison data."
                )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

            st.write("")

            st.markdown(
                """
                <div class="panel">

                    <div class="panel-title">
                        Suggested Actions
                    </div>

                    <div class="action-box">
                        Contact customer to confirm
                        the correct information.
                    </div>

                    <br>

                    <div class="action-box">
                        Update Draft BL if the SI is confirmed.
                    </div>

                    <br>

                    <div class="action-box">
                        Re-check related documents.
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write("")

            if record.get("Status") != "Done":

                if st.button(
                    "Mark as Reviewed",
                    use_container_width=True,
                    key=f"mark_reviewed_{record['ID']}",
                ):

                    record_id = record["ID"]

                    update_record_status(
                        record_id,
                        "Done",
                    )

                    st.session_state[
                        "selected_record_id"
                    ] = record_id

                    add_activity(
                        "Document review completed",
                        record["Shipment"],
                        record["Type"],
                        event_key=(
                            f"document_review_completed_{record_id}"
                        ),
                    )

                    st.success(
                        "Case marked as reviewed."
                    )

                    st.rerun()

            else:

                st.success(
                    "This case has already been reviewed."
                )

    else:

        left, right = st.columns(
            [2.2, 1],
            gap="large",
        )

        with left:

            st.markdown(
                """
                <div class="panel">
                    <div class="panel-title">
                        Document Summary
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write(
                f"**Document type:** {record['Type']}"
            )

            st.write(
                f"**Shipment / reference:** {record['Shipment']}"
            )

            st.write(
                f"**Priority:** {record['Priority']}"
            )

            st.write(
                f"**Current status:** "
                f"{record.get('Status', 'Under Review')}"
            )

            note = get_review_note(
                record["ID"]
            )

            if note:

                st.write("")

                st.markdown(
                    """
                    <div class="info-box">
                        <div class="panel-title">
                            Review Note
                        </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.write(note)

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True,
                )

            st.write("")

            st.info(
                "This frontend review screen is ready "
                "for the backend document content to be connected."
            )

        with right:

            st.markdown(
                """
                <div class="panel">
                    <div class="panel-title">
                        Review
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                status_badge(
                    record.get(
                        "Status",
                        "Under Review",
                    )
                ),
                unsafe_allow_html=True,
            )

            st.write("")

            if record.get("Status") != "Done":

                if st.button(
                    "Mark as Reviewed",
                    use_container_width=True,
                    key=f"mark_reviewed_generic_{record['ID']}",
                ):

                    record_id = record["ID"]

                    update_record_status(
                        record_id,
                        "Done",
                    )

                    st.session_state[
                        "selected_record_id"
                    ] = record_id

                    add_activity(
                        "Record review completed",
                        record["Shipment"],
                        record["Type"],
                        event_key=(
                            f"record_review_completed_{record_id}"
                        ),
                    )

                    st.success(
                        "Document marked as reviewed."
                    )

                    st.rerun()

            else:

                st.success(
                    "This document has already been reviewed."
                )


# ============================================================
# SETTINGS
# ============================================================

elif page_to_show == "Settings":

    render_page_header(
        "Settings",
        "Manage your ShipGuard AI workspace preferences.",
    )

    if st.button(
        "Back to Home",
        key="settings_back",
    ):

        st.session_state["_pending_nav"] = {
            "main_nav": "Home",
            "insights_nav": None,
            "system_nav": None,
            "page_override": None,
            "case_view": False,
            "selected_record_id": None,
        }
        st.rerun()

    st.write("")

    email_notifications = st.toggle(
        "Email notifications",
        value=True,
        key="setting_email_notifications",
    )

    ai_alerts = st.toggle(
        "AI discrepancy alerts",
        value=True,
        key="setting_ai_alerts",
    )

    daily_summary = st.toggle(
        "Daily operations summary",
        value=False,
        key="setting_daily_summary",
    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True,
    )

    st.caption(
        "Settings are currently stored in the frontend session. "
        "Connect these controls to the backend when available."
    )


# ============================================================
# INBOX
# ============================================================

elif page_to_show == "Inbox":

    render_page_header(
        "Inbox",
        "All incoming shipping-related emails.",
    )

    inbox_df = df.copy()

    render_filtered_records(
        inbox_df,
        "No emails match your search.",
        search_key="inbox_search",
    )


# ============================================================
# SI REQUESTS
# ============================================================

elif page_to_show == "SI Requests":

    render_page_header(
        "SI Requests",
        "Shipping Instruction requests received from customers.",
    )

    si_df = df[
        df["Type"] == "SI Request"
    ].copy()

    render_filtered_records(
        si_df,
        "No SI requests found.",
        search_key="si_search",
    )


# ============================================================
# INVOICES
# ============================================================

elif page_to_show == "Invoices":

    render_page_header(
        "Invoices",
        "Invoice-related questions and documents.",
    )

    invoice_df = df[
        df["Type"] == "Invoice Question"
    ].copy()

    render_filtered_records(
        invoice_df,
        "No invoice questions found.",
        search_key="invoice_search",
    )


# ============================================================
# OPERATIONAL UPDATES
# ============================================================

elif page_to_show == "Operational Updates":

    render_page_header(
        "Operational Updates",
        "Operational shipment updates and vessel information.",
    )

    operational_df = df[
        df["Type"] == "Operational Update"
    ].copy()

    render_filtered_records(
        operational_df,
        "No operational updates found.",
        search_key="operational_search",
    )


# ============================================================
# SPAM
# ============================================================

elif page_to_show == "Spam":

    render_page_header(
        "Spam",
        "Filtered spam and irrelevant emails.",
    )

    spam_df = df[
        df["Type"] == "Spam"
    ].copy()

    render_filtered_records(
        spam_df,
        "No spam records found.",
        search_key="spam_search",
    )


# ============================================================
# REPORTS
# ============================================================

elif page_to_show == "Reports":

    render_page_header(
        "Reports",
        "Operational reports and document review summaries.",
    )

    report_col1, report_col2, report_col3 = st.columns(3)

    report_col1.metric(
        "Total records",
        len(df),
    )

    report_col2.metric(
        "Under review",
        int(
            (df["Status"] == "Under Review").sum()
        ),
    )

    report_col3.metric(
        "Completed",
        int(
            (df["Status"] == "Done").sum()
        ),
    )

    st.write("")

    report_df = (
        df.groupby("Type")
        .size()
        .reset_index(name="Records")
        .sort_values(
            "Records",
            ascending=False,
        )
    )

    st.markdown(
        """
        <div class="panel">
            <div class="panel-title">
                Records by Category
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(
        report_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# SAFETY FALLBACK
# ============================================================

else:

    st.session_state["page_override"] = None
    st.session_state["case_view"] = False
    st.session_state["main_nav"] = "Home"
    st.session_state["insights_nav"] = None
    st.session_state["system_nav"] = None
    st.rerun()

st.markdown(
    """
    <style>
    .st-key-sidebar_account_footer .sidebar-avatar,
    .st-key-sidebar_account_footer .sidebar-avatar * {
        color: #0f2942 !important;
        -webkit-text-fill-color: #0f2942 !important;
        opacity: 1 !important;
        font-weight: 800 !important;
    }

    .st-key-sidebar_account_footer .sidebar-avatar {
        background: #eef5fb !important;
        border: 1px solid rgba(255,255,255,.35) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
    [data-testid="stMetric"] {
        color: var(--text-color) !important;
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] *,
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] *,
    [data-testid="stMetricDelta"],
    [data-testid="stMetricDelta"] * {
        color: var(--text-color) !important;
        -webkit-text-fill-color: var(--text-color) !important;
        opacity: 1 !important;
    }

    [data-testid="stMetricLabel"] {
        opacity: .72 !important;
    }

    [data-testid="stMetricValue"] {
        font-weight: 650 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)



# ============================================================
# SHIPGUARD FINAL STABLE KPI THEME
# Single source of truth for Home + Analytics KPI cards.
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       HOME: STREAMLIT METRICS
       ======================================================== */

    [data-testid="stMain"] [data-testid="stMetric"] {
        background:
            var(
                --st-secondary-background-color,
                var(--secondary-background-color)
            ) !important;

        border:
            1px solid rgba(127, 127, 127, 0.28) !important;

        border-radius: 18px !important;
        padding: 18px 20px !important;

        box-shadow:
            0 10px 26px rgba(0, 0, 0, 0.08) !important;

        transition:
            transform 160ms ease,
            border-color 160ms ease,
            box-shadow 160ms ease !important;
    }

    [data-testid="stMain"] [data-testid="stMetric"]:hover {
        transform: translateY(-2px);

        border-color:
            var(
                --st-primary-color,
                var(--primary-color)
            ) !important;

        box-shadow:
            0 14px 30px rgba(0, 0, 0, 0.11) !important;
    }


    /* Home metric labels */
    [data-testid="stMain"] [data-testid="stMetricLabel"],
    [data-testid="stMain"] [data-testid="stMetricLabel"] *,
    [data-testid="stMain"] [data-testid="stMetricLabel"] p {
        color:
            var(
                --st-text-color,
                var(--text-color)
            ) !important;

        -webkit-text-fill-color:
            var(
                --st-text-color,
                var(--text-color)
            ) !important;

        opacity: 0.82 !important;

        font-size: 0.95rem !important;
        font-weight: 700 !important;
    }


    /* Home metric numbers */
    [data-testid="stMain"] [data-testid="stMetricValue"],
    [data-testid="stMain"] [data-testid="stMetricValue"] *,
    [data-testid="stMain"] [data-testid="stMetricValue"] div,
    [data-testid="stMain"] [data-testid="stMetricValue"] p {
        color:
            var(
                --st-text-color,
                var(--text-color)
            ) !important;

        -webkit-text-fill-color:
            var(
                --st-text-color,
                var(--text-color)
            ) !important;

        opacity: 1 !important;

        font-size: 3rem !important;
        font-weight: 900 !important;

        line-height: 1 !important;
        letter-spacing: -0.035em !important;

        text-shadow: none !important;
    }


    /* ========================================================
       ANALYTICS: DISCREPANCY INTELLIGENCE
       ======================================================== */

    [data-testid="stMain"] .sg-intelligence-card {
        min-height: 132px;

        padding: 16px 16px 14px;

        border-radius: 16px;

        border:
            1px solid rgba(127, 127, 127, 0.28) !important;

        background:
            var(
                --st-secondary-background-color,
                var(--secondary-background-color)
            ) !important;

        box-shadow:
            0 10px 26px rgba(0, 0, 0, 0.08);

        box-sizing: border-box;

        transition:
            transform 160ms ease,
            border-color 160ms ease,
            box-shadow 160ms ease;
    }

    [data-testid="stMain"] .sg-intelligence-card:hover {
        transform: translateY(-2px);

        border-color:
            var(
                --st-primary-color,
                var(--primary-color)
            ) !important;

        box-shadow:
            0 14px 30px rgba(0, 0, 0, 0.11);
    }


    /* Analytics labels */
    [data-testid="stMain"] .sg-intelligence-label {
        color:
            var(
                --st-text-color,
                var(--text-color)
            ) !important;

        -webkit-text-fill-color:
            var(
                --st-text-color,
                var(--text-color)
            ) !important;

        opacity: 0.82 !important;

        font-size: 13px;
        font-weight: 700;

        margin-bottom: 8px;
    }


    /* Analytics numbers */
    [data-testid="stMain"] .sg-intelligence-value {
        color:
            var(
                --st-text-color,
                var(--text-color)
            ) !important;

        -webkit-text-fill-color:
            var(
                --st-text-color,
                var(--text-color)
            ) !important;

        opacity: 1 !important;

        font-size: 42px;
        line-height: 1.05;

        font-weight: 900;

        letter-spacing: -0.035em;

        white-space: normal;
        overflow-wrap: anywhere;
    }

    [data-testid="stMain"] .sg-intelligence-value.compact {
        font-size: 26px;
        letter-spacing: -0.02em;
    }


    /* Top Issue count badge */
    [data-testid="stMain"] .sg-intelligence-badge {
        display: inline-block;

        margin-top: 9px;

        padding: 4px 9px;

        border-radius: 999px;

        background: #166534 !important;

        color: #ecfdf5 !important;
        -webkit-text-fill-color: #ecfdf5 !important;

        font-size: 11px;
        font-weight: 800;
    }


    /* Motion accessibility */
    @media (prefers-reduced-motion: reduce) {
        [data-testid="stMain"] [data-testid="stMetric"],
        [data-testid="stMain"] .sg-intelligence-card {
            transition: none !important;
            transform: none !important;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)
