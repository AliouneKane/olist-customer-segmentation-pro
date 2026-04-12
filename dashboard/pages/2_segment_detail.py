"""Segment Detail page — deep dive into a single cluster.

Shows per-cluster KPIs, radar chart, marketing avatar + recommendations,
Gemini AI analysis, and the full profile table.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# ── Fix: parents[2] = olist-customer-segmentation (project root) ──────────────
# File lives at: dashboard/pages/2_segment_detail.py
# parents[0] = pages/, parents[1] = dashboard/, parents[2] = project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dashboard.components.charts import radar_chart
from dashboard.components.data_store import load_cluster_profile
from dashboard.components.segment_recommendations import (
    RECOMMENDATIONS,
    SEGMENT_AVATARS,
    SEGMENT_ICONS,
    SEGMENT_NAMES,
)
from dashboard.components.kpi_cards import render_segment_kpi_row
from dashboard.components.sidebar import render_sidebar
from dashboard.styles import SEGMENT_COLORS, apply_theme, inject_css

_RADAR_FEATURES = [
    "Monetary",
    "Recency",
    "avg_delivery_delay",
    "avg_review_score",
    "avg_freight_ratio",
    "avg_installments",
    "region_freight_score",
]

_ICON_MAP = {
    "bi-credit-card-2-front": "💳",
    "bi-piggy-bank": "🐷",
    "bi-geo-alt": "📍",
    "bi-people": "👥",
    "bi-trophy": "🏆",
    "bi-emoji-frown": "😞",
}

# Hex colors for segments (matching sidebar + styles.py)
_SEG_HEX = SEGMENT_COLORS


def _badge(text: str, color: str) -> str:
    return (
        f"<span style='display:inline-block;background:{color}22;"
        f"border:1px solid {color}55;border-radius:9999px;"
        f"padding:2px 10px;font-size:0.72rem;color:{color};font-weight:600;'>{text}</span>"
    )


def _metric_pill(label: str, value: str, icon: str = "") -> str:
    return f"""
    <div style="display:flex;flex-direction:column;align-items:center;
                background:rgba(45,51,72,0.3);border-radius:10px;padding:10px 14px;
                border:1px solid rgba(45,51,72,0.6);">
        <div style="font-size:1rem;">{icon}</div>
        <div style="font-size:1.1rem;font-weight:700;color:#f1f5f9;margin:2px 0;">{value}</div>
        <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;">{label}</div>
    </div>"""


def _render_recommendation_card(cluster_id: int) -> None:
    """Renders the marketing avatar + recommendations as styled HTML."""
    name = SEGMENT_NAMES.get(cluster_id, f"Cluster {cluster_id}")
    avatar = SEGMENT_AVATARS.get(cluster_id, "")
    recs = RECOMMENDATIONS.get(cluster_id, [])
    color = _SEG_HEX[cluster_id % len(_SEG_HEX)]
    icon_class = SEGMENT_ICONS.get(cluster_id, "bi-person")
    icon = _ICON_MAP.get(icon_class, "👤")

    rec_items = "".join(
        f"""<li style="margin-bottom:10px; color:#475569; font-size:0.85rem; line-height:1.55;">
               <span style="color:{color};margin-right:6px;">▸</span>{r}</li>"""
        for r in recs
    )

    html = f"""<div style="background-color:#FFFFFF; border:1px solid #E2E8F0; border-top:3px solid {color}; border-radius:12px; padding:1.4rem 1.5rem; height:100%; box-shadow:0px 4px 15px rgba(0,0,0,0.03); position:relative; overflow:hidden;">
    <div style="font-size:1rem; font-weight:700; color:{color}; margin-bottom:14px; display:flex; align-items:center; gap:8px;">
        <span style="font-size:1.3rem;">{icon}</span> Stratégie — {name}
    </div>
    <div style="background-color:#F8FAFC; border:1px solid #E2E8F0; border-left:3px solid {color}; border-radius:8px; padding:10px 14px; margin-bottom:16px; font-style:italic; color:#64748B; font-size:0.84rem; line-height:1.6;">
        👤 {avatar}
    </div>
    <div style="font-size:0.75rem;font-weight:700;color:#64748B; text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;">
        ⚡ Actions marketing prioritaires
    </div>
    <ul style="padding-left:0; margin:0; list-style:none;">
        {rec_items}
    </ul>
