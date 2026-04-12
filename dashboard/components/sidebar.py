"""Premium SaaS sidebar for the Olist Segmentation Streamlit dashboard.

Renders the logo, navigation links, and a persistent cluster selector
stored in st.session_state["selected_cluster"].
"""

from __future__ import annotations

import streamlit as st

from dashboard.styles import SEGMENT_COLORS

_SEGMENT_LABELS = {
    0: "Premium Crédit",
    1: "Économes Boleto",
    2: "Périphériques Contraints",
    3: "Mainstream",
    4: "Champions",
    5: "Déçus / Insatisfaits",
}

_SEGMENT_ICONS = {
    0: "💳",
    1: "🐷",
    2: "📍",
    3: "👥",
    4: "🏆",
    5: "😞",
}

_SEGMENT_DESCRIPTIONS = {
    0: "Haut panier · 8 versements",
    1: "Boleto · Prix bas",
    2: "Fret élevé · Rural",
    3: "Cœur de cible · 41%",
    4: "Fidèles · CLV max",
    5: "Churn risk · Note 1/5",
}


def render_sidebar() -> int:
    """Renders the premium sidebar and returns the currently selected cluster id.

    Writes ``selected_cluster`` into ``st.session_state`` so all pages
    stay in sync when the user changes the selector.

    Returns:
        Integer cluster id (0–5).
    """
    with st.sidebar:
        # ── Brand logo / title ─────────────────────────────────────────────
        st.markdown(
            """
            <div style="padding: 1.25rem 0 1rem 0;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                    <div style="width:36px;height:36px;border-radius:10px;
                                background-color:#2563EB;
                                display:flex;align-items:center;justify-content:center;
                                font-size:1.1rem;box-shadow:0 4px 10px rgba(37,99,235,0.2);">
                        🛍️
                    </div>
                    <div>
                        <div style="font-size:1rem; font-weight:800; color:#0F172A;
                                    letter-spacing:-0.02em; line-height:1.2;">
                            Olist Segments
                        </div>
                        <div style="font-size:0.68rem; color:#64748B; font-weight:500;">
                            Customer Intelligence
                        </div>
                    </div>
                </div>
                <div style="height:1px;background-color:#E2E8F0;
                            margin-top:8px;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Segment selector label ─────────────────────────────────────────
        st.markdown(
            "<p style='font-size:0.68rem;color:#64748B;text-transform:uppercase;"
            "letter-spacing:0.1em;font-weight:700;margin-bottom:6px;'>Segment actif</p>",
            unsafe_allow_html=True,
        )

        options = list(range(6))
        format_func = (
            lambda cid: f"{_SEGMENT_ICONS[cid]}  Cluster {cid} — {_SEGMENT_LABELS[cid]}"  # noqa: E731
        )

        default = st.session_state.get("selected_cluster", 0)
        if default not in options:
            default = 0

        cluster_id = st.selectbox(
            label="Segment actif",
            options=options,
            index=options.index(default),
            format_func=format_func,
            label_visibility="collapsed",
            key="sidebar_cluster_selector",
        )
        st.session_state["selected_cluster"] = cluster_id

        # ── Active segment badge ───────────────────────────────────────────
        color = SEGMENT_COLORS[cluster_id % len(SEGMENT_COLORS)]
        name = _SEGMENT_LABELS[cluster_id]
        icon = _SEGMENT_ICONS[cluster_id]
        desc = _SEGMENT_DESCRIPTIONS[cluster_id]

        st.markdown(
            f"""
            <div style="
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-left: 3px solid {color};
                border-radius: 8px;
                padding: 12px 14px;
                margin-top: 10px;
            ">
                <div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;
                            letter-spacing:0.08em;font-weight:700;margin-bottom:5px;">
                    Segment sélectionné
                </div>
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
                    <span style="font-size:1.1rem;">{icon}</span>
                    <span style="font-size:0.92rem;font-weight:700;color:{color};">{name}</span>
                </div>
                <div style="font-size:0.72rem;color:#475569;">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Segments quick reference ───────────────────────────────────────
        st.markdown("<div style='margin-top:1.25rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:0.68rem;color:#64748B;text-transform:uppercase;"
            "letter-spacing:0.1em;font-weight:700;margin-bottom:8px;'>Tous les segments</p>",
            unsafe_allow_html=True,
        )

        for cid in range(6):
            c = SEGMENT_COLORS[cid % len(SEGMENT_COLORS)]
            is_active = cid == cluster_id
            bg = "#EFF6FF" if is_active else "transparent"
            border = f"1px solid #BFDBFE" if is_active else "1px solid transparent"
            weight = "700" if is_active else "500"
            text_color = c if is_active else "#64748B"
            st.markdown(
                f"""<div style="background-color:{bg};border:{border};border-radius:8px;
                                padding:6px 8px;margin-bottom:3px;display:flex;
                                align-items:center;gap:8px;">
                      <span style="font-size:0.85rem;">{_SEGMENT_ICONS[cid]}</span>
                      <div>
                        <div style="font-size:0.75rem;font-weight:{weight};color:{text_color};
                                    line-height:1.2;">C{cid} — {_SEGMENT_LABELS[cid]}</div>
                      </div>
                    </div>""",
                unsafe_allow_html=True,
            )

        # ── Footer ────────────────────────────────────────────────────────
        st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
        st.markdown(
            """<div style="border-top:1px solid #E2E8F0;padding-top:0.75rem;">
                 <div style="font-size:0.68rem;color:#94A3B8;line-height:1.6;">
                     📌 93 358 clients · KMeans k=6<br>
                     📈 Silhouette: 0.213<br>
                     🌎 Marketplace Olist / Brésil
                 </div>
               </div>""",
            unsafe_allow_html=True,
        )

    return cluster_id
