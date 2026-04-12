"""Algorithm Comparison page — benchmark clustering algorithms.

Displays the model_comparison.csv table and a grouped bar chart
comparing silhouette, Davies-Bouldin, and Calinski-Harabasz scores.
Falls back gracefully when the CSV is not available.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# ── Fix: parents[2] = olist-customer-segmentation (project root) ──────────────
# File lives at: dashboard/pages/3_comparison.py
# parents[0] = pages/, parents[1] = dashboard/, parents[2] = project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dashboard.components.charts import bar_algorithm_metrics
from dashboard.components.data_store import load_model_comparison
from dashboard.components.sidebar import render_sidebar
from dashboard.styles import (
    ACCENT_GREEN,
    ACCENT_BLUE,
    ACCENT_YELLOW,
    ACCENT_RED,
    SEGMENT_COLORS,
    apply_theme,
    inject_css,
)

# ── Metric explanation cards content ─────────────────────────────────────────

_METRIC_EXPLANATIONS = [
    {
        "icon": "📈",
        "name": "Silhouette Score",
        "direction": "Plus élevé = meilleur",
        "range": "[−1, 1]",
        "color": ACCENT_GREEN,
        "desc": "Mesure la cohésion intra-cluster vs. la séparation inter-cluster. 1 = parfait, 0 = chevauchement.",
    },
    {
        "icon": "📉",
        "name": "Davies-Bouldin",
        "direction": "Plus faible = meilleur",
        "range": "[0, ∞)",
        "color": ACCENT_YELLOW,
        "desc": "Rapport de la dispersion intra-cluster sur la distance inter-cluster. 0 = clusters parfaits.",
    },
    {
        "icon": "🔭",
        "name": "Calinski-Harabasz",
        "direction": "Plus élevé = meilleur",
        "range": "[0, ∞)",
        "color": ACCENT_BLUE,
        "desc": "Ratio variance inter/intra-cluster. Favorise les clusters denses et bien séparés.",
    },
]


def _render_metric_guide() -> None:
    """Renders 3 metric explanation pills."""
    cols = st.columns(3, gap="medium")
    for col, m in zip(cols, _METRIC_EXPLANATIONS):
        c = m["color"]
        with col:
            html = f"""<div style="background-color:#FFFFFF; border:1px solid #E2E8F0; border-top:2px solid {c}; border-radius:12px; padding:1rem 1.1rem; box-shadow:0px 4px 15px rgba(0,0,0,0.03);">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        <span style="font-size:1.2rem;">{m['icon']}</span>
        <span style="font-weight:700;color:{c};font-size:0.9rem;">{m['name']}</span>
    </div>
    <div style="display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;">
        <span style="background-color:{c}15;border:1px solid {c}30;color:{c}; padding:2px 8px;border-radius:9999px;font-size:0.7rem;font-weight:600;">
            {m['direction']}
        </span>
        <span style="background-color:#F1F5F9;border:1px solid #E2E8F0; color:#64748B;padding:2px 8px;border-radius:9999px; font-size:0.7rem;font-weight:500;">
            {m['range']}
        </span>
    </div>
    <p style="color:#64748B;font-size:0.8rem;margin:0;line-height:1.5;">
        {m['desc']}
    </p>
</div>"""
            st.markdown(html.replace('\n', ''), unsafe_allow_html=True)


def _render_best_algo_banner(comparison_df) -> None:
    """Highlights the best algorithm with a premium banner."""
    if "composite_score" not in comparison_df.columns:
        return

    best_idx = comparison_df["composite_score"].idxmax()
    best = comparison_df.loc[best_idx]
    algo_name = str(best.get("algorithm", "—"))
    k = int(best.get("n_clusters", best.get("k", 0)))
    sil = float(best.get("silhouette", 0))
    db = float(best.get("davies_bouldin", 0))
    ch = float(best.get("calinski_harabasz", 0))
    score = float(best.get("composite_score", 0))

    html = f"""<div style="background-color:#F0FDF4; border:1px solid #BBF7D0; border-radius:12px; padding:1.2rem 1.6rem; margin-bottom:1.75rem; display:flex; align-items:center; gap:1.2rem; flex-wrap:wrap;">
    <div style="font-size:2.5rem;filter:drop-shadow(0 0 8px rgba(16,185,129,0.3));">🏆</div>
    <div style="flex:1;min-width:200px;">
        <div style="font-size:0.7rem;color:#059669;text-transform:uppercase; letter-spacing:0.1em;font-weight:700;margin-bottom:4px;">Meilleur Algorithme</div>
        <div style="font-size:1.25rem;font-weight:800;color:#065F46; letter-spacing:-0.01em;">{algo_name} — k={k}</div>
        <div style="font-size:0.82rem;color:#10B981;margin-top:2px;">Score composite normalisé le plus élevé</div>
    </div>
    <div style="display:flex;gap:12px;flex-wrap:wrap;">
        <div style="text-align:center;background-color:#FFFFFF; border:1px solid #E2E8F0;border-radius:10px; padding:8px 14px;box-shadow:0px 2px 4px rgba(0,0,0,0.02);">
            <div style="font-size:1.1rem;font-weight:700;color:{ACCENT_GREEN};">{sil:.4f}</div>
            <div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;">Silhouette ↑</div>
        </div>
        <div style="text-align:center;background-color:#FFFFFF; border:1px solid #E2E8F0;border-radius:10px; padding:8px 14px;box-shadow:0px 2px 4px rgba(0,0,0,0.02);">
            <div style="font-size:1.1rem;font-weight:700;color:{ACCENT_YELLOW};">{db:.4f}</div>
            <div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;">Davies-B. ↓</div>
        </div>
        <div style="text-align:center;background-color:#FFFFFF; border:1px solid #E2E8F0;border-radius:10px; padding:8px 14px;box-shadow:0px 2px 4px rgba(0,0,0,0.02);">
            <div style="font-size:1.1rem;font-weight:700;color:{ACCENT_BLUE};">{ch:,.0f}</div>
            <div style="font-size:0.65rem;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;">Calinski-H. ↑</div>
        </div>
    </div>
