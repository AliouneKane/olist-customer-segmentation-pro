"""Algorithm Comparison page — benchmark clustering algorithms."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dashboard.components.charts import bar_algorithm_metrics, table_algorithm_comparison
from dashboard.components.data_store import load_model_comparison
from streamlit_app.styles import OLIST_BLUE, apply_olist_theme


def render() -> None:
    """Renders the Algorithm Comparison page."""
    # ── Header ─────────────────────────────────────────────────────────────────
    st.markdown(
        f"<h2 style='color:{OLIST_BLUE}; margin-bottom:0.2rem;'>"
        "⚖️ Comparaison des Algorithmes de Clustering</h2>"
        "<p style='color:#6b7280; margin-bottom:1.25rem;'>"
        "Benchmark KMeans · CAH · DBSCAN sur le dataset Olist (93 358 clients)</p>",
        unsafe_allow_html=True,
    )

    comparison_df = load_model_comparison()

    if comparison_df is None:
        st.info(
            "`data/processed/model_comparison.csv` introuvable. "
            "Exécutez `scripts/generate_artifacts.py` pour générer les métriques.",
            icon="📊",
        )
        return

    # ── Best algorithm banner ──────────────────────────────────────────────────
    if "composite_score" in comparison_df.columns:
        best = comparison_df.loc[comparison_df["composite_score"].idxmax()]
        algo = best.get("algorithm", "—")
        k = int(best.get("n_clusters", best.get("k", 0)))
        sil = float(best.get("silhouette", 0))

        col_a, col_b, col_c = st.columns(3, gap="small")
        with col_a:
            st.info("Meilleur Algorithme", icon="🏆")
            st.metric("Algo", f"{algo} (k={k})")
        with col_b:
            st.info("Silhouette Score ↑", icon="📈")
            st.metric("Score", f"{sil:.4f}")
        with col_c:
            st.info("Score Composite ↑", icon="🎯")
            st.metric("Normalisé", f"{float(best.get('composite_score', 0)):.4f}")

        from streamlit_extras.metric_cards import style_metric_cards
        style_metric_cards(
            background_color="#FFFFFF",
            border_left_color="#0041FF",
            border_color="#e5e7eb",
            box_shadow="#d1d5db",
        )

    st.divider()

    # ── Metrics table ──────────────────────────────────────────────────────────
    st.markdown(
        f"<h3 style='color:{OLIST_BLUE}; margin-bottom:0.75rem;'>Tableau des Métriques</h3>",
        unsafe_allow_html=True,
    )

    display_df = comparison_df.copy()
    for col in display_df.select_dtypes(include="float").columns:
        display_df[col] = display_df[col].round(4)

    col_config: dict = {}
    if "silhouette" in display_df.columns:
        col_config["silhouette"] = st.column_config.NumberColumn(
            "Silhouette ↑", help="Plus élevé = meilleur", format="%.4f"
        )
    if "davies_bouldin" in display_df.columns:
        col_config["davies_bouldin"] = st.column_config.NumberColumn(
            "Davies-Bouldin ↓", help="Plus faible = meilleur", format="%.4f"
        )
    if "calinski_harabasz" in display_df.columns:
        col_config["calinski_harabasz"] = st.column_config.NumberColumn(
            "Calinski-Harabasz ↑", help="Plus élevé = meilleur", format="%.1f"
        )
    if "composite_score" in display_df.columns:
        col_config["composite_score"] = st.column_config.ProgressColumn(
            "Score Composite",
            format="%.4f",
            min_value=0,
            max_value=float(display_df["composite_score"].max()),
        )

    st.dataframe(display_df, use_container_width=True, hide_index=True, column_config=col_config)

    st.divider()

    # ── Bar chart ──────────────────────────────────────────────────────────────
    st.markdown(
        f"<h3 style='color:{OLIST_BLUE}; margin-bottom:0.75rem;'>Comparaison Visuelle</h3>",
        unsafe_allow_html=True,
    )
    bar_fig = bar_algorithm_metrics(comparison_df)
    apply_olist_theme(bar_fig, height=420)
    st.plotly_chart(bar_fig, use_container_width=True)

    # ── Plotly table ───────────────────────────────────────────────────────────
    table_fig = table_algorithm_comparison(comparison_df)
    apply_olist_theme(table_fig, height=300)
    st.plotly_chart(table_fig, use_container_width=True)

    # ── Methodology note ───────────────────────────────────────────────────────
    with st.expander("📐 MÉTHODOLOGIE ET DÉFINITION DES MÉTRIQUES"):
        st.markdown(
            """
**Silhouette Score** ↑ (max 1.0)
Mesure la cohésion intra-cluster et la séparation inter-clusters.
Un score > 0.20 est acceptable sur des données comportementales.

**Davies-Bouldin Index** ↓ (min 0)
Rapport de la dispersion intra-cluster sur la séparation inter-clusters.
Plus il est faible, meilleure est la configuration.

**Calinski-Harabasz Index** ↑
Rapport entre la variance inter-clusters et la variance intra-clusters.
Plus il est élevé, plus les clusters sont denses et bien séparés.

**Score Composite** = normalisé(Silhouette ↑) + normalisé(1/DB ↓) + normalisé(CH ↑) / 3
KMeans k=6 retenu avec Silhouette **0.213** comme algorithme de production.
            """
        )
