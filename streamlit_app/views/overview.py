"""Overview page — storytelling intro + distribution + comparisons."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from streamlit_app.components.charts import (
    bar_segment_comparison,
    heatmap_cluster_features,
    pie_segment_distribution,
)
from streamlit_app.components.data_store import load_cluster_profile
from streamlit_app.components.kpi_cards import render_global_kpi_row
from streamlit_app.styles import (
    OLIST_BLUE,
    OLIST_YELLOW,
    SEGMENT_COLORS,
    apply_olist_theme,
)

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


def _story_card(icon: str, title: str, body: str, color: str = OLIST_BLUE) -> None:
    st.markdown(
        f"""
        <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                    border-top:4px solid {color}; border-radius:10px;
                    padding:1.1rem 1.25rem; box-shadow:0 1px 4px #e5e7eb;
                    height:100%;">
            <div style="font-size:1.5rem; margin-bottom:6px;">{icon}</div>
            <div style="font-size:0.9rem; font-weight:700;
                        color:{color}; margin-bottom:6px;">{title}</div>
            <div style="font-size:0.83rem; color:#4b5563; line-height:1.65;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    try:
        profile_df = load_cluster_profile()
    except FileNotFoundError as exc:
        st.error(str(exc))
        return

    # 1. STORYTELLING — Contexte métier (avant tout graphique)
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg, {OLIST_BLUE} 0%, #0033cc 100%);
                    border-radius:14px; padding:2rem 2.5rem; margin-bottom:1.5rem;
                    color:#FFFFFF;">
            <div style="font-size:0.75rem; color:rgba(255,255,255,0.6);
                        text-transform:uppercase; letter-spacing:0.1em;
                        margin-bottom:6px;">Segmentation Client — Olist Brasil</div>
            <h1 style="color:#FFFFFF; font-size:1.8rem; font-weight:800;
                       margin:0 0 10px 0; line-height:1.2;">
                Qui sont vos clients,<br>et comment les activer ?
            </h1>
            <p style="color:rgba(255,255,255,0.85); font-size:0.95rem;
                      max-width:620px; line-height:1.7; margin:0;">
                Sur 75 937 acheteurs Olist (après nettoyage IQR), <strong>4 profils distincts</strong>
                ont été identifiés par machine learning (UMAP + KMeans). Ce dashboard transforme
                ces profils en <strong>stratégies marketing actionnables</strong> — chaque
                segment a sa propre logique d'achat, ses leviers et ses risques.
            </p>
            <div style="margin-top:14px; display:flex; gap:12px; flex-wrap:wrap;">
                <span style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.3);
                              border-radius:20px; padding:4px 14px; font-size:0.78rem;
                              color:#FFFFFF;">75 937 clients</span>
                <span style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.3);
                              border-radius:20px; padding:4px 14px; font-size:0.78rem;
                              color:#FFFFFF;">4 segments UMAP+KMeans</span>
                <span style="background:rgba(240,255,0,0.25); border:1px solid rgba(240,255,0,0.5);
                              border-radius:20px; padding:4px 14px; font-size:0.78rem;
                              color:{OLIST_YELLOW};">Silhouette 0.449 ✓</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3 messages-clés
    st.markdown(
        "<h3 style='color:#374151; font-size:1rem; font-weight:700;"
        " margin-bottom:0.75rem;'>Insights Clés — Ce que révèle la segmentation</h3>",
        unsafe_allow_html=True,
    )
    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1:
        _story_card(
            "C2",
            "24 % — Cible premium à convertir",
            "Les <strong>Acheteurs Premium</strong> (C2) ont commandé il y a ~4 mois avec "
            "un panier de <strong>180 BRL</strong>. Beauté haut de gamme, tech, mode. "
            "Un email de nurturing à J+30 peut doubler leur CLV.",
            color=SEGMENT_COLORS[2],
        )
    with k2:
        _story_card(
            "C3",
            "23 % — Dormants à fort potentiel",
            "Les <strong>Dormants Premium</strong> (C3) ont dépensé ~160 BRL mais sont "
            "inactifs depuis <strong>367 jours</strong>. Électronique, mobilier, bijoux. "
            "Une offre exclusive –20 % peut les ramener avant la perte définitive.",
            color=SEGMENT_COLORS[3],
        )
    with k3:
        _story_card(
            "C0",
            "28 % — Volume et récurrence à activer",
            "Les <strong>Acheteurs Budget</strong> (C0) sont récents (~4 mois) mais économes "
            "(panier ~64 BRL). Beauté, maison, enfants. <strong>Premier groupe de la base</strong> "
            "— des promotions hebdomadaires augmentent la fréquence d'achat.",
            color=SEGMENT_COLORS[0],
        )
    with k4:
        _story_card(
            "C1",
            "25 % — Dormants à relancer prudemment",
            "Les <strong>Dormants Budget</strong> (C1) sont inactifs depuis ~292 jours "
            "et dépensaient peu (~72 BRL). Nordeste et Norte. "
            "<strong>ROI faible</strong> — un simple email automatisé suffit, sans remise élevée.",
            color=SEGMENT_COLORS[1],
        )

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # 2. KPIs GLOBAUX
    st.markdown(
        f"<h3 style='color:{OLIST_BLUE}; margin-bottom:0.75rem;'>"
        "Indicateurs Globaux</h3>",
        unsafe_allow_html=True,
    )
    render_global_kpi_row(profile_df)
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # 3. DISTRIBUTION + HEATMAP
    st.markdown(
        f"<h3 style='color:{OLIST_BLUE}; margin-bottom:0.3rem;'>"
        "Répartition de la Base Client</h3>"
        "<p style='color:#6b7280; font-size:0.85rem; margin-bottom:0.75rem;'>"
        "Le camembert montre le <em>poids</em> de chaque segment. "
        "La heatmap révèle les <em>différences comportementales</em> — "
        "une cellule verte = score élevé, rouge = score faible.</p>",
        unsafe_allow_html=True,
    )
    col_left, col_right = st.columns([1, 1], gap="medium")
    with col_left:
        fig = pie_segment_distribution(profile_df)
        apply_olist_theme(fig, height=420)
        st.plotly_chart(fig, use_container_width=True)
    with col_right:
        heatmap_cols = [c for c in _HEATMAP_FEATURES if c in profile_df.columns]
        fig = heatmap_cluster_features(profile_df, heatmap_cols)
        apply_olist_theme(fig, height=420)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # 4. COMPARAISONS PAR MÉTRIQUE
    st.markdown(
        f"<h3 style='color:{OLIST_BLUE}; margin-bottom:0.3rem;'>"
        "Comparaison par Métrique</h3>"
        "<p style='color:#6b7280; font-size:0.85rem; margin-bottom:0.75rem;'>"
        "Chaque barre représente la <em>valeur médiane</em> du segment. "
        "Comparez la hauteur des barres pour identifier qui dépense le plus, "
        "qui est le plus récent, qui paie le plus de frais de port.</p>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        fig = bar_segment_comparison(profile_df, "Monetary")
        apply_olist_theme(fig, height=320)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        if "CLV_proxy" in profile_df.columns:
            fig = bar_segment_comparison(profile_df, "CLV_proxy")
            apply_olist_theme(fig, height=320)
            st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2, gap="medium")
    with col3:
        if "Recency" in profile_df.columns:
            fig = bar_segment_comparison(profile_df, "Recency")
            apply_olist_theme(fig, height=320)
            st.plotly_chart(fig, use_container_width=True)
    with col4:
        if "avg_freight_ratio" in profile_df.columns:
            fig = bar_segment_comparison(profile_df, "avg_freight_ratio")
            apply_olist_theme(fig, height=320)
            st.plotly_chart(fig, use_container_width=True)

    # Données brutes
    with st.expander("VOIR LE TABLEAU COMPLET DES PROFILS"):
        cols_filter = st.multiselect(
            "Colonnes :",
            options=profile_df.columns.tolist(),
            default=[
                "cluster",
                "n_customers",
                "pct_customers",
                "Monetary",
                "Recency",
                "avg_review_score",
                "CLV_proxy",
            ],
        )
        if cols_filter:
            st.dataframe(
                profile_df[cols_filter], use_container_width=True, hide_index=True
            )