</div>"""
    st.markdown(html.replace('\n', ''), unsafe_allow_html=True)


def _render_algorithm_cards(comparison_df) -> None:
    """Renders per-algorithm score cards as a visual alternative to the table."""
    cols = st.columns(len(comparison_df), gap="medium")
    has_best = "composite_score" in comparison_df.columns
    best_idx = comparison_df["composite_score"].idxmax() if has_best else -1

    for col, (idx, row) in zip(cols, comparison_df.iterrows()):
        algo = str(row.get("algorithm", f"Algo {idx}"))
        k = int(row.get("n_clusters", 0))
        sil = float(row.get("silhouette", 0))
        db = float(row.get("davies_bouldin", 0))
        ch = float(row.get("calinski_harabasz", 0))
        cs = float(row.get("composite_score", 0)) if has_best else 0
        is_best = has_best and idx == best_idx

        color = SEGMENT_COLORS[int(idx) % len(SEGMENT_COLORS)]
        crown = "🏆 " if is_best else ""
        glow = f"box-shadow:0 0 24px {color}22;" if is_best else ""

        pct = max(0, min(1, (cs + 1) / 2)) * 100  # normalize to 0-100

        with col:
            bg_color = f"{color}0A" if is_best else "#FFFFFF"
            html_str = f"""<div style="background-color:{bg_color}; border:1px solid {'#CBD5E1' if not is_best else color}; border-top:3px solid {color}; border-radius:12px; padding:1.2rem 1.1rem; {glow} transition:all 0.2s ease; position:relative;">
{'<div style="position:absolute;top:10px;right:12px;font-size:1rem;">👑</div>' if is_best else ''}
<div style="font-size:1.1rem;font-weight:800;color:#0F172A; margin-bottom:4px;">{crown}{algo}</div>
<div style="font-size:0.75rem;color:#64748B;margin-bottom:16px;">k = {k} clusters</div>
<div style="display:flex;flex-direction:column;gap:8px;">
<div>
<div style="display:flex;justify-content:space-between; font-size:0.75rem;margin-bottom:3px;">
<span style="color:#64748B;">Silhouette ↑</span>
<span style="color:{ACCENT_GREEN};font-weight:600;">{sil:.4f}</span>
</div>
<div style="height:4px;background-color:#E2E8F0;border-radius:2px;">
<div style="height:100%;width:{min(sil,1)*100:.1f}%; background-color:{ACCENT_GREEN};border-radius:2px;"></div>
</div>
</div>
<div>
<div style="display:flex;justify-content:space-between; font-size:0.75rem;margin-bottom:3px;">
<span style="color:#64748B;">Davies-B. ↓</span>
<span style="color:{ACCENT_YELLOW};font-weight:600;">{db:.4f}</span>
</div>
</div>
<div>
<div style="display:flex;justify-content:space-between; font-size:0.75rem;margin-bottom:3px;">
<span style="color:#64748B;">Calinski-H. ↑</span>
<span style="color:{ACCENT_BLUE};font-weight:600;">{ch:,.0f}</span>
</div>
</div>
</div>
<div style="margin-top:14px;padding-top:12px;border-top:1px solid #E2E8F0;">
<div style="font-size:0.7rem;color:#64748B;margin-bottom:4px; text-transform:uppercase;letter-spacing:0.06em;">
Score composite
</div>
<div style="height:6px;background-color:#E2E8F0;border-radius:3px;">
<div style="height:100%;width:{pct:.1f}%; background-color:{color}; border-radius:3px;"></div>
</div>
<div style="font-size:0.85rem;font-weight:700;color:{color}; margin-top:4px;">{cs:+.4f}</div>
</div>
</div>"""
            st.markdown(html_str.replace('\n', ''), unsafe_allow_html=True)


def main() -> None:
    inject_css()
    render_sidebar()

    # ── Premium Header ──────────────────────────────────────────────────────────
    html_header = """<div style="margin-bottom:1.75rem;">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
        <div style="width:42px;height:42px;border-radius:12px; background-color:#FEE2E2; border:1px solid #FECACA; display:flex;align-items:center; justify-content:center;font-size:1.3rem;">⚖️</div>
        <div>
            <h1 style="margin:0;font-size:1.6rem;color:#0F172A;">Comparaison des Algorithmes</h1>
            <p style="margin:0;color:#64748B;font-size:0.85rem;">Benchmark KMeans k=4/5/6 sur le dataset Olist — 93 358 clients</p>
        </div>
    </div>
