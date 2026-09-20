import streamlit as st
import pandas as pd
from datetime import datetime
import html
import re
from modules.inbox import load_inbox
from modules.classifier import classify_email

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ShipGuard AI",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------------
# BUGFIX: st.markdown(..., unsafe_allow_html=True) 里的 HTML
# 字符串是按 Python 源码缩进写的（比如缩进 12/16 个空格）。
# Markdown 规范里，一段文字整体缩进 4 个空格以上会被当成
# "代码块"处理，于是浏览器只会把这些 <div>/<span> 标签当成
# 纯文本打印出来，而不是渲染成卡片——这正是很多页面点进去
# 显示"乱码"（原始 HTML 标签）的根本原因。
# 这里给 st.markdown 打一个全局补丁：只要传了
# unsafe_allow_html=True，就先把每一行的前导空白去掉，再交给
# 原始的 st.markdown 渲染。不影响其他不带 unsafe_allow_html
# 的普通文字调用。
# ------------------------------------------------------------
_original_markdown = st.markdown


def _dedented_markdown(body="", *args, **kwargs):
    if kwargs.get("unsafe_allow_html") and isinstance(body, str):
        body = "\n".join(line.lstrip() for line in body.split("\n"))
    return _original_markdown(body, *args, **kwargs)


st.markdown = _dedented_markdown


# ============================================================
# USER CONFIG
# ============================================================

USER_NAME = "user"
USER_ROLE = "Operations Executive"
USER_INITIALS = "SY"


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
    background: #f5f8fc;
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
    color: #12253f;
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
    background: #ffffff;
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
    background: #ffffff;
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
    background: #ffffff;
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
    background: #ffffff;
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
    background: #ffffff;
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
    background: #ffffff;
    border: 1px solid #e3ebf5;
    border-radius: 16px;
    padding: 35px;
    text-align: center;
    box-shadow: 0 8px 30px rgba(23,54,90,.08);
}

