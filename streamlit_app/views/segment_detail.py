"""Segment Detail page — deep dive into a single cluster."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from streamlit_app.components.charts import bar_segment_comparison, radar_chart
from streamlit_app.components.data_store import load_cluster_profile
from streamlit_app.components.segment_recommendations import (
    RECOMMENDATIONS,
    SEGMENT_AVATARS,
    SEGMENT_ICONS,
    SEGMENT_NAMES,
)
from streamlit_app.components.kpi_cards import render_segment_kpi_row
from streamlit_app.styles import OLIST_BLUE, OLIST_YELLOW, SEGMENT_COLORS, apply_olist_theme

_RADAR_FEATURES = [
    "Monetary",
    "Recency",
    "avg_delivery_delay",
    "avg_review_score",
    "avg_freight_ratio",
    "avg_installments",
    "region_freight_score",
]

_ICON_EMOJI_MAP = {
    "bi-credit-card-2-front": "💳",
    "bi-piggy-bank": "🐷",
    "bi-geo-alt": "📍",
    "bi-people": "👥",
    "bi-trophy": "🏆",
    "bi-emoji-frown": "😞",
}


def _recommendation_card(cluster_id: int) -> None:
    name = SEGMENT_NAMES.get(cluster_id, f"Cluster {cluster_id}")
    avatar = SEGMENT_AVATARS.get(cluster_id, "")
    recs = RECOMMENDATIONS.get(cluster_id, [])
    color = SEGMENT_COLORS[cluster_id % len(SEGMENT_COLORS)]
    icon = _ICON_EMOJI_MAP.get(SEGMENT_ICONS.get(cluster_id, ""), "👤")

    rec_html = "".join(
        f"<li style='margin-bottom:8px; color:#374151; line-height:1.5;'>{r}</li>"
        for r in recs
    )

    st.markdown(
        f"""
        <div style="
            background: #FFFFFF;
            border: 1px solid #e5e7eb;
            border-top: 4px solid {color};
            border-radius: 8px;
            padding: 1.25rem;
            height: 100%;
            box-shadow: 0 1px 3px #d1d5db;
        ">
            <div style="font-size:1rem; font-weight:700; color:{color}; margin-bottom:12px;">
                {icon} Stratégie — {name}
            </div>
            <div style="
                background:{color}0d;
                border-left: 3px solid {color};
                border-radius:0 6px 6px 0;
                padding:10px 14px;
                margin-bottom:14px;
                font-style:italic;
                color:#6b7280;
                font-size:0.85rem;
                line-height:1.6;
            ">
                👤 {avatar}
            </div>
            <div style="font-size:0.75rem; font-weight:700; color:#9ca3af;
                        text-transform:uppercase; letter-spacing:0.07em; margin-bottom:8px;">
                Actions marketing
            </div>
            <ul style="padding-left:1.1rem; margin:0; font-size:0.84rem;">
                {rec_html}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _ai_insight_section(cluster_id: int, profile_df) -> None:
    color = SEGMENT_COLORS[cluster_id % len(SEGMENT_COLORS)]

    st.markdown(
        f"""
        <div style="margin-bottom:0.75rem;">
            <div style="font-size:1.05rem; font-weight:800; color:#212121;">
                ⚡ Choses à faire dès maintenant
            </div>
            <div style="font-size:0.8rem; color:#6b7280; margin-top:3px;">
                5 actions concrètes générées par IA · propres à ce segment
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        from streamlit_app.components.ai_insight import _GEMINI_AVAILABLE, get_ai_insight

        if not _GEMINI_AVAILABLE:
            st.info("IA indisponible — configurez `GEMINI_API_KEY` dans `.env`.", icon="🤖")
            return

        row = profile_df[profile_df["cluster"] == cluster_id]
        profile_hash = (
            str(hash(tuple(row.values.flatten().tolist()))) if not row.empty else "0"
        )

        with st.spinner("Génération en cours..."):
            insight_md = get_ai_insight(cluster_id, profile_hash)

        if insight_md is None:
            st.warning("Profil introuvable pour ce cluster.")
            return

        # Parse numbered lines and render as numbered action cards
        lines = [
            ln.strip() for ln in insight_md.strip().splitlines()
            if ln.strip() and ln.strip()[0].isdigit()
        ]
        if not lines:
            st.markdown(insight_md)
            return

        for i, line in enumerate(lines):
            text = line.split(".", 1)[-1].strip() if "." in line else line
            st.markdown(
                f"""
                <div style="display:flex; align-items:flex-start; gap:12px;
                            background:#FFFFFF; border:1px solid #e5e7eb;
                            border-left:4px solid {color};
                            border-radius:0 8px 8px 0;
                            padding:0.65rem 1rem; margin-bottom:0.45rem;
                            box-shadow:0 1px 3px #f3f4f6;">
                    <div style="background:{color}; color:#FFFFFF;
                                font-size:0.72rem; font-weight:800;
                                border-radius:50%; min-width:22px; height:22px;
                                display:flex; align-items:center; justify-content:center;
                                flex-shrink:0; margin-top:1px;">{i+1}</div>
                    <div style="font-size:0.85rem; color:#212121;
                                line-height:1.55; font-weight:500;">{text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    except Exception as exc:
        st.error(f"Erreur IA : {exc}")


def render(cluster_id: int) -> None:
    """Renders the Segment Detail page for a given cluster.

    Args:
        cluster_id: Cluster label (0–5).
    """
    try:
        profile_df = load_cluster_profile()
    except FileNotFoundError as exc:
        st.error(str(exc))
        return

    name = SEGMENT_NAMES.get(cluster_id, f"Cluster {cluster_id}")
    color = SEGMENT_COLORS[cluster_id % len(SEGMENT_COLORS)]

    # Header
    st.markdown(
        f"<h2 style='margin-bottom:0.2rem;'>"
        f"🔍 Segment — <span style='color:{color};'>{name}</span></h2>"
        f"<p style='color:#6b7280; margin-bottom:1.25rem;'>"
        f"Cluster {cluster_id} · Analyse détaillée du profil et recommandations marketing</p>",
        unsafe_allow_html=True,
    )

    # Segment KPIs
    render_segment_kpi_row(profile_df, cluster_id)
    st.markdown("<br>", unsafe_allow_html=True)

    # Radar + Recommendations
    col_radar, col_rec = st.columns([3, 2], gap="large")
    with col_radar:
        radar_cols = [c for c in _RADAR_FEATURES if c in profile_df.columns]
        fig = radar_chart(profile_df, radar_cols, selected_cluster=cluster_id)
        apply_olist_theme(fig, height=460)
        st.plotly_chart(fig, use_container_width=True)
    with col_rec:
        _recommendation_card(cluster_id)

    st.divider()

    # Progress bar — CLV vs. Champions target
    row = profile_df[profile_df["cluster"] == cluster_id]
    if not row.empty and "CLV_proxy" in profile_df.columns:
        clv = float(row.iloc[0]["CLV_proxy"])
        clv_max = float(profile_df["CLV_proxy"].max())
        pct = min(int(clv / clv_max * 100), 100) if clv_max > 0 else 0
        st.markdown(
            f"<p style='font-weight:600; color:#374151; margin-bottom:4px;'>"
            f"CLV Proxy vs. Champions : {clv:,.0f} / {clv_max:,.0f} BRL ({pct}%)</p>",
            unsafe_allow_html=True,
        )
        st.progress(pct / 100)

    st.divider()

    # AI Insight
    _ai_insight_section(cluster_id, profile_df)

    st.divider()

    # Bar chart — segment vs. all
    st.markdown(
        f"<h3 style='color:{OLIST_BLUE}; margin-bottom:0.75rem;'>"
        "Comparaison Monetary — Ce Segment vs. Tous</h3>",
        unsafe_allow_html=True,
    )
    fig = bar_segment_comparison(profile_df, "Monetary")
    apply_olist_theme(fig, height=300)
    st.plotly_chart(fig, use_container_width=True)

    # Expandable profile table
    with st.expander("📄 VOIR LES MÉDIANES DE TOUS LES SEGMENTS"):
        display_df = profile_df.copy()
        for col in display_df.select_dtypes(include="float").columns:
            display_df[col] = display_df[col].round(2)

        def _hl(r):  # type: ignore[return]
            if int(r["cluster"]) == cluster_id:
                return [f"background-color:{color}1a; font-weight:600; color:{color};"] * len(r)
            return [""] * len(r)

        st.dataframe(
            display_df.style.apply(_hl, axis=1),
            use_container_width=True,
            hide_index=True,
        )