</div>"""
    st.markdown(html_header.replace('\n', ''), unsafe_allow_html=True)

    # ── Metric guide ───────────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.75rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:10px;'>"
        "📐 Guide des métriques</div>",
        unsafe_allow_html=True,
    )
    _render_metric_guide()
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # ── Load data ──────────────────────────────────────────────────────────────
    comparison_df = load_model_comparison()

    if comparison_df is None or comparison_df.empty:
        html_error = """<div style="background-color:#FEF2F2; border:1px solid #FECACA;border-radius:12px; padding:1.5rem;text-align:center;">
    <div style="font-size:2.5rem;margin-bottom:12px;">📊</div>
    <div style="font-weight:700;color:#991B1B;font-size:1rem;margin-bottom:6px;">Données non disponibles</div>
    <div style="color:#B91C1C;font-size:0.875rem;">Le fichier <code style="background-color:#FCA5A5;padding:1px 6px;border-radius:4px;color:#7F1D1D;">data/processed/model_comparison.csv</code> est introuvable.<br>Exécutez <code style="background-color:#FCA5A5;padding:1px 6px;border-radius:4px;color:#7F1D1D;">scripts/generate_artifacts.py</code> pour générer les métriques.</div>
</div>"""
        st.markdown(html_error.replace('\n', ''), unsafe_allow_html=True)
        return

    # ── Best algorithm banner ──────────────────────────────────────────────────
    _render_best_algo_banner(comparison_df)

    # ── Algorithm score cards ──────────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:0.75rem;font-weight:700;color:#64748B;"
        "text-transform:uppercase;letter-spacing:0.1em;margin-bottom:12px;'>"
        "🎯 Scores par Algorithme</div>",
        unsafe_allow_html=True,
    )
    _render_algorithm_cards(comparison_df)

    st.divider()

    # ── Tabs: Table | Chart ────────────────────────────────────────────────────
    tab_table, tab_chart = st.tabs(["📋  Tableau des Métriques", "📊  Visualisation"])

    with tab_table:
        display_df = comparison_df.copy()
        float_cols = display_df.select_dtypes(include="float").columns
        for col in float_cols:
            display_df[col] = display_df[col].round(4)

        col_config: dict = {}
        if "silhouette" in display_df.columns:
            col_config["silhouette"] = st.column_config.NumberColumn(
                "Silhouette ↑",
                help="Plus élevé = meilleur (max 1.0)",
                format="%.4f",
            )
        if "davies_bouldin" in display_df.columns:
            col_config["davies_bouldin"] = st.column_config.NumberColumn(
                "Davies-Bouldin ↓",
                help="Plus faible = meilleur",
                format="%.4f",
            )
        if "calinski_harabasz" in display_df.columns:
            col_config["calinski_harabasz"] = st.column_config.NumberColumn(
                "Calinski-Harabasz ↑",
                help="Plus élevé = meilleur",
                format="%.1f",
            )
        if "composite_score" in display_df.columns:
            col_config["composite_score"] = st.column_config.ProgressColumn(
                "Score Composite",
                help="Score normalisé combinant les 3 métriques",
                format="%.4f",
                min_value=float(display_df["composite_score"].min()),
                max_value=float(display_df["composite_score"].max()),
            )

        st.dataframe(display_df, use_container_width=True, hide_index=True, column_config=col_config)

    with tab_chart:
        bar_fig = bar_algorithm_metrics(comparison_df)
        if bar_fig.data:
            apply_theme(bar_fig, height=450)
            st.plotly_chart(bar_fig, use_container_width=True)
        else:
            st.info("Aucune métrique disponible pour le graphique.", icon="ℹ️")

    st.divider()

    # ── Methodology note ───────────────────────────────────────────────────────
    html_method = f"""<div style="background-color:#F8FAFC; border:1px solid #E2E8F0; border-left:3px solid {ACCENT_BLUE}; border-radius:12px; padding:1rem 1.25rem; font-size:0.85rem; color:#64748B; line-height:1.7;">
    <strong style="color:#0F172A;">📐 Méthodologie :</strong>
    Le <em>score composite</em> normalise les trois métriques sur [0,1] et les agrège (silhouette ↑ positif, DB ↓ inversé, CH ↑ positif).
    <strong style="color:{ACCENT_GREEN};">KMeans k=6</strong> a été retenu comme algorithme de production avec un Silhouette de <strong style="color:{ACCENT_GREEN};">0.213</strong>.
</div>"""
    st.markdown(html_method.replace('\n', ''), unsafe_allow_html=True)


main()
