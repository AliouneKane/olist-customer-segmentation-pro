"""Olist brand styles for the Streamlit dashboard.

Olist brand palette
-------------------
Primary blue  : #0041FF
Accent yellow : #F0FF00
Background    : #FFFFFF
Light surface : #F5F5F5
Dark text     : #212121
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

# Brand palette

OLIST_BLUE = "#0041FF"
OLIST_YELLOW = "#F0FF00"
BG_WHITE = "#FFFFFF"
BG_LIGHT = "#F5F5F5"
TEXT_DARK = "#212121"
TEXT_MUTED = "#6b7280"
BORDER_LIGHT = "#e5e7eb"
GRID_COLOR = "#e5e7eb"

SEGMENT_COLORS = [
    "#f59e0b",  # 0 — Acheteurs Budget  (amber)
    "#6b7280",  # 1 — Dormants Budget   (gray)
    "#0041FF",  # 2 — Acheteurs Premium (Olist blue)
    "#0ea5e9",  # 3 — Dormants Premium  (sky blue)
]

# CSS injected into every page

_CSS = """
/* ── Hide Streamlit chrome ─────────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* Style the sidebar open/close toggle buttons (Olist blue) */
[data-testid="collapsedControl"] button {
    background-color: #0041FF !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 0 6px 6px 0 !important;
}
[data-testid="collapsedControl"] svg { fill: #FFFFFF !important; }
[data-testid="stSidebarCollapseButton"] button {
    background-color: rgba(255,255,255,0.15) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
}
[data-testid="stSidebarCollapseButton"] svg { fill: #FFFFFF !important; }

/* ── Global font ──────────────────────────────────────────────── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif !important;
}

/* ── App background ───────────────────────────────────────────── */
.stApp { background-color: #FFFFFF; color: #212121; }
.main .block-container {
    padding-top: 0.5rem;
    padding-bottom: 2rem;
    background-color: #FFFFFF;
}

/* ── Sidebar ──────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #0041FF !important;
    border-right: none !important;
}
[data-testid="stSidebar"] > div {
    background-color: #0041FF !important;
}
/* Force ALL text inside sidebar to white */
[data-testid="stSidebar"],
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] small {
    color: #FFFFFF !important;
}
/* Muted text */
[data-testid="stSidebar"] [data-muted="true"],
[data-testid="stSidebar"] .sidebar-muted {
    color: rgba(255,255,255,0.55) !important;
}

/* ── Nav buttons in sidebar — secondary = inactive, primary = active ─ */
[data-testid="stSidebar"] button[kind="secondary"] {
    background-color: transparent !important;
    color: rgba(255,255,255,0.8) !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    text-align: left !important;
    border-radius: 7px !important;
    font-size: 0.88rem !important;
    font-weight: 400 !important;
    margin-bottom: 3px !important;
}
[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background-color: rgba(255,255,255,0.12) !important;
    color: #FFFFFF !important;
    border-color: rgba(255,255,255,0.35) !important;
}
[data-testid="stSidebar"] button[kind="primary"] {
    background-color: rgba(255,255,255,0.2) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255,255,255,0.4) !important;
    border-radius: 7px !important;
    font-size: 0.88rem !important;
    font-weight: 700 !important;
    margin-bottom: 3px !important;
}
[data-testid="stSidebar"] button[kind="primary"]:hover {
    background-color: rgba(255,255,255,0.28) !important;
}

/* ── Sidebar selectbox ────────────────────────────────────────── */
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div {
    background-color: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.25) !important;
    color: #FFFFFF !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] svg {
    fill: #FFFFFF !important;
}

/* ── Hide default Streamlit page nav ─────────────────────────── */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Metric cards ─────────────────────────────────────────────── */
[data-testid="metric-container"] {
    box-shadow: 0 1px 4px #d1d5db;
    padding: 14px;
    border-radius: 10px;
    background-color: #FFFFFF;
    border: 1px solid #f3f4f6;
}
[data-testid="stMetricLabel"] p { color: #6b7280 !important; font-size: 0.8rem !important; }
[data-testid="stMetricValue"] { color: #212121 !important; }

/* ── Plot containers ──────────────────────────────────────────── */
[data-testid="stPlotlyChart"] {
    background-color: #FFFFFF;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    padding: 0.25rem;
    box-shadow: 0 1px 3px #e5e7eb;
}

/* ── Expanders ────────────────────────────────────────────────── */
div[data-testid="stExpander"] div[role="button"] p {
    font-size: 0.9rem;
    color: #374151;
    font-weight: 600;
}
div[data-testid="stExpander"] { border: 1px solid #e5e7eb !important; border-radius: 8px !important; }

/* ── DataFrames ───────────────────────────────────────────────── */
[data-testid="stDataFrame"] { border: 1px solid #e5e7eb; border-radius: 8px; }

/* ── Progress bar ─────────────────────────────────────────────── */
.stProgress > div > div > div > div {
    background: linear-gradient(to right, #0041FF, #F0FF00);
}

/* ── Dividers ─────────────────────────────────────────────────── */
hr { border-color: #e5e7eb !important; }

/* ── Info / alert boxes ───────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
}

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: #F5F5F5; }
::-webkit-scrollbar-thumb { background: #0041FF55; border-radius: 3px; }
"""


def inject_css() -> None:
    """Injects the Olist brand CSS into the Streamlit page."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


# Plotly theme


def apply_olist_theme(fig: go.Figure, height: int | None = None) -> go.Figure:
    """Applies Olist brand theme to a Plotly figure.

    Args:
        fig: Plotly figure to modify in place.
        height: Optional height override in pixels.

    Returns:
        The same figure with theme applied.
    """
    layout_kw: dict = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=TEXT_DARK, size=12),
        title_font=dict(color=TEXT_DARK, size=13),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=BORDER_LIGHT,
            borderwidth=1,
            font=dict(color=TEXT_DARK),
        ),
        xaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=BORDER_LIGHT,
            tickfont=dict(color=TEXT_MUTED),
            title_font=dict(color=TEXT_MUTED),
            showgrid=True,
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=BORDER_LIGHT,
            tickfont=dict(color=TEXT_MUTED),
            title_font=dict(color=TEXT_MUTED),
            showgrid=True,
        ),
        margin=dict(t=50, b=40, l=40, r=20),
    )
    if height is not None:
        layout_kw["height"] = height

    fig.update_layout(**layout_kw)

    if fig.layout.polar:
        fig.update_layout(
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(
                    gridcolor=GRID_COLOR,
                    linecolor=BORDER_LIGHT,
                    tickfont=dict(color=TEXT_MUTED),
                ),
                angularaxis=dict(
                    gridcolor=GRID_COLOR,
                    linecolor=BORDER_LIGHT,
                    tickfont=dict(color=TEXT_DARK),
                ),
            )
        )

    return fig
