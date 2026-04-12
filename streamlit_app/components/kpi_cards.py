"""KPI metric row components — style_metric_cards template pattern."""

from __future__ import annotations

import pandas as pd
import streamlit as st
from numerize.numerize import numerize
from streamlit_extras.metric_cards import style_metric_cards


def _apply_card_style() -> None:
    """Applies the metric card style (template pattern: white bg, blue left border)."""
    style_metric_cards(
        background_color="#FFFFFF",
        border_left_color="#0041FF",
        border_color="#e5e7eb",
        box_shadow="#d1d5db",
    )


def render_global_kpi_row(profile_df: pd.DataFrame) -> None:
    """Renders 5 global KPI metrics following the template 5-column pattern.

    Args:
        profile_df: Cluster profile DataFrame from load_cluster_profile().
    """
    total_customers = int(profile_df["n_customers"].sum())
    n_clusters = len(profile_df)
    median_clv = float(profile_df["CLV_proxy"].median()) if "CLV_proxy" in profile_df.columns else 0.0
    avg_review = (
        float(profile_df["avg_review_score"].mean())
        if "avg_review_score" in profile_df.columns
        else 0.0
    )
    median_monetary = (
        float(profile_df["Monetary"].median()) if "Monetary" in profile_df.columns else 0.0
    )

    col1, col2, col3, col4, col5 = st.columns(5, gap="small")

    with col1:
        st.info("Total Clients", icon="👥")
        st.metric(label="Clients uniques", value=numerize(float(total_customers)))

    with col2:
        st.info("Segments KMeans", icon="🔢")
        st.metric(label="Clusters", value=str(n_clusters))

    with col3:
        st.info("Panier Médian", icon="🛒")
        st.metric(label="Monetary BRL", value=f"{median_monetary:,.0f}")

    with col4:
        st.info("CLV Médian", icon="💰")
        st.metric(label="CLV proxy BRL", value=f"{median_clv:,.0f}")

    with col5:
        st.info("Satisfaction Moy.", icon="⭐")
        st.metric(label="Score /5", value=f"{avg_review:.2f}", help="Moyenne pondérée par segment")

    _apply_card_style()


def render_segment_kpi_row(profile_df: pd.DataFrame, cluster_id: int) -> None:
    """Renders 5 KPI metrics for a specific cluster (template 5-column pattern).

    Args:
        profile_df: Cluster profile DataFrame.
        cluster_id: Cluster label to display.
    """
    row = profile_df[profile_df["cluster"] == cluster_id]
    if row.empty:
        st.warning(f"Cluster {cluster_id} introuvable dans le profil.")
        return

    r = row.iloc[0]
    total = int(profile_df["n_customers"].sum())
    n = int(r.get("n_customers", 0))
    pct = float(r.get("pct_customers", n / total * 100 if total else 0))
    monetary = float(r.get("Monetary", 0))
    clv = float(r.get("CLV_proxy", 0))
    review = float(r.get("avg_review_score", 0))
    recency = float(r.get("Recency", 0))
    frequency = float(r.get("Frequency", 1))

    col1, col2, col3, col4, col5 = st.columns(5, gap="small")

    with col1:
        st.info("Taille Segment", icon="👥")
        st.metric(label="Clients", value=f"{n:,}", delta=f"{pct:.1f}% base")

    with col2:
        st.info("Panier Médian", icon="🛒")
        st.metric(label="Monetary BRL", value=f"{monetary:,.0f}")

    with col3:
        st.info("CLV Proxy", icon="💰")
        st.metric(label="Lifetime value", value=f"{clv:,.0f}")

    with col4:
        st.info("Satisfaction", icon="⭐")
        st.metric(label="Score /5", value=f"{review:.1f}")

    with col5:
        st.info("Récence", icon="📅")
        st.metric(label="Jours", value=f"{recency:.0f}", delta=f"Fréq. {frequency:.1f}x", delta_color="inverse")

    _apply_card_style()
