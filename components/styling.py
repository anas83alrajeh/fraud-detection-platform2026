"""
styling.py
------------------------------------------------------------------
Injects custom CSS into Streamlit to:
  1. Switch document direction (RTL for Arabic, LTR for EN/DE).
  2. Apply the correct font stack per language.
  3. Give the app a clean, professional "security console" look.

The CSS is rebuilt on every rerun based on the active language, so the
whole UI flips direction the moment the user changes the dropdown.
"""

import streamlit as st

# Brand palette — a calm, trustworthy security/fintech theme.
PRIMARY = "#0E7C66"        # teal-green
PRIMARY_DARK = "#0A5C4C"
ACCENT = "#E0A100"         # amber for warnings
DANGER = "#C0392B"         # red for high severity
BG_SOFT = "#F5F7F9"
TEXT = "#1F2937"


def inject_theme(direction: str, font_family: str) -> None:
    """Inject direction-aware CSS. Call once per rerun, early in app.py."""
    align = "right" if direction == "rtl" else "left"

    css = f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');

        /* ---- Global direction & font ---- */
        html, body, [class*="css"], .stApp, .main, [data-testid="stAppViewContainer"] {{
            direction: {direction};
            font-family: {font_family};
            text-align: {align};
        }}
        [data-testid="stSidebar"] {{
            direction: {direction};
            text-align: {align};
            background: linear-gradient(180deg, {PRIMARY_DARK} 0%, {PRIMARY} 100%);
        }}
        [data-testid="stSidebar"] * {{ color: #F8FAFB !important; }}

        /* Keep number/metric fields LTR even in Arabic for correct digit grouping */
        [data-testid="stMetricValue"], .ltr-num {{
            direction: ltr;
            unicode-bidi: isolate;
        }}

        /* ---- App header ---- */
        .app-header {{
            background: linear-gradient(135deg, {PRIMARY} 0%, {PRIMARY_DARK} 100%);
            color: #fff; padding: 1.4rem 1.8rem; border-radius: 16px;
            margin-bottom: 1.2rem; box-shadow: 0 8px 24px rgba(14,124,102,0.18);
        }}
        .app-header h1 {{ margin: 0; font-size: 1.6rem; font-weight: 700; color:#fff; }}
        .app-header p  {{ margin: .35rem 0 0; opacity: .9; font-size: .95rem; }}

        .offline-badge {{
            display: inline-block; background: rgba(255,255,255,.18);
            border: 1px solid rgba(255,255,255,.35); color:#fff;
            padding: .2rem .7rem; border-radius: 999px; font-size: .78rem;
            margin-top: .6rem;
        }}

        /* ---- KPI cards ---- */
        .kpi-card {{
            background:#fff; border:1px solid #E5E9EC; border-radius:14px;
            padding:1rem 1.2rem; box-shadow:0 2px 8px rgba(0,0,0,.04);
        }}
        .kpi-label {{ color:#6B7280; font-size:.85rem; }}
        .kpi-value {{ color:{PRIMARY_DARK}; font-size:1.5rem; font-weight:700;
                      direction:ltr; unicode-bidi:isolate; }}

        /* ---- Severity pills ---- */
        .pill {{ padding:.15rem .6rem; border-radius:999px; font-size:.78rem; font-weight:600; }}
        .pill-high   {{ background:#FDE8E6; color:{DANGER}; }}
        .pill-medium {{ background:#FCF3D9; color:{ACCENT}; }}
        .pill-low    {{ background:#E6F4EF; color:{PRIMARY_DARK}; }}

        /* ---- Buttons ---- */
        .stButton > button {{
            background:{PRIMARY}; color:#fff; border:none; border-radius:10px;
            padding:.5rem 1.2rem; font-weight:600;
        }}
        .stButton > button:hover {{ background:{PRIMARY_DARK}; color:#fff; }}

        /* Tidy default Streamlit chrome */
        #MainMenu, footer {{ visibility: hidden; }}
        .block-container {{ padding-top: 1.5rem; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def header(title: str, subtitle: str, badge: str) -> None:
    """Render the branded app header."""
    st.markdown(
        f"""
        <div class="app-header">
            <h1>🛡️ {title}</h1>
            <p>{subtitle}</p>
            <span class="offline-badge">🔒 {badge}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str) -> None:
    """Render a single KPI card."""
    st.markdown(
        f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def severity_pill(level: str, label: str) -> str:
    """Return HTML for a colored severity pill ('high'|'medium'|'low')."""
    return f'<span class="pill pill-{level}">{label}</span>'
