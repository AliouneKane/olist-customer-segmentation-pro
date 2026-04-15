"""Sidebar navigation using native st.button() — navigation state in session_state."""

from __future__ import annotations

import streamlit as st

PAGE_OVERVIEW = "Vue d'Ensemble"
PAGE_SEGMENT = "Détail Segment"
PAGE_COMPARISON = "Comparaison"
PAGE_GUIDE = "Guide du Dashboard"

_PAGES = [
    {"name": PAGE_OVERVIEW,  "icon": "📊"},
    {"name": PAGE_SEGMENT,   "icon": "🔍"},
    {"name": PAGE_COMPARISON,"icon": "⚖️"},
    {"name": PAGE_GUIDE,     "icon": "📖"},
]

_SEGMENT_LABELS = {
    0: "Acheteurs Budget",
    1: "Dormants Budget",
    2: "Acheteurs Premium",
    3: "Dormants Premium",
}

_SEGMENT_ICONS = {0: "🛒", 1: "⏳", 2: "⭐", 3: "🌙"}


def render_sidebar() -> tuple[str, int]:
    """Renders the sidebar and returns (selected_page, selected_cluster_id)."""
    # Init session state
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = PAGE_OVERVIEW
    if "selected_cluster" not in st.session_state:
        st.session_state["selected_cluster"] = 0

    with st.sidebar:
        # Logo
        st.markdown(
            """
            <div style="text-align:center; padding:1rem 0 1.25rem 0;">
                <div style="font-size:2.2rem; font-weight:900; color:#FFFFFF;
                            letter-spacing:-0.04em; line-height:1;">
                    olist
                </div>
                <div style="font-size:0.65rem; color:rgba(255,255,255,0.55);
                            letter-spacing:0.12em; text-transform:uppercase;
                            margin-top:5px;">
                    Customer Analytics
                </div>
                <div style="width:40px; height:3px;
                            background:#F0FF00; border-radius:2px;
                            margin:8px auto 0 auto;">
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Navigation label
        st.markdown(
            "<p style='font-size:0.65rem; color:rgba(255,255,255,0.45);"
            " text-transform:uppercase; letter-spacing:0.1em;"
            " font-weight:700; margin:0 0 6px 4px;'>Navigation</p>",
            unsafe_allow_html=True,
        )

        # Nav buttons — primary style = active page
        current = st.session_state["current_page"]
        for page in _PAGES:
            is_active = page["name"] == current
            # Style active vs inactive via button type
            label = f"{page['icon']}  {page['name']}"
            if st.button(
                label,
                key=f"nav__{page['name']}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["current_page"] = page["name"]
                st.rerun()

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.18); margin:14px 0;'>",
            unsafe_allow_html=True,
        )

        # Segment selector
        st.markdown(
            "<p style='font-size:0.65rem; color:rgba(255,255,255,0.45);"
            " text-transform:uppercase; letter-spacing:0.1em;"
            " font-weight:700; margin:0 0 6px 4px;'>Segment Actif</p>",
            unsafe_allow_html=True,
        )

        options = list(range(4))
        current_cluster = min(st.session_state["selected_cluster"], 3)
        cluster_id = st.selectbox(
            label="segment",
            options=options,
            index=current_cluster,
            format_func=lambda c: f"{_SEGMENT_ICONS[c]}  C{c} — {_SEGMENT_LABELS[c]}",
            label_visibility="collapsed",
            key="sidebar_cluster_selector",
        )
        st.session_state["selected_cluster"] = cluster_id

        # Footer
        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.18); margin:14px 0;'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='font-size:0.65rem; color:rgba(255,255,255,0.4);"
            " line-height:2; padding-bottom:0.5rem;'>"
            "📦 75 937 clients · k=4 · Sil. 0.449"
            "</div>",
            unsafe_allow_html=True,
        )

    return st.session_state["current_page"], cluster_id