</div>"""
    st.markdown(html.replace('\n', ''), unsafe_allow_html=True)


def _render_profile_table(profile_df, cluster_id: int, color: str) -> None:
    """Renders the styled cluster comparison table."""
    st.markdown(
        """<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.75rem;">
             <span style="font-size:1.2rem;">📋</span>
             <h3 style="margin:0;color:#0F172A;">Médianes du Segment vs. Tous les Segments</h3>
           </div>""",
        unsafe_allow_html=True,
    )

    display_df = profile_df.copy()
    numeric_cols = display_df.select_dtypes(include="number").columns.tolist()
    for col in numeric_cols:
        if col not in ("cluster", "n_customers"):
            display_df[col] = display_df[col].round(2)

    def _highlight_selected(row):  # type: ignore[return]
        if int(row["cluster"]) == cluster_id:
            return [f"background-color:{color}18;color:{color};font-weight:600;"] * len(row)
        return [""] * len(row)

    styled = display_df.style.apply(_highlight_selected, axis=1)
    st.dataframe(styled, use_container_width=True, hide_index=True)


def main() -> None:
    inject_css()
    cluster_id = render_sidebar()

    try:
        profile_df = load_cluster_profile()
    except FileNotFoundError as exc:
        st.error(str(exc), icon="🚨")
        return

    name = SEGMENT_NAMES.get(cluster_id, f"Cluster {cluster_id}")
    color = _SEG_HEX[cluster_id % len(_SEG_HEX)]
    icon_class = SEGMENT_ICONS.get(cluster_id, "bi-person")
    icon = _ICON_MAP.get(icon_class, "👤")

    # ── Premium Header ──────────────────────────────────────────────────────────
    row_data = profile_df[profile_df["cluster"] == cluster_id]
    n_customers = int(row_data["n_customers"].iloc[0]) if not row_data.empty else 0
    pct = float(row_data["pct_customers"].iloc[0]) if not row_data.empty else 0.0

    html_header = f"""<div style="display:flex;align-items:flex-start;justify-content:space-between; flex-wrap:wrap;gap:1rem;margin-bottom:1.75rem;">
    <div>
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
            <div style="width:42px;height:42px;border-radius:12px; background-color:#EFF6FF; border:1px solid #BFDBFE; display:flex;align-items:center; justify-content:center;font-size:1.3rem;">{icon}</div>
            <div>
                <h1 style="margin:0;font-size:1.6rem;color:#0F172A;">Segment — <span style="color:{color};">{name}</span></h1>
                <p style="margin:0;color:#64748B;font-size:0.85rem;">Cluster {cluster_id} · Analyse détaillée du profil et recommandations marketing</p>
            </div>
        </div>
    </div>
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
        <span style="background-color:#E0E7FF;border:1px solid #C7D2FE;color:#2563EB; padding:5px 14px;border-radius:9999px;font-size:0.8rem;font-weight:600;">{n_customers:,} clients</span>
        <span style="background-color:#F8FAFC;border:1px solid #E2E8F0;color:#64748B; padding:5px 14px;border-radius:9999px;font-size:0.8rem;font-weight:500;">{pct:.1f}% de la base</span>
    </div>
</div>"""
    st.markdown(html_header.replace('\n', ''), unsafe_allow_html=True)

    # ── Segment KPIs ───────────────────────────────────────────────────────────
    render_segment_kpi_row(profile_df, cluster_id)
    st.markdown("<div style='margin-top:1.75rem;'></div>", unsafe_allow_html=True)

    # ── Radar + Recommendations ────────────────────────────────────────────────
    col_radar, col_rec = st.columns([3, 2], gap="large")

    with col_radar:
        st.markdown(
            "<div style='font-size:0.7rem;font-weight:700;color:#64748b;"
            "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;'>"
            "📡 Profil Radar Normalisé</div>",
            unsafe_allow_html=True,
        )
        radar_cols = [c for c in _RADAR_FEATURES if c in profile_df.columns]
        if radar_cols:
            fig = radar_chart(profile_df, radar_cols, selected_cluster=cluster_id)
            apply_theme(fig, height=480)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Colonnes radar non disponibles dans le profil.", icon="ℹ️")

    with col_rec:
        st.markdown(
            "<div style='font-size:0.7rem;font-weight:700;color:#64748b;"
            "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;'>"
            "🎯 Stratégie Marketing</div>",
            unsafe_allow_html=True,
        )
        _render_recommendation_card(cluster_id)

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    st.divider()

    # ── Profile table ──────────────────────────────────────────────────────────
    _render_profile_table(profile_df, cluster_id, color)


main()
