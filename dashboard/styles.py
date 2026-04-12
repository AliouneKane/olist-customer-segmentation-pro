"""Global Light Mode SaaS styles for the Olist Streamlit dashboard."""

from __future__ import annotations

import streamlit as st

# ── Color Palette (Olist Brand & SaaS Light Theme) ─────────────────────────
BG_MAIN = "#F8FAFC"        # Slate 50
BG_CARD = "#FFFFFF"        # White
TEXT_MAIN = "#0F172A"      # Slate 900
TEXT_MUTED = "#64748B"     # Slate 500
BORDER = "#E2E8F0"         # Slate 200

# Primary Olist accent (Vivid Blue)
ACCENT_BLUE = "#2563EB"    # Blue 600

# Secondary semantic colors
ACCENT_GREEN = "#10B981"   # Emerald 500
ACCENT_RED = "#EF4444"     # Red 500
ACCENT_YELLOW = "#F59E0B"  # Amber 500

# Categorical colors for the 6 segments (Light Theme adapted)
SEGMENT_COLORS = [
    "#2563EB",  # C0: Blue
    "#8B5CF6",  # C1: Violet
    "#F59E0B",  # C2: Amber
    "#10B981",  # C3: Emerald
    "#EF4444",  # C4: Red
    "#64748B",  # C5: Slate
]

# ── Generic CSS Injection ───────────────────────────────────────────────────
def inject_css() -> None:
    """Inject global CSS variables and generic Streamlit overrides (Light Mode)."""
    st.markdown(
        f"""
        <style>
        /* Typography: Inter / Roboto / System UI */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
            background-color: {BG_MAIN};
            color: {TEXT_MAIN};
        }}

        /* Full app background */
        .stApp {{
            background-color: {BG_MAIN};
        }}

        /* Hide anchor links (chain icon) */
        .css-15zrgzn {{ display: none; }}
        a.header-anchor {{ display: none !important; }}

        /* Main structural padding */
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1300px;
        }}

        /* Metric widget font colors */
        [data-testid="stMetricValue"] {{
            color: {TEXT_MAIN} !important;
            font-weight: 700 !important;
        }}
        [data-testid="stMetricLabel"] {{
            color: {TEXT_MUTED} !important;
        }}

        /* Sidebar Styling */
        [data-testid="stSidebar"] {{
            background-color: #FFFFFF !important;
            border-right: 1px solid {BORDER};
        }}
        [data-testid="stSidebar"] .stSelectbox label {{
            color: {TEXT_MUTED} !important;
        }}
        
        /* Tabs styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 2rem;
            background-color: transparent;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 3rem;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px 4px 0px 0px;
            gap: 1rem;
            color: {TEXT_MUTED};
            font-weight: 500;
        }}
        .stTabs [aria-selected="true"] {{
            color: {ACCENT_BLUE} !important;
            font-weight: 600;
            border-bottom: 3px solid {ACCENT_BLUE} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

# ── Plotly Theme (Light) ───────────────────────────────────────────────────
def apply_theme(fig, height: int = 350) -> None:
    """
    Applies the custom Light SaaS design to a given Plotly figure in-place.
    """
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_CARD,
        font=dict(family="Inter, sans-serif", color=TEXT_MUTED, size=11),
        title=dict(
            font=dict(color=TEXT_MAIN, size=14, family="Inter, sans-serif", weight="bold")
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=TEXT_MUTED),
        ),
        hoverlabel=dict(
            bgcolor="#1E293B",
            font_size=12,
            font_family="Inter, sans-serif",
            font_color="#FFFFFF"
        )
    )

    # Grid lines and axes
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="#F1F5F9",
        zeroline=False,
        showline=False,
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor="#F1F5F9",
        zeroline=False,
        showline=False,
    )
