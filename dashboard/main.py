"""Olist Customer Segmentation — Streamlit SaaS Dashboard.

Entry point for both local development and production (via `streamlit run`).
Multi-page routing is handled via st.navigation() (Streamlit >= 1.36).

Usage:
    streamlit run dashboard/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# ── Ensure project root is on sys.path ────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Page configuration (must be the FIRST Streamlit call) ─────────────────────
st.set_page_config(
    page_title="Olist · Customer Intelligence",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com",
        "About": (
            "**Olist Customer Segmentation Dashboard**\n\n"
            "KMeans k=6 · Silhouette 0.213 · 93 358 clients\n\n"
            "Segments: Premium Crédit · Économes Boleto · Périphériques · "
            "Mainstream · Champions · Déçus"
        ),
    },
)

# ── Navigation ────────────────────────────────────────────────────────────────
# NOTE: st.Page() paths must be relative to THIS file's directory (Streamlit >= 1.36)

pages = [
    st.Page("pages/1_overview.py", title="Vue d'Ensemble", icon="📊", default=True),
    st.Page("pages/2_segment_detail.py", title="Détail Segment", icon="🔍"),
    st.Page("pages/3_comparison.py", title="Comparaison Algos", icon="⚖️"),
]

pg = st.navigation(pages)
pg.run()
