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


/* CONFIDENCE BADGE FIX */

[data-testid="stMain"] .badge.confidence-high {
    color: #087f5b !important;
    -webkit-text-fill-color: #087f5b !important;
    background: #e7f8f1 !important;
    border-color: #bdebdc !important;
    opacity: 1 !important;
}

[data-testid="stMain"] .badge.confidence-medium {
    color: #8a5a00 !important;
    -webkit-text-fill-color: #8a5a00 !important;
    background: #fff3c4 !important;
    border-color: #e8cf76 !important;
    opacity: 1 !important;
}

[data-testid="stMain"] .badge.confidence-low {
    color: #a33a3a !important;
    -webkit-text-fill-color: #a33a3a !important;
    background: #fff0f0 !important;
    border-color: #f2c7c7 !important;
    opacity: 1 !important;
}


/* ============================================================
   SHIPGUARD LED POLISH
   Visual-only enhancements. No application logic affected.
   ============================================================ */

/* Smooth dashboard interaction */
.metric-card,
.status-card,
.sg-insight-card,
.sg-ai-callout,
.panel,
.doc-card,
.command-chip {
    position: relative;
    transition:
        transform 180ms ease,
        box-shadow 180ms ease,
        border-color 180ms ease !important;
}

/* Subtle dashboard glow on hover */
.metric-card:hover,
.status-card:hover,
.sg-insight-card:hover,
.sg-ai-callout:hover,
.panel:hover,
.doc-card:hover,
.command-chip:hover {
    transform: translateY(-2px);
    border-color: rgba(59, 130, 246, 0.45) !important;
    box-shadow:
        0 10px 28px rgba(15, 23, 42, 0.10),
        0 0 0 1px rgba(59, 130, 246, 0.07),
        0 0 22px rgba(59, 130, 246, 0.10) !important;
}

/* Live system LED */
.sg-live-pill {
    display: inline-flex !important;
    align-items: center !important;
    gap: 7px !important;
}

.sg-live-pill::before {
    content: "";
    display: inline-block;
    width: 7px;
    height: 7px;
    flex: 0 0 7px;
    border-radius: 50%;
    background: #10b981;
    box-shadow:
        0 0 0 3px rgba(16, 185, 129, 0.12),
        0 0 10px rgba(16, 185, 129, 0.80);
    animation: sg-led-pulse 2.2s ease-in-out infinite;
}

@keyframes sg-led-pulse {
    0%, 100% {
        opacity: 0.68;
        transform: scale(0.92);
        box-shadow:
            0 0 0 3px rgba(16, 185, 129, 0.10),
            0 0 8px rgba(16, 185, 129, 0.55);
    }

    50% {
        opacity: 1;
        transform: scale(1.08);
        box-shadow:
            0 0 0 4px rgba(16, 185, 129, 0.14),
            0 0 14px rgba(16, 185, 129, 0.95);
    }
}

/* Category LED accents */
.metric-card.type-document:hover {
    border-color: rgba(139, 92, 246, 0.55) !important;
    box-shadow:
        0 10px 28px rgba(15, 23, 42, 0.10),
        0 0 22px rgba(139, 92, 246, 0.16) !important;
}

.metric-card.type-si:hover {
    border-color: rgba(249, 115, 22, 0.55) !important;
    box-shadow:
        0 10px 28px rgba(15, 23, 42, 0.10),
        0 0 22px rgba(249, 115, 22, 0.15) !important;
}

.metric-card.type-invoice:hover {
    border-color: rgba(59, 130, 246, 0.55) !important;
    box-shadow:
        0 10px 28px rgba(15, 23, 42, 0.10),
        0 0 22px rgba(59, 130, 246, 0.15) !important;
}

.metric-card.type-operational:hover,
.metric-card.type-general:hover,
.metric-card.type-update:hover {
    border-color: rgba(16, 185, 129, 0.55) !important;
    box-shadow:
        0 10px 28px rgba(15, 23, 42, 0.10),
        0 0 22px rgba(16, 185, 129, 0.15) !important;
}

.metric-card.type-spam:hover {
    border-color: rgba(239, 68, 68, 0.55) !important;
    box-shadow:
        0 10px 28px rgba(15, 23, 42, 0.10),
        0 0 22px rgba(239, 68, 68, 0.15) !important;
}