</style>
""",
    unsafe_allow_html=True,
)


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
        "Field": "Vessel",
        "Shipping Instruction (SI)": "MV Ocean Star",
        "Draft Bill of Lading (BL)": "MV Ocean Star",
    },
    {
        "Shipment": "SI-2026-0821",
        "Field": "Container",
        "Shipping Instruction (SI)": "TCNU1234567",
        "Draft Bill of Lading (BL)": "TCNU1234567",
    },
    {
        "Shipment": "SI-2026-0821",
        "Field": "Quantity",
        "Shipping Instruction (SI)": "500 CTNS",
        "Draft Bill of Lading (BL)": "500 CTNS",
    },
    {
        "Shipment": "SI-2026-0821",
        "Field": "Gross Weight",
        "Shipping Instruction (SI)": "12,500 KG",
        "Draft Bill of Lading (BL)": "12,050 KG",
    },
]


def load_backend_records():
    category_map = {
        "document_comparison": "Document Check",
        "new_si_request": "SI Request",
        "invoice_query": "Invoice Question",
        "general": "Operational Update",
        "spam": "Spam",
    }

    inbox = load_inbox()
    rows = []

    for email in inbox:
        classification = classify_email(email)

        category = classification["category"]

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
        })

    return pd.DataFrame(rows)


def load_backend_comparison():
    return pd.DataFrame(DEFAULT_COMPARISON)


# ============================================================
# SESSION STATE
# ============================================================

if "df" not in st.session_state:
    st.session_state["df"] = load_backend_records()

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

if "logged_out" not in st.session_state:
    st.session_state["logged_out"] = False

if "search_query" not in st.session_state:
    st.session_state["search_query"] = ""

if "_pending_nav" not in st.session_state:
    st.session_state["_pending_nav"] = None


# ------------------------------------------------------------
# BUGFIX: main_nav / insights_nav / system_nav 这三个键是绑定
# 在侧边栏 st.radio 组件上的。Streamlit 规定：一个组件被创建
# 之后，本次运行内不能再直接对同名的 session_state 赋值，否则
# 会抛出 StreamlitAPIException（页面上就是一片报错文字，也就
# 是你看到的"乱码"）。但原代码里有好几处按钮（例如"返回
# Home"、Settings 里的"Back to Home"）恰好是在侧边栏渲染完
# 之后才执行的，直接写 st.session_state["main_nav"] = "Home"
# 就会踩中这个限制。
#
# 解决办法：这些按钮不再直接改 main_nav/insights_nav/system_nav，
# 而是把想要的值放进 _pending_nav 里排队，然后 st.rerun()。下一次
# 运行一开始（此处，早于侧边栏 radio 被创建之前）再把排队的值
# 应用到真正的 session_state 上，这样就不会违反前面的限制了。
# ------------------------------------------------------------
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
    insights_nav=None,
    system_nav=None,
    page_override="__unset__",
    case_view=None,
    selected_record_id="__unset__",
):
    """排队一次导航跳转，并立即 rerun。

    main_nav / insights_nav / system_nav 是侧边栏 radio 组件的
    session_state 键，只能在对应组件被创建之前赋值。这里统一走
    _pending_nav 队列，在下一次脚本运行最开始（组件创建之前）
    再真正写入，从而避免 StreamlitAPIException。
    """

    pending = {}

    if main_nav is not None:
        pending["main_nav"] = main_nav

    if insights_nav is not None:
        pending["insights_nav"] = insights_nav

    if system_nav is not None:
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
    cls = "badge-green" if text == "Done" else "badge-orange"

    return f"""
    <span class="badge {cls}">
        {safe_text(text)}
    </span>
    """


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

    if comparison_df.empty:

        return pd.DataFrame(
            columns=[
                "Field",
                "Shipping Instruction (SI)",
                "Draft Bill of Lading (BL)",
            ]
        )

    shipment = record.get("Shipment")

    if "Shipment" in comparison_df.columns:

        result = comparison_df[
            comparison_df["Shipment"].astype(str)
            == str(shipment)
        ].copy()

    else:

        result = comparison_df.copy()

    return result


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

    st.markdown(f"# {safe_text(title)}")

    st.markdown(
        '<div class="page-accent"></div>',
        unsafe_allow_html=True,
    )

    if caption:
        st.caption(caption)


def render_filtered_records(
    record_df,
    empty_message="No records found.",
    search_key=None,
    show_search=True,
):

    working_df = record_df.copy()

    if show_search:

        query = st.text_input(
            "Search",
            placeholder=(
                "Search subject, shipment, type or priority..."
            ),
            label_visibility="collapsed",
            key=search_key,
        )

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

    st.markdown(
        f"""
        <div class="small-muted" style="margin-bottom:10px;">
            {len(working_df)} record(s)
        </div>
        """,
        unsafe_allow_html=True,
    )

    for row_index, row in working_df.iterrows():

        st.markdown(
            '<div class="doc-card">',
            unsafe_allow_html=True,
        )

        c1, c2, c3, c4 = st.columns(
            [1.15, 3.1, 1.15, .8]
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

    under_review = int(
        (df["Status"] == "Under Review").sum()
    )

    done = int(
        (df["Status"] == "Done").sum()
    )

    status_c1, status_c2 = st.columns(2)

    with status_c1:

        st.markdown(
            f"""
            <div class="status-card">
                <div class="status-label">
                    Under review
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
                    Done
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

    st.markdown(
        '<div class="sidebar-user-box">',
        unsafe_allow_html=True,
    )

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

    st.markdown(
        "</div>",
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

    left_space, filter_col, sort_col = st.columns(
        [3.0, 1.1, 1.1]
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

    if shipment_filter != "All Shipments":

        filtered_df = filtered_df[
            filtered_df["Shipment Type"]
            == shipment_filter
        ]

    filtered_df = sort_records(
        filtered_df,
        priority_sort,
    )

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
                1.05fr 2.9fr 1.25fr .9fr .95fr .8fr;
                gap:12px;
            ">
                <div>Type</div>
                <div>Subject</div>
                <div>Shipment</div>
                <div>Priority</div>
                <div>Received</div>
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

        for index, row in filtered_df.iterrows():

            row_cols = st.columns(
                [1.05, 2.9, 1.25, .9, .95, .8]
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

                if st.button(
                    "View",
                    key=f"home_view_{row['ID']}_{index}",
                    use_container_width=False
                    ,
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

    total_emails = len(df)

    action_required = int(
        (df["Status"] == "Under Review").sum()
    )

    open_document_checks = int(
        (
            (df["Type"] == "Document Check")
            &
            (df["Status"] == "Under Review")
        ).sum()
    )

    completed_records = int(
        (df["Status"] == "Done").sum()
    )

    a, b, c, d = st.columns(4)

    a.metric(
        "Total records",
        total_emails,
    )

    b.metric(
        "Action required",
        action_required,
    )

    c.metric(
        "Open document checks",
        open_document_checks,
    )

    d.metric(
        "Completed",
        completed_records,
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

        <h2 style="margin:4px 0 8px;">
            {safe_text(record["Subject"])}
        </h2>

        {priority_badge(record["Priority"])}

        {status_badge(record.get("Status", "Under Review"))}

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

        with side:

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

        go_to(
            main_nav="Home",
            insights_nav=None,
            system_nav=None,
            page_override=None,
            case_view=False,
            selected_record_id=None,
        )

    st.write("")

    st.markdown(
        '<div class="panel">',
        unsafe_allow_html=True,
    )

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
