"""Premium KPI metric row components for the Olist Segmentation Streamlit dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.styles import (
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_YELLOW,
    ACCENT_RED,
    SEGMENT_COLORS,
)


def _custom_kpi_card(
    label: str,
    value: str,
    subtitle: str = "",
    icon: str = "",
    color: str = ACCENT_BLUE,
    delta: str | None = None,
    delta_positive: bool = True,
) -> str:
    """Returns HTML string for a premium glassmorphism KPI card."""
    delta_html = ""
    if delta:
        arrow = "▲" if delta_positive else "▼"
        d_color = ACCENT_GREEN if delta_positive else ACCENT_RED
        delta_html = (
            f"<div style='font-size:0.75rem;font-weight:600;color:{d_color};"
            f"margin-top:4px;'>{arrow} {delta}</div>"
        )

    html = f"""<div style="background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 1.25rem 1.4rem; position: relative; overflow: hidden; box-shadow: 0px 4px 15px rgba(0, 0, 0, 0.03); height: 100%;">
    <div style="display:flex;align-items:flex-start;justify-content:space-between; margin-bottom:10px;">
        <div style="font-size:0.75rem;font-weight:600;color:#64748B; text-transform:uppercase;letter-spacing:0.05em;">{label}</div>
        <div style="font-size:1.4rem;">{icon}</div>
    </div>
    <div style="font-size:1.75rem;font-weight:800;color:#0F172A; letter-spacing:-0.02em;line-height:1.1;">{value}</div>
    {delta_html}
    <div style="font-size:0.75rem;color:#64748B;margin-top:5px;font-weight:500;">{subtitle}</div>
</div>"""
    return html.replace('\n', '')


def render_global_kpi_row(profile_df: pd.DataFrame) -> None:
    """Renders 4 global KPI metrics (all segments combined).

    Args:
        profile_df: Cluster profile DataFrame from load_cluster_profile().
    """
    total_customers = int(profile_df["n_customers"].sum())
    n_clusters = len(profile_df)
    median_clv = float(profile_df["CLV_proxy"].median()) if "CLV_proxy" in profile_df.columns else 0.0
    avg_review = float(profile_df["avg_review_score"].mean()) if "avg_review_score" in profile_df.columns else 0.0
    avg_monetary = float(profile_df["Monetary"].mean()) if "Monetary" in profile_df.columns else 0.0

    col1, col2, col3, col4 = st.columns(4, gap="medium")

    cards = [
        (
            col1,
            _custom_kpi_card(
                label="Total Clients",
                value=f"{total_customers:,}",
                subtitle="Clients uniques analysés",
                icon="👥",
                color=ACCENT_BLUE,
            ),
        ),
        (
            col2,
            _custom_kpi_card(
                label="Segments KMeans",
                value=str(n_clusters),
                subtitle="k=6 optimisé (silhouette=0.213)",
                icon="🎯",
                color="#8b5cf6",  # violet
            ),
        ),
        (
            col3,
            _custom_kpi_card(
                label="CLV Médian",
                value=f"{median_clv:.0f} BRL",
                subtitle=f"Panier moyen: {avg_monetary:.0f} BRL",
                icon="💰",
                color=ACCENT_GREEN,
            ),
        ),
        (
            col4,
            _custom_kpi_card(
                label="Satisfaction Moy.",
                value=f"{avg_review:.2f} / 5",
                subtitle="Note de satisfaction agrégée",
                icon="⭐",
                color=ACCENT_YELLOW,
                delta=f"{avg_review:.2f} sur 5 étoiles",
                delta_positive=avg_review >= 4.0,
            ),
        ),
    ]

    for col, html in cards:
        with col:
            st.markdown(html, unsafe_allow_html=True)


def render_segment_kpi_row(profile_df: pd.DataFrame, cluster_id: int) -> None:
    """Renders 4 KPI metrics for a specific cluster segment.

    Args:
        profile_df: Cluster profile DataFrame.
        cluster_id: Cluster label to display.
    """
    row = profile_df[profile_df["cluster"] == cluster_id]
    if row.empty:
        st.warning(f"Cluster {cluster_id} introuvable dans le profil.", icon="⚠️")
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

    color = SEGMENT_COLORS[cluster_id % len(SEGMENT_COLORS)]

    col1, col2, col3, col4 = st.columns(4, gap="medium")

    cards = [
        (
            col1,
            _custom_kpi_card(
                label="Clients · Part de marché",
                value=f"{n:,}",
                subtitle=f"{pct:.1f}% de la base totale",
                icon="👥",
                color=color,
                delta=f"{pct:.1f}% de la base",
                delta_positive=pct >= 15,
            ),
        ),
        (
            col2,
            _custom_kpi_card(
                label="Panier Médian",
                value=f"{monetary:.0f} BRL",
                subtitle=f"Fréquence: {frequency:.1f} cmd",
                icon="🛒",
                color=ACCENT_GREEN,
            ),
        ),
        (
            col3,
            _custom_kpi_card(
                label="CLV Proxy",
                value=f"{clv:.0f} BRL",
                subtitle="Monetary × Frequency estimé",
                icon="💎",
                color="#8b5cf6",
            ),
        ),
        (
            col4,
            _custom_kpi_card(
                label="Satisfaction · Récence",
                value=f"{review:.1f} / 5",
                subtitle=f"Dernier achat: {recency:.0f}j",
                icon="⭐",
                color=ACCENT_YELLOW if review >= 3.5 else ACCENT_RED,
                delta=f"Récence {recency:.0f}j",
                delta_positive=recency < 200,
            ),
        ),
    ]

    for col, html in cards:
        with col:
            st.markdown(html, unsafe_allow_html=True)