/* Primary CTA LED */
[data-testid="stMain"] button[kind="primary"],
[data-testid="stMain"] [data-testid="stBaseButton-primary"] {
    transition:
        transform 160ms ease,
        box-shadow 160ms ease,
        background 160ms ease !important;

    box-shadow:
        0 6px 18px rgba(37, 99, 235, 0.24),
        0 0 18px rgba(37, 99, 235, 0.12) !important;
}

[data-testid="stMain"] button[kind="primary"]:hover,
[data-testid="stMain"] [data-testid="stBaseButton-primary"]:hover {
    transform: translateY(-1px);
    box-shadow:
        0 8px 24px rgba(37, 99, 235, 0.30),
        0 0 24px rgba(37, 99, 235, 0.20) !important;
}

/* Progress LED */
.sg-progress > span {
    box-shadow:
        0 0 10px rgba(74, 155, 208, 0.35),
        0 0 18px rgba(74, 155, 208, 0.12);
}

/* Search/input focus glow */
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: rgba(59, 130, 246, 0.60) !important;
    box-shadow:
        0 0 0 2px rgba(59, 130, 246, 0.08),
        0 0 16px rgba(59, 130, 246, 0.08) !important;
}

/* Respect accessibility settings */
@media (prefers-reduced-motion: reduce) {
    .sg-live-pill::before {
        animation: none !important;
    }

    .metric-card,
    .status-card,
    .sg-insight-card,
    .sg-ai-callout,
    .panel,
    .doc-card,
    .command-chip,
    [data-testid="stMain"] button {
        transition: none !important;
    }

    .metric-card:hover,
    .status-card:hover,
    .sg-insight-card:hover,
    .sg-ai-callout:hover,
    .panel:hover,
    .doc-card:hover,
    .command-chip:hover {
        transform: none !important;
    }
}


/* ============================================================
   SHIPGUARD SIDEBAR POLISH
   Sidebar-only visual improvements
   ============================================================ */

/* Sidebar shell */
section[data-testid="stSidebar"],
[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at top left, rgba(37, 99, 235, 0.18), transparent 28%),
        linear-gradient(180deg, #0b2b4a 0%, #08213a 45%, #06182d 100%) !important;
    border-right: 1px solid rgba(148, 163, 184, 0.14) !important;
}

/* Sidebar content area */
section[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] > div {
    background: transparent !important;
}

/* General sidebar text */
[data-testid="stSidebar"] * {
    color: #e8f1fb !important;
}

/* Section labels like WORKSPACE / INSIGHTS / SYSTEM */
[data-testid="stSidebar"] .stMarkdown p strong,
[data-testid="stSidebar"] .stMarkdown strong {
    letter-spacing: 0.12em;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    color: rgba(226, 232, 240, 0.80) !important;
}

/* Sidebar dividers */
[data-testid="stSidebar"] hr {
    border: none !important;
    border-top: 1px solid rgba(148, 163, 184, 0.14) !important;
    margin: 0.8rem 0 1rem 0 !important;
}

/* Buttons / clickable controls in sidebar */
[data-testid="stSidebar"] button,
[data-testid="stSidebar"] [role="button"],
[data-testid="stSidebar"] a {
    border-radius: 12px !important;
    transition:
        background 160ms ease,
        box-shadow 160ms ease,
        transform 160ms ease !important;
}

/* Hover state */
[data-testid="stSidebar"] button:hover,
[data-testid="stSidebar"] [role="button"]:hover,
[data-testid="stSidebar"] a:hover {
    background: rgba(255, 255, 255, 0.06) !important;
    box-shadow:
        0 0 0 1px rgba(96, 165, 250, 0.10),
        0 0 16px rgba(59, 130, 246, 0.10) !important;
    transform: translateX(2px);
}

/* Active/current page style */
[data-testid="stSidebar"] a[aria-current="page"],
[data-testid="stSidebar"] button[kind="secondary"][aria-current="page"],
[data-testid="stSidebar"] [aria-current="page"] {
    background: linear-gradient(90deg, rgba(59,130,246,0.20), rgba(59,130,246,0.08)) !important;
    border: 1px solid rgba(96, 165, 250, 0.28) !important;
    box-shadow:
        inset 0 0 0 1px rgba(125, 211, 252, 0.10),
        0 0 18px rgba(59, 130, 246, 0.12) !important;
}

/* Sidebar inputs / select / search if any */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(148, 163, 184, 0.16) !important;
    color: #f8fbff !important;
    border-radius: 12px !important;
}

[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] textarea::placeholder {
    color: rgba(226, 232, 240, 0.55) !important;
}

