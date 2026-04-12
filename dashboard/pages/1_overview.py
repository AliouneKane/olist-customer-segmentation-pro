"""Overview page — global distribution and segment comparison.

Displays:
- 4 global KPI cards
- Pie chart (segment distribution) + heatmap side by side
- Bar chart: Monetary comparison across segments
- Bar chart: CLV proxy comparison
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# ── Fix: parents[2] = olist-customer-segmentation (project root) ──────────────
# File lives at: dashboard/pages/1_overview.py
# parents[0] = pages/, parents[1] = dashboard/, parents[2] = project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dashboard.components.charts import (
    bar_segment_comparison,
    heatmap_cluster_features,
    pie_segment_distribution,
)
from dashboard.components.data_store import load_cluster_profile
from dashboard.components.kpi_cards import render_global_kpi_row
from dashboard.components.sidebar import render_sidebar
from dashboard.styles import ACCENT_BLUE, SEGMENT_COLORS, apply_theme, inject_css

# ── Page config is set by main.py — do NOT call st.set_page_config() here ─────

_HEATMAP_FEATURES = [
    "Monetary",
    "Recency",
    "Frequency",
    "avg_review_score",
    "avg_freight_ratio",
    "avg_delivery_delay",
    "avg_installments",
    "CLV_proxy",
]

_SEGMENT_NAMES = {
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


def _render_segment_summary_row(profile_df) -> None:
    """Renders a row of 6 compact segment pill cards."""
    st.markdown(
        "<div style='font-size:0.7rem;font-weight:700;color:#64748b;"
        "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;'>"
        "🎯 Aperçu des 6 Segments</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(6, gap="small")
    for idx, row in profile_df.iterrows():
        cid = int(row["cluster"])
        color = SEGMENT_COLORS[cid % len(SEGMENT_COLORS)]
        name = _SEGMENT_NAMES.get(cid, f"Cluster {cid}")
        icon = _SEGMENT_ICONS.get(cid, "👤")
        n = int(row["n_customers"])
        pct = float(row.get("pct_customers", 0))

        with cols[cid]:
            st.markdown(
                f"""<div style="background:linear-gradient(135deg,rgba(28,32,48,0.9),rgba(20,23,32,0.95));
                                border:1px solid {color}33;border-top:2px solid {color};
                                border-radius:12px;padding:10px;text-align:center;
                                box-shadow:0 4px 12px rgba(0,0,0,0.2);
                                transition:transform 0.2s ease;">
                      <div style="font-size:1.2rem;margin-bottom:4px;">{icon}</div>
                      <div style="font-size:0.7rem;font-weight:700;color:{color};
                                  margin-bottom:2px;line-height:1.2;">{name}</div>
                      <div style="font-size:1rem;font-weight:800;color:#f1f5f9;">{pct:.0f}%</div>
                      <div style="font-size:0.65rem;color:#64748b;">{n:,} clients</div>
                    </div>""",
                unsafe_allow_html=True,
            )


def main() -> None:
    inject_css()
    render_sidebar()

    # ── Load data ──────────────────────────────────────────────────────────────
    try:
        profile_df = load_cluster_profile()
    except FileNotFoundError as exc:
        st.error(str(exc), icon="🚨")
        return

    # ── Premium Header ──────────────────────────────────────────────────────────
    st.markdown(
        """<div style="margin-bottom:1.5rem;">
             <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
               <div style="width:42px;height:42px;border-radius:12px;
                           background-color:#E0E7FF;
                           border:1px solid #C7D2FE;display:flex;align-items:center;
                           justify-content:center;font-size:1.3rem;">📊</div>
               <div>
                 <h1 style="margin:0;font-size:1.6rem;color:#0F172A;">Vue d'Ensemble</h1>
                 <p style="margin:0;color:#64748B;font-size:0.85rem;">
                   Distribution des 93 358 clients Olist sur 6 segments — KMeans k=6 · Silhouette 0.213
                 </p>
               </div>
             </div>
           </div>""",
        unsafe_allow_html=True,
    )

    # ── Global KPIs ────────────────────────────────────────────────────────────
    render_global_kpi_row(profile_df)
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Segment summary pills ──────────────────────────────────────────────────
    _render_segment_summary_row(profile_df)
    st.markdown("<div style='margin-top:1.75rem;'></div>", unsafe_allow_html=True)

    # ── Pie + Heatmap ──────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.75rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;'>"
        "📈 Distribution & Profils</div>",
        unsafe_allow_html=True,
    )
    col_left, col_right = st.columns([1, 1], gap="medium")

    with col_left:
        pie_fig = pie_segment_distribution(profile_df)
        apply_theme(pie_fig, height=420)
        st.plotly_chart(pie_fig, use_container_width=True)

    with col_right:
        heatmap_cols = [c for c in _HEATMAP_FEATURES if c in profile_df.columns]
        if heatmap_cols:
            heatmap_fig = heatmap_cluster_features(profile_df, heatmap_cols)
            apply_theme(heatmap_fig, height=420)
            st.plotly_chart(heatmap_fig, use_container_width=True)

    st.divider()

    # ── Bar charts ─────────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.75rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;'>"
        "💰 Comparaison par Métrique</div>",
        unsafe_allow_html=True,
    )

    bar_col1, bar_col2 = st.columns(2, gap="medium")

    with bar_col1:
        bar_monetary = bar_segment_comparison(profile_df, "Monetary")
        apply_theme(bar_monetary, height=350)
        st.plotly_chart(bar_monetary, use_container_width=True)

    with bar_col2:
        if "CLV_proxy" in profile_df.columns:
            bar_clv = bar_segment_comparison(profile_df, "CLV_proxy")
            apply_theme(bar_clv, height=350)
            st.plotly_chart(bar_clv, use_container_width=True)
        elif "avg_review_score" in profile_df.columns:
            bar_review = bar_segment_comparison(profile_df, "avg_review_score")
            apply_theme(bar_review, height=350)
            st.plotly_chart(bar_review, use_container_width=True)

    st.divider()

    # ── Recency + Freight ──────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.75rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;'>"
        "⏱️ Récence & Logistique</div>",
        unsafe_allow_html=True,
    )
    bar_col3, bar_col4 = st.columns(2, gap="medium")

    with bar_col3:
        if "Recency" in profile_df.columns:
            bar_rec = bar_segment_comparison(profile_df, "Recency")
            apply_theme(bar_rec, height=350)
            st.plotly_chart(bar_rec, use_container_width=True)

    with bar_col4:
        if "avg_freight_ratio" in profile_df.columns:
            bar_freight = bar_segment_comparison(profile_df, "avg_freight_ratio")
            apply_theme(bar_freight, height=350)
            st.plotly_chart(bar_freight, use_container_width=True)

    # ── Footer ─────────────────────────────────────────────────────────────────
    st.markdown(
        f"""<div style="margin-top:1rem;padding:1rem;
                        background-color:#FFFFFF;
                        border:1px solid #E2E8F0;border-radius:12px;
                        display:flex;align-items:center;justify-content:space-between;
                        flex-wrap:wrap;gap:8px;box-shadow:0 2px 4px rgba(0,0,0,0.02);">
             <div style="font-size:0.8rem;color:#64748B;">
               🛍️ <strong style="color:#0F172A;">Olist Customer Segmentation</strong> ·
               KMeans k=6 · Silhouette 0.213 · 93 358 clients
             </div>
             <div style="display:flex;gap:8px;">
               <span style="background-color:#EFF6FF;border:1px solid #BFDBFE;
                            color:#2563EB;padding:4px 12px;border-radius:9999px;
                            font-size:0.75rem;font-weight:600;">
                 Production Model
               </span>
             </div>
           </div>""",
        unsafe_allow_html=True,
    )


main()
