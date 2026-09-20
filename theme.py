import streamlit as st


def inject_theme_css():
    st.markdown(
        """
<style>

/* ============================================================
   SHIPGUARD FINAL THEME
   ============================================================ */

/*
   Streamlit controls the active light/dark foreground.
   ShipGuard custom HTML inherits that computed foreground.
*/

/* Main content foreground */
[data-testid="stMain"] {
    color: inherit !important;
}

[data-testid="stMain"] .stMarkdown,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] {
    color: inherit !important;
}

/*
   Override old hardcoded text colours in app.py.
   Specific colour accents are restored below.
*/
[data-testid="stMain"] .stMarkdown *,
[data-testid="stMain"] [data-testid="stMarkdownContainer"] * {
    color: inherit !important;
    -webkit-text-fill-color: currentColor !important;
}

/* Main headings */
[data-testid="stMain"] h1,
[data-testid="stMain"] h2,
[data-testid="stMain"] h3,
[data-testid="stMain"] h4,
[data-testid="stMain"] h5,
[data-testid="stMain"] h6 {
    color: inherit !important;
    -webkit-text-fill-color: currentColor !important;
}

/* Top application bar */
.sg-topbar {
    background: rgba(127, 127, 127, 0.045) !important;
    border-color: rgba(127, 127, 127, 0.30) !important;
}

.sg-topbar-title,
.sg-topbar-path,
.sg-shortcut {
    color: inherit !important;
    -webkit-text-fill-color: currentColor !important;
}

.sg-shortcut {
    background: rgba(127, 127, 127, 0.08) !important;
    border-color: rgba(127, 127, 127, 0.30) !important;
}

/* Dashboard cards */
.command-chip,
.metric-card,
.status-card,
.sg-insight-card,
.sg-ai-callout,
.panel,
.doc-card,
.action-box,
.table-box,
.ai-summary,
.document-summary,
.review-panel,
.priority-wrapper,
.case-banner,
.info-box {
    background: rgba(127, 127, 127, 0.055) !important;
    border-color: rgba(127, 127, 127, 0.30) !important;
}

/* Dashboard text */
.command-chip-label,
.command-chip-value,
.sg-insight-title,
.sg-insight-value,
.sg-insight-copy,
.sg-ai-callout-title,
.sg-ai-callout-copy,
.metric-title,
.metric-label,
.metric-value,
.status-label,
.status-value,
.overview-title,
.sg-section-label,
.priority-title,
.panel-title,
.subject-text,
.ai-summary-title,
.ai-summary-value,
.ai-summary-label,
.small-muted,
.received-text,
.shipment-text {
    color: inherit !important;
    -webkit-text-fill-color: currentColor !important;
}

/* Secondary text */
.command-chip-label,
.metric-title,
.metric-label,
.status-label,
.sg-insight-copy,
.sg-ai-callout-copy,
.small-muted,
.received-text,
.shipment-text {
    opacity: 0.72 !important;
}

.sg-section-label,
.overview-title {
    opacity: 0.90 !important;
}

/* Search and form controls */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-baseweb="select"] > div {
    background: rgba(127, 127, 127, 0.10) !important;
    color: inherit !important;
    -webkit-text-fill-color: currentColor !important;
    border-color: rgba(127, 127, 127, 0.30) !important;
}

[data-testid="stTextInput"] input::placeholder,
[data-testid="stTextArea"] textarea::placeholder {
    color: inherit !important;
    -webkit-text-fill-color: currentColor !important;
    opacity: 0.55 !important;
}

/* Primary action button */
[data-testid="stMain"] button[kind="primary"],
[data-testid="stMain"] button[data-testid="stBaseButton-primary"],
[data-testid="stMain"] [data-testid="stBaseButton-primary"] {
    background: #2563eb !important;
    border-color: #2563eb !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 700 !important;
    box-shadow: 0 6px 18px rgba(37, 99, 235, 0.22) !important;
}

[data-testid="stMain"] button[kind="primary"] *,
[data-testid="stMain"] [data-testid="stBaseButton-primary"] * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

[data-testid="stMain"] button[kind="primary"]:hover,
[data-testid="stMain"] [data-testid="stBaseButton-primary"]:hover {
    background: #1d4ed8 !important;
    border-color: #1d4ed8 !important;
}

/* AI confidence badge */
[data-testid="stMain"] .sg-ai-badge,
[data-testid="stMain"] .sg-ai-badge * {
    background: #eaf5ff !important;
    color: #1769aa !important;
    -webkit-text-fill-color: #1769aa !important;
    border-color: #cfe3f4 !important;
    opacity: 1 !important;
}

/* Operational status */
[data-testid="stMain"] .sg-live-pill,
[data-testid="stMain"] .sg-live-pill * {
    color: #087f5b !important;
    -webkit-text-fill-color: #087f5b !important;
    opacity: 1 !important;
}

/* Workspace icons */
[data-testid="stMain"] .sg-kpi-icon,
[data-testid="stMain"] .sg-kpi-icon * {
    color: #1769aa !important;
    -webkit-text-fill-color: #1769aa !important;
    opacity: 1 !important;
}

/* Category accents */
[data-testid="stMain"] .metric-card.type-document .metric-value {
    color: #8b5cf6 !important;
    -webkit-text-fill-color: #8b5cf6 !important;
}

[data-testid="stMain"] .metric-card.type-si .metric-value {
    color: #f97316 !important;
    -webkit-text-fill-color: #f97316 !important;
}

[data-testid="stMain"] .metric-card.type-invoice .metric-value {
    color: #3b82f6 !important;
    -webkit-text-fill-color: #3b82f6 !important;
}

[data-testid="stMain"] .metric-card.type-operational .metric-value,
[data-testid="stMain"] .metric-card.type-general .metric-value,
[data-testid="stMain"] .metric-card.type-update .metric-value {
    color: #10b981 !important;
    -webkit-text-fill-color: #10b981 !important;
}

[data-testid="stMain"] .metric-card.type-spam .metric-value {
    color: #ef4444 !important;
    -webkit-text-fill-color: #ef4444 !important;
}

/* Progress bars */
.sg-progress {
    background: rgba(127, 127, 127, 0.18) !important;
}

.sg-progress > span {
    background: linear-gradient(
        90deg,
        #1c6aa5,
        #4a9bd0
    ) !important;
}

/* Native Streamlit header */
header[data-testid="stHeader"],
[data-testid="stHeader"] {
    background: transparent !important;
    color: inherit !important;
    border-bottom-color: rgba(127, 127, 127, 0.20) !important;
}

[data-testid="stToolbar"],
.stAppToolbar {
    background: transparent !important;
    color: inherit !important;
}

[data-testid="stToolbar"] button,
[data-testid="stToolbar"] span,
[data-testid="stToolbar"] a,
.stAppToolbar button,
.stAppToolbar span {
    color: inherit !important;
    -webkit-text-fill-color: currentColor !important;
}

[data-testid="stToolbar"] svg,
.stAppToolbar svg,
span[data-testid="stMainMenu"] svg {
    color: inherit !important;
    fill: currentColor !important;
}

/* Native metrics and captions */
[data-testid="stMetric"] *,
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] * {
    color: inherit !important;
    -webkit-text-fill-color: currentColor !important;
}

/* Keep sidebar styling controlled by app.py */
[data-testid="stSidebar"] {
    color: #f1f5f9 !important;
}

</style>
""",
        unsafe_allow_html=True,
    )