/* Bottom card / profile-like container feel */
[data-testid="stSidebar"] .stContainer,
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(button),
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(a) {
    border-radius: 14px;
}

/* Small polish for avatar-like circles if present */
[data-testid="stSidebar"] [style*="border-radius: 50%"],
[data-testid="stSidebar"] .avatar,
[data-testid="stSidebar"] .profile-avatar {
    box-shadow:
        0 0 0 2px rgba(255,255,255,0.08),
        0 0 14px rgba(59,130,246,0.16) !important;
}

/* Keep animations accessible */
@media (prefers-reduced-motion: reduce) {
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] [role="button"],
    [data-testid="stSidebar"] a {
        transition: none !important;
        transform: none !important;
    }
}


/* ============================================================
   SHIPGUARD SIDEBAR NAV V2
   Precise styling for Streamlit radio navigation
   ============================================================ */

/* Remove unnecessary radio widget spacing */
[data-testid="stSidebar"] [data-testid="stRadio"] {
    margin-top: -2px !important;
    margin-bottom: 2px !important;
}

[data-testid="stSidebar"] [data-testid="stRadio"] > div {
    gap: 3px !important;
}

/* Every navigation row */
[data-testid="stSidebar"] [data-baseweb="radio"] {
    width: 100% !important;
    min-height: 34px !important;
    padding: 6px 9px !important;
    margin: 1px 0 !important;

    border: 1px solid transparent !important;
    border-radius: 10px !important;

    background: transparent !important;

    transition:
        background 160ms ease,
        border-color 160ms ease,
        box-shadow 160ms ease,
        transform 160ms ease !important;
}

/* Navigation text */
[data-testid="stSidebar"] [data-baseweb="radio"] p,
[data-testid="stSidebar"] [data-baseweb="radio"] span {
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #dce9f5 !important;
    -webkit-text-fill-color: #dce9f5 !important;
}

/* Hover state */
[data-testid="stSidebar"] [data-baseweb="radio"]:hover {
    background: rgba(96, 165, 250, 0.075) !important;
    border-color: rgba(96, 165, 250, 0.12) !important;

    transform: translateX(3px);

    box-shadow:
        inset 0 0 0 1px rgba(96,165,250,.025),
        0 4px 14px rgba(0,0,0,.08),
        0 0 16px rgba(59,130,246,.055) !important;
}

/* ACTIVE NAV ITEM */
[data-testid="stSidebar"] [data-baseweb="radio"]:has(input:checked) {
    background:
        linear-gradient(
            90deg,
            rgba(37, 99, 235, 0.24),
            rgba(59, 130, 246, 0.09)
        ) !important;

    border-color: rgba(96, 165, 250, 0.28) !important;

    box-shadow:
        inset 3px 0 0 #60a5fa,
        inset 0 0 0 1px rgba(125,211,252,.035),
        0 4px 16px rgba(0,0,0,.10),
        0 0 18px rgba(59,130,246,.10) !important;
}

/* Active navigation text */
[data-testid="stSidebar"]
[data-baseweb="radio"]:has(input:checked) p,
[data-testid="stSidebar"]
[data-baseweb="radio"]:has(input:checked) span {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 700 !important;
}

/* Radio LED container */
[data-testid="stSidebar"]
[data-baseweb="radio"] > div:first-child {
    flex-shrink: 0 !important;
}

/* Selected radio LED */
[data-testid="stSidebar"]
[data-baseweb="radio"]:has(input:checked)
> div:first-child > div {
    border-color: #60a5fa !important;
    background: #3b82f6 !important;

    box-shadow:
        0 0 0 3px rgba(59,130,246,.13),
        0 0 10px rgba(96,165,250,.42) !important;
}

/* Unselected radio indicator */
[data-testid="stSidebar"]
[data-baseweb="radio"]:not(:has(input:checked))
> div:first-child > div {
    border-color: rgba(148,163,184,.42) !important;
    background: rgba(15,23,42,.40) !important;
}

/* Sidebar section headings */
[data-testid="stSidebar"] .sidebar-section {
    padding: 5px 9px 7px !important;
    margin-top: 1px !important;

    font-size: 10px !important;
    font-weight: 800 !important;
    letter-spacing: 1.05px !important;

    color: rgba(226, 238, 249, .82) !important;
    -webkit-text-fill-color: rgba(226, 238, 249, .82) !important;
}

