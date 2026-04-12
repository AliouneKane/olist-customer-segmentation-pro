"""Olist Customer Segmentation — Streamlit Dashboard.

Entry point. Page routing via st.session_state + sidebar buttons.

Usage:
    streamlit run streamlit_app/main.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="Olist — Customer Segmentation",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

from streamlit_app.components.sidebar import (
    PAGE_COMPARISON,
    PAGE_GUIDE,
    PAGE_OVERVIEW,
    PAGE_SEGMENT,
    render_sidebar,
)
from streamlit_app.styles import inject_css

inject_css()
selected_page, cluster_id = render_sidebar()

if selected_page == PAGE_OVERVIEW:
    from streamlit_app.views.overview import render
    render()

elif selected_page == PAGE_SEGMENT:
    from streamlit_app.views.segment_detail import render
    render(cluster_id)

elif selected_page == PAGE_COMPARISON:
    from streamlit_app.views.comparison import render
    render()

elif selected_page == PAGE_GUIDE:
    from streamlit_app.views.guide import render
    render()