/* Cleaner separators */
[data-testid="stSidebar"] .sidebar-divider {
    margin: 10px 3px 11px !important;

    background:
        linear-gradient(
            90deg,
            transparent,
            rgba(148,163,184,.18) 10%,
            rgba(148,163,184,.18) 90%,
            transparent
        ) !important;
}

/* Brand logo gets a subtle AI glow */
[data-testid="stSidebar"] .shipguard-logo {
    border: 1px solid rgba(125,211,252,.16) !important;

    box-shadow:
        inset 0 0 0 1px rgba(255,255,255,.04),
        0 0 18px rgba(59,130,246,.10) !important;
}

/* Account footer refinement */
.st-key-sidebar_account_footer {
    border-color: rgba(125, 211, 252, .14) !important;

    background:
        radial-gradient(
            circle at top left,
            rgba(59,130,246,.10),
            transparent 40%
        ),
        linear-gradient(
            180deg,
            rgba(13,42,69,.98),
            rgba(8,29,51,.99)
        ) !important;

    box-shadow:
        0 -8px 30px rgba(0,0,0,.20),
        0 0 22px rgba(59,130,246,.045) !important;
}

/* Account avatar */
.st-key-sidebar_account_footer .sidebar-avatar {
    box-shadow:
        0 0 0 3px rgba(255,255,255,.045),
        0 0 14px rgba(96,165,250,.15) !important;
}

/* Account button */
.st-key-sidebar_account_footer button {
    min-height: 38px !important;
    border-radius: 10px !important;

    transition:
        transform 150ms ease,
        box-shadow 150ms ease,
        border-color 150ms ease !important;
}

.st-key-sidebar_account_footer button:hover {
    transform: translateY(-1px) !important;

    border-color: rgba(96,165,250,.35) !important;

    box-shadow:
        0 5px 16px rgba(0,0,0,.12),
        0 0 13px rgba(59,130,246,.08) !important;
}

/* Avoid exaggerated movement for reduced motion users */
@media (prefers-reduced-motion: reduce) {
    [data-testid="stSidebar"] [data-baseweb="radio"],
    .st-key-sidebar_account_footer button {
        transition: none !important;
        transform: none !important;
    }
}


/* ============================================================
   SHIPGUARD NAV PILL FIX
   ============================================================ */

/* Navigation rows */
.st-key-main_nav label,
.st-key-insights_nav label,
.st-key-system_nav label {
    width: 100% !important;
    min-height: 36px !important;
    padding: 7px 10px !important;
    margin: 2px 0 !important;

    border-radius: 10px !important;
    border: 1px solid transparent !important;
    background: transparent !important;

    transition:
        background 160ms ease,
        border-color 160ms ease,
        box-shadow 160ms ease,
        transform 160ms ease !important;
}

/* Hover */
.st-key-main_nav label:hover,
.st-key-insights_nav label:hover,
.st-key-system_nav label:hover {
    background: rgba(96, 165, 250, 0.08) !important;
    border-color: rgba(96, 165, 250, 0.13) !important;
    transform: translateX(3px);

    box-shadow:
        0 0 14px rgba(59, 130, 246, 0.07) !important;
}

/* Selected navigation item */
.st-key-main_nav label:has(input:checked),
.st-key-insights_nav label:has(input:checked),
.st-key-system_nav label:has(input:checked) {
    background:
        linear-gradient(
            90deg,
            rgba(37, 99, 235, 0.28),
            rgba(59, 130, 246, 0.08)
        ) !important;

    border-color: rgba(96, 165, 250, 0.28) !important;

    box-shadow:
        inset 3px 0 0 #60a5fa,
        0 4px 14px rgba(0, 0, 0, 0.10),
        0 0 18px rgba(59, 130, 246, 0.10) !important;
}

/* Selected text */
.st-key-main_nav label:has(input:checked) p,
.st-key-insights_nav label:has(input:checked) p,
.st-key-system_nav label:has(input:checked) p {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 700 !important;
}

/* Remove ugly red Streamlit selected indicator */
.st-key-main_nav input:checked + div,
.st-key-insights_nav input:checked + div,
.st-key-system_nav input:checked + div {
    background: #3b82f6 !important;
    border-color: #60a5fa !important;
    box-shadow:
        0 0 0 3px rgba(59,130,246,.13),
        0 0 10px rgba(96,165,250,.45) !important;
}

/* Radio circle base */
.st-key-main_nav label > div:first-child,
.st-key-insights_nav label > div:first-child,
.st-key-system_nav label > div:first-child {
    flex-shrink: 0 !important;
}


</style>
""",
        unsafe_allow_html=True,
    )
