"""Prediction page — classify new customers into segments via CSV/Excel upload.

The marketing team uploads a file with new customer data (post-campaign).
The page applies the same feature engineering as training, scales with the
saved StandardScaler, and assigns each customer to the nearest cluster
centroid (equivalent to KMeans assignment in the 9-feature scaled space).

Results show the cluster distribution of new arrivals vs the historical
baseline, enabling the team to judge which campaigns are working.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from streamlit_app.components.segment_recommendations import (
    RECOMMENDATIONS,
    SEGMENT_ICONS,
    SEGMENT_NAMES,
    SEGMENT_TOP_CATEGORIES,
)
from streamlit_app.styles import OLIST_BLUE, OLIST_YELLOW, SEGMENT_COLORS, apply_olist_theme

_MODELS_DIR = _PROJECT_ROOT / "models"
_PROCESSED = _PROJECT_ROOT / "data" / "processed"

_FINAL_FEATURES: list[str] = [
    "Log_Recency",
    "Log_Monetary",
    "Frequency_flag",
    "avg_freight_ratio",
    "avg_delivery_delay",
    "avg_review_score",
    "payment_type_cc_flag",
    "avg_installments",
    "region_freight_score",
]

_REQUIRED_INPUT: list[str] = [
    "Recency",
    "Monetary",
    "Frequency",
    "avg_review_score",
    "avg_freight_ratio",
    "avg_delivery_delay",
    "avg_installments",
]

_STATE_REGION: dict[str, str] = {
    "AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste", "DF": "Centro-Oeste", "GO": "Centro-Oeste",
    "MS": "Centro-Oeste", "MT": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

_REGION_SCORE: dict[str, int] = {
    "Sul": 1, "Sudeste": 2, "Centro-Oeste": 3, "Nordeste": 4, "Norte": 5,
}

_ICON_MAP: dict[str, str] = {
    "bi-cart": "🛒", "bi-hourglass": "⏳", "bi-star": "⭐", "bi-moon-stars": "🌙",
}


@st.cache_resource(show_spinner=False)
def _load_predictor() -> tuple | None:
    """Load scaler and compute per-cluster centroids from training data."""
    try:
        import joblib

        scaler_path = _MODELS_DIR / "standard_scaler.pkl"
        labeled_path = _PROCESSED / "customer_features_labeled.parquet"

        if not scaler_path.exists():
            return None
        if not labeled_path.exists():
            return None

        scaler = joblib.load(scaler_path)
        labeled = pd.read_parquet(labeled_path)

        X = labeled[_FINAL_FEATURES].values
        X_scaled = scaler.transform(X)
        cluster_ids = sorted(labeled["cluster"].unique())

        centroids = np.array(
            [X_scaled[labeled["cluster"].values == c].mean(axis=0) for c in cluster_ids]
        )

        baseline_pct = (
            labeled["cluster"].value_counts(normalize=True).sort_index()
        )

        return scaler, centroids, cluster_ids, baseline_pct

    except Exception as exc:
        st.warning(f"Erreur chargement modèle : {exc}")
        return None


def _engineer_features(df: pd.DataFrame) -> pd.DataFrame | None:
    """Apply the same feature engineering as training pipeline."""
    missing = [c for c in _REQUIRED_INPUT if c not in df.columns]
    if missing:
        st.error(
            f"Colonnes manquantes dans le fichier : **{', '.join(missing)}**\n\n"
            "Téléchargez le modèle CSV ci-dessus pour voir le format attendu."
        )
        return None

    out = df.copy()

    out["Log_Recency"] = np.log1p(out["Recency"].clip(lower=0))
    out["Log_Monetary"] = np.log1p(out["Monetary"].clip(lower=0))
    out["Frequency_flag"] = (out["Frequency"] >= 2).astype(int)

    if "payment_type_cc_flag" not in out.columns:
        if "payment_type" in out.columns:
            out["payment_type_cc_flag"] = (
                out["payment_type"].str.lower() == "credit_card"
            ).astype(int)
        else:
            out["payment_type_cc_flag"] = 0

    if "region_freight_score" not in out.columns:
        if "customer_state" in out.columns:
            region = out["customer_state"].str.upper().map(_STATE_REGION)
            out["region_freight_score"] = region.map(_REGION_SCORE).fillna(3).astype(int)
        else:
            out["region_freight_score"] = 3

    out["avg_freight_ratio"] = out["avg_freight_ratio"].clip(0.0, 2.0)
    out["avg_delivery_delay"] = out["avg_delivery_delay"].clip(-30.0, 60.0)
    out["avg_installments"] = out["avg_installments"].clip(1.0, 12.0)

    fill_defaults: dict[str, float] = {
        "avg_freight_ratio": 0.15,
        "avg_delivery_delay": 0.0,
        "avg_review_score": 4.0,
        "payment_type_cc_flag": 0,
        "avg_installments": 1.5,
        "region_freight_score": 3,
        "Log_Recency": 0.0,
        "Log_Monetary": 0.0,
        "Frequency_flag": 0,
    }
    for col, val in fill_defaults.items():
        if col in out.columns:
            out[col] = out[col].fillna(val)

    return out


def _predict_clusters(df_engineered: pd.DataFrame) -> pd.Series | None:
    """Scale and assign each row to nearest cluster centroid."""
    from scipy.spatial.distance import cdist

    result = _load_predictor()
    if result is None:
        st.error(
            "Impossible de charger le modèle. "
            "Vérifiez que `models/standard_scaler.pkl` et "
            "`data/processed/customer_features_labeled.parquet` existent."
        )
        return None

    scaler, centroids, cluster_ids, _ = result

    X = df_engineered[_FINAL_FEATURES].values
    X_scaled = scaler.transform(X)
    distances = cdist(X_scaled, centroids, metric="euclidean")
    labels = distances.argmin(axis=1)

    return pd.Series(labels, index=df_engineered.index, name="cluster")


def _pie_chart(counts: pd.Series, title: str) -> go.Figure:
    labels = [f"C{c} — {SEGMENT_NAMES.get(c, str(c))}" for c in counts.index]
    colors = [SEGMENT_COLORS[c % len(SEGMENT_COLORS)] for c in counts.index]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=counts.values,
            hole=0.42,
            marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
            textinfo="label+percent",
            textfont=dict(size=11),
            sort=False,
        )
    )
    fig.update_layout(title_text=title, title_x=0, showlegend=False)
    apply_olist_theme(fig, height=340)
    return fig


def _comparison_bar(new_pct: pd.Series, base_pct: pd.Series) -> go.Figure:
    clusters = sorted(set(new_pct.index) | set(base_pct.index))
    names = [f"C{c} — {SEGMENT_NAMES.get(c, str(c))}" for c in clusters]
    colors = [SEGMENT_COLORS[c % len(SEGMENT_COLORS)] for c in clusters]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Nouveaux clients",
            x=names,
            y=[new_pct.get(c, 0) * 100 for c in clusters],
            marker_color=colors,
            marker_opacity=0.9,
        )
    )
    fig.add_trace(
        go.Bar(
            name="Base historique (référence)",
            x=names,
            y=[base_pct.get(c, 0) * 100 for c in clusters],
            marker_color=colors,
            marker_opacity=0.30,
            marker_pattern_shape="/",
        )
    )
    fig.update_layout(
        barmode="group",
        yaxis_title="% de clients",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    apply_olist_theme(fig, height=340)
    return fig


def _insight_card(cluster_id: int, new_pct: float, base_pct: float) -> None:
    color = SEGMENT_COLORS[cluster_id % len(SEGMENT_COLORS)]
    name = SEGMENT_NAMES.get(cluster_id, f"Cluster {cluster_id}")
    icon_key = SEGMENT_ICONS.get(cluster_id, "")
    icon = _ICON_MAP.get(icon_key, "👤")
    delta = new_pct - base_pct
    delta_str = f"+{delta:.1f} pts" if delta >= 0 else f"{delta:.1f} pts"
    delta_color = "#16a34a" if delta >= 0 else "#dc2626"

    cats = SEGMENT_TOP_CATEGORIES.get(cluster_id, [])
    cat_tags = "".join(
        f"<span style='display:inline-block; background:{color}15; color:{color}; "
        f"border:1px solid {color}40; border-radius:20px; padding:1px 8px; "
        f"font-size:0.72rem; font-weight:600; margin:2px 3px 2px 0;'>{c}</span>"
        for c in cats
    )

    recs = RECOMMENDATIONS.get(cluster_id, [])
    rec_html = "".join(
        f"<li style='margin-bottom:5px; font-size:0.78rem; color:#374151; line-height:1.5;'>{r}</li>"
        for r in recs[:2]
    )

    st.markdown(
        f"""
        <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                    border-top:4px solid {color}; border-radius:8px;
                    padding:0.9rem 1.1rem; margin-bottom:0.75rem;
                    box-shadow:0 1px 3px #f3f4f6;">
            <div style="display:flex; justify-content:space-between;
                        align-items:center; margin-bottom:8px;">
                <div style="font-size:0.9rem; font-weight:700; color:{color};">
                    {icon} {name}
                </div>
                <div>
                    <span style="font-size:1rem; font-weight:800;
                                 color:#1f2937;">{new_pct:.1f}%</span>
                    <span style="font-size:0.78rem; color:{delta_color};
                                 font-weight:700; margin-left:6px;">{delta_str} vs base</span>
                </div>
            </div>
            <div style="margin-bottom:8px;">{cat_tags}</div>
            <div style="font-size:0.68rem; color:#9ca3af; text-transform:uppercase;
                        letter-spacing:0.07em; margin-bottom:5px;">Actions à prioriser</div>
            <ul style="padding-left:1rem; margin:0;">{rec_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _csv_template() -> bytes:
    template = pd.DataFrame(
        {
            "customer_id": ["CLIENT_001", "CLIENT_002", "CLIENT_003", "CLIENT_004", "CLIENT_005"],
            "Recency": [30, 120, 250, 45, 310],
            "Monetary": [185.0, 68.0, 155.0, 72.0, 200.0],
            "Frequency": [1, 1, 2, 1, 1],
            "avg_review_score": [4.5, 4.0, 3.5, 3.0, 4.8],
            "avg_freight_ratio": [0.12, 0.28, 0.18, 0.35, 0.10],
            "avg_delivery_delay": [-2.0, 1.5, 3.0, 0.0, -5.0],
            "avg_installments": [2.0, 1.0, 3.0, 1.0, 4.0],
            "payment_type": ["credit_card", "boleto", "credit_card", "boleto", "credit_card"],
            "customer_state": ["SP", "BA", "RJ", "CE", "SC"],
        }
    )
    return template.to_csv(index=False).encode("utf-8")


def render() -> None:
    """Renders the new-customer prediction and campaign analysis page."""

    # ── Hero ────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,{OLIST_BLUE} 0%,#0033cc 100%);
                    border-radius:14px; padding:1.75rem 2.25rem; margin-bottom:1.5rem;">
            <div style="font-size:0.7rem; color:rgba(255,255,255,0.55);
                        text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px;">
                Analyse des Campagnes Marketing
            </div>
            <h1 style="color:#FFFFFF; font-size:1.6rem; font-weight:800; margin:0 0 8px 0;">
                🎯 Prédiction Nouveaux Clients
            </h1>
            <p style="color:rgba(255,255,255,0.85); font-size:0.9rem;
                      max-width:640px; line-height:1.7; margin:0 0 12px 0;">
                Importez un fichier avec les données de vos nouveaux clients pour savoir
                à quel segment ils appartiennent. Si une campagne a bien fonctionné,
                vous verrez une majorité de nouveaux clients dans le segment ciblé.
            </p>
            <div style="display:flex; gap:10px; flex-wrap:wrap;">
                <span style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.3);
                              border-radius:20px; padding:3px 12px; font-size:0.75rem;
                              color:#FFFFFF;">CSV ou Excel</span>
                <span style="background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.3);
                              border-radius:20px; padding:3px 12px; font-size:0.75rem;
                              color:#FFFFFF;">Modèle KMeans k=4 · Sil. 0.449</span>
                <span style="background:rgba(240,255,0,0.25); border:1px solid rgba(240,255,0,0.5);
                              border-radius:20px; padding:3px 12px; font-size:0.75rem;
                              color:{OLIST_YELLOW};">Nearest-centroid — sans UMAP requis</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Template download ────────────────────────────────────────────────────
    col_info, col_dl = st.columns([3, 1], gap="medium")
    with col_info:
        st.markdown(
            f"""
            <div style="background:#f0f4ff; border:1px solid #c7d7fe;
                        border-radius:10px; padding:1rem 1.2rem;">
                <div style="font-size:0.88rem; font-weight:700; color:{OLIST_BLUE};
                            margin-bottom:8px;">Colonnes attendues dans votre fichier</div>
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;
                            font-size:0.8rem; color:#374151;">
                    <div>
                        <strong>Obligatoires</strong><br>
                        • <code>Recency</code> — jours depuis dernier achat<br>
                        • <code>Monetary</code> — panier total (BRL)<br>
                        • <code>Frequency</code> — nb de commandes<br>
                        • <code>avg_review_score</code> — note (1–5)<br>
                        • <code>avg_freight_ratio</code> — fret/panier<br>
                        • <code>avg_delivery_delay</code> — délai (jours)<br>
                        • <code>avg_installments</code> — nb versements
                    </div>
                    <div>
                        <strong>Optionnelles</strong><br>
                        • <code>payment_type</code> —<br>
                          <em>'credit_card'</em> ou <em>'boleto'</em><br>
                        • <code>customer_state</code> —<br>
                          code état brésilien (ex. SP, BA)<br>
                        • <code>customer_id</code> — identifiant libre
                    </div>
                    <div>
                        <strong>Remarques</strong><br>
                        Si <code>payment_type</code> absent → boleto par défaut<br>
                        Si <code>customer_state</code> absent → Centro-Oeste par défaut<br>
                        Valeurs nulles → imputées avec la médiane d'entraînement
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_dl:
        st.markdown("<div style='margin-top:0.4rem;'></div>", unsafe_allow_html=True)
        st.download_button(
            label="⬇️ Télécharger le modèle CSV",
            data=_csv_template(),
            file_name="modele_nouveaux_clients.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)

    # ── File uploader ────────────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Importer le fichier des nouveaux clients",
        type=["csv", "xlsx", "xls"],
        help="Fichier CSV ou Excel. Colonnes obligatoires : Recency, Monetary, Frequency, "
        "avg_review_score, avg_freight_ratio, avg_delivery_delay, avg_installments.",
    )

    if uploaded is None:
        st.markdown(
            f"""
            <div style="text-align:center; padding:3rem 1rem; color:#9ca3af;
                        border:2px dashed #e5e7eb; border-radius:12px; margin-top:1rem;">
                <div style="font-size:2.5rem; margin-bottom:8px;">📂</div>
                <div style="font-size:0.95rem; font-weight:600;">
                    Aucun fichier importé
                </div>
                <div style="font-size:0.82rem; margin-top:4px;">
                    Déposez un CSV ou Excel contenant les données de vos nouveaux clients
                    (résultats d'une campagne marketing).
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # ── Load file ────────────────────────────────────────────────────────────
    try:
        if uploaded.name.endswith((".xlsx", ".xls")):
            df_raw = pd.read_excel(uploaded)
        else:
            df_raw = pd.read_csv(uploaded)
    except Exception as exc:
        st.error(f"Impossible de lire le fichier : {exc}")
        return

    if df_raw.empty:
        st.warning("Le fichier est vide.")
        return

    st.markdown(
        f"<p style='color:#6b7280; font-size:0.85rem;'>"
        f"✅ Fichier chargé — <strong>{len(df_raw):,} clients</strong>, "
        f"{df_raw.shape[1]} colonnes.</p>",
        unsafe_allow_html=True,
    )

    with st.expander("Aperçu des données importées (5 premières lignes)"):
        st.dataframe(df_raw.head(), use_container_width=True, hide_index=True)

    # ── Feature engineering + prediction ────────────────────────────────────
    with st.spinner("Préparation des features et prédiction en cours…"):
        df_eng = _engineer_features(df_raw)
        if df_eng is None:
            return

        labels = _predict_clusters(df_eng)
        if labels is None:
            return

    df_result = df_raw.copy()
    df_result["cluster"] = labels.values
    df_result["segment"] = df_result["cluster"].map(SEGMENT_NAMES)

    # ── Chiffres clés ────────────────────────────────────────────────────────
    n_total = len(df_result)
    mask_premium = df_result["cluster"].isin([2, 3])
    mask_budget = ~mask_premium

    n_premium = int(mask_premium.sum())
    n_budget = int(mask_budget.sum())
    pct_premium = n_premium / n_total * 100
    pct_budget = n_budget / n_total * 100

    avg_prem = float(df_result.loc[mask_premium, "Monetary"].mean()) if n_premium > 0 else 0.0
    avg_bud = float(df_result.loc[mask_budget, "Monetary"].mean()) if n_budget > 0 else 0.0
    rev_prem = float(df_result.loc[mask_premium, "Monetary"].sum()) if n_premium > 0 else 0.0
    rev_bud = float(df_result.loc[mask_budget, "Monetary"].sum()) if n_budget > 0 else 0.0
    rev_total = rev_prem + rev_bud

    _C_PREM = SEGMENT_COLORS[2]
    _C_BUD = SEGMENT_COLORS[0]

    st.success(f"Analyse terminée — {n_total:,} clients traités.")
    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    # BLOC 1 — CE QU'ON A TROUVÉ
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"<div style='font-size:1.1rem; font-weight:800; color:{OLIST_BLUE};"
        " margin-bottom:1rem;'>📊 Bloc 1 — Ce qu'on a trouvé</div>",
        unsafe_allow_html=True,
    )

    # Barre Budget / Premium
    st.markdown(
        f"""
        <div style="margin-bottom:1.25rem;">
            <div style="display:flex; justify-content:space-between;
                        font-size:0.82rem; font-weight:700; margin-bottom:6px;">
                <span style="color:{_C_BUD};">🛒 Profil Budget — {pct_budget:.0f}%
                    &nbsp;({n_budget:,} clients)</span>
                <span style="color:{_C_PREM};">⭐ Profil Premium — {pct_premium:.0f}%
                    &nbsp;({n_premium:,} clients)</span>
            </div>
            <div style="display:flex; height:20px; border-radius:10px;
                        overflow:hidden; box-shadow:0 1px 4px #e5e7eb;">
                <div style="width:{pct_budget:.1f}%; background:{_C_BUD};"></div>
                <div style="width:{pct_premium:.1f}%; background:{_C_PREM};"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Deux cartes chiffrées
    col_bud, col_prem = st.columns(2, gap="medium")

    with col_bud:
        st.markdown(
            f"""
            <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                        border-top:5px solid {_C_BUD}; border-radius:10px;
                        padding:1.1rem 1.25rem; box-shadow:0 1px 3px #f3f4f6;">
                <div style="font-size:0.7rem; color:#9ca3af; text-transform:uppercase;
                            letter-spacing:0.08em; margin-bottom:6px;">Profil Budget</div>
                <div style="font-size:2rem; font-weight:900;
                            color:{_C_BUD}; margin-bottom:2px;">{n_budget:,}</div>
                <div style="font-size:0.82rem; color:#6b7280;
                            margin-bottom:12px;">{pct_budget:.0f}% des nouveaux clients</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                    <div>
                        <div style="font-size:0.68rem; color:#9ca3af; text-transform:uppercase;
                                    letter-spacing:0.06em; margin-bottom:2px;">Panier moyen</div>
                        <div style="font-size:1.1rem; font-weight:800;
                                    color:#1f2937;">{avg_bud:.0f} BRL</div>
                    </div>
                    <div>
                        <div style="font-size:0.68rem; color:#9ca3af; text-transform:uppercase;
                                    letter-spacing:0.06em; margin-bottom:2px;">Revenue total</div>
                        <div style="font-size:1.1rem; font-weight:800;
                                    color:#1f2937;">{rev_bud:,.0f} BRL</div>
                    </div>
                </div>
                <div style="margin-top:10px; padding-top:10px; border-top:1px solid #f3f4f6;
                            font-size:0.78rem; color:#6b7280;">
                    Part du revenue total :
                    <strong style="color:{_C_BUD};">{rev_bud/rev_total*100:.0f}%</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_prem:
        st.markdown(
            f"""
            <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                        border-top:5px solid {_C_PREM}; border-radius:10px;
                        padding:1.1rem 1.25rem; box-shadow:0 1px 3px #f3f4f6;">
                <div style="font-size:0.7rem; color:#9ca3af; text-transform:uppercase;
                            letter-spacing:0.08em; margin-bottom:6px;">Profil Premium</div>
                <div style="font-size:2rem; font-weight:900;
                            color:{_C_PREM}; margin-bottom:2px;">{n_premium:,}</div>
                <div style="font-size:0.82rem; color:#6b7280;
                            margin-bottom:12px;">{pct_premium:.0f}% des nouveaux clients</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                    <div>
                        <div style="font-size:0.68rem; color:#9ca3af; text-transform:uppercase;
                                    letter-spacing:0.06em; margin-bottom:2px;">Panier moyen</div>
                        <div style="font-size:1.1rem; font-weight:800;
                                    color:#1f2937;">{avg_prem:.0f} BRL</div>
                    </div>
                    <div>
                        <div style="font-size:0.68rem; color:#9ca3af; text-transform:uppercase;
                                    letter-spacing:0.06em; margin-bottom:2px;">Revenue total</div>
                        <div style="font-size:1.1rem; font-weight:800;
                                    color:#1f2937;">{rev_prem:,.0f} BRL</div>
                    </div>
                </div>
                <div style="margin-top:10px; padding-top:10px; border-top:1px solid #f3f4f6;
                            font-size:0.78rem; color:#6b7280;">
                    Part du revenue total :
                    <strong style="color:{_C_PREM};">{rev_prem/rev_total*100:.0f}%</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Interprétation simple niveau 3e
    if pct_premium >= 60:
        verdict_color = "#16a34a"
        verdict_icon = "✅"
        verdict = (
            f"Vos campagnes ont bien marché. Sur {n_total} nouveaux clients, "
            f"{n_premium} ont dépensé en moyenne <strong>{avg_prem:.0f} BRL</strong> "
            f"et ont payé par carte de crédit. "
            f"Ces clients-là ont de la valeur — ils ressemblent à vos meilleurs acheteurs actuels. "
            f"Même s'ils sont moins nombreux que les autres, ils rapportent "
            f"<strong>{rev_prem/rev_total*100:.0f}% du revenue total</strong> de cette vague."
        )
    elif pct_budget >= 60:
        verdict_color = "#d97706"
        verdict_icon = "⚠️"
        verdict = (
            f"Vos campagnes ont attiré surtout des clients qui cherchaient la promo. "
            f"Sur {n_total} nouveaux clients, {n_budget} ont dépensé en moyenne "
            f"<strong>{avg_bud:.0f} BRL</strong> et ont payé par virement. "
            f"C'est bien pour le volume, mais ces clients reviendront moins facilement "
            f"si vous ne leur proposez pas une nouvelle promotion. "
            f"Les {n_premium} clients Premium que vous avez ramenés sont plus précieux "
            f"— ils rapportent déjà <strong>{rev_prem/rev_total*100:.0f}% du revenue</strong> "
            f"à eux seuls."
        )
    else:
        verdict_color = OLIST_BLUE
        verdict_icon = "📊"
        verdict = (
            f"Vos campagnes ont touché les deux types de clients. "
            f"{n_premium} clients ont un profil Premium (panier moyen <strong>{avg_prem:.0f} BRL</strong>) "
            f"et {n_budget} ont un profil Budget (panier moyen <strong>{avg_bud:.0f} BRL</strong>). "
            f"Les Premium sont moins nombreux mais génèrent "
            f"<strong>{rev_prem/rev_total*100:.0f}% du revenue total</strong>. "
            f"Le mois prochain, regardez si ce ratio s'améliore — plus de Premium = mieux ciblé."
        )

    st.markdown(
        f"""
        <div style="background:{verdict_color}0d; border-left:5px solid {verdict_color};
                    border-radius:0 10px 10px 0; padding:1rem 1.25rem; margin-top:1rem;">
            <div style="font-size:0.7rem; color:#9ca3af; text-transform:uppercase;
                        letter-spacing:0.08em; margin-bottom:6px;">Ce que ça veut dire</div>
            <div style="font-size:0.88rem; color:#1f2937; line-height:1.75;">
                {verdict_icon} {verdict}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # ════════════════════════════════════════════════════════════════════════
    # BLOC 2 — CE QU'ON FAIT MAINTENANT
    # ════════════════════════════════════════════════════════════════════════
    st.markdown(
        f"<div style='font-size:1.1rem; font-weight:800; color:{OLIST_BLUE};"
        " margin-bottom:1rem;'>🎯 Bloc 2 — Ce qu'on fait maintenant</div>",
        unsafe_allow_html=True,
    )

    col_act_prem, col_act_bud = st.columns(2, gap="medium")

    with col_act_prem:
        prem_steps = [
            f"Dans les <strong>30 prochains jours</strong>, envoyer un email "
            f"de remerciement aux {n_premium} clients Premium avec une offre "
            f"de <strong>–10% sur leur prochaine commande</strong>.",
            "Leur proposer des produits dans les mêmes catégories que leur premier "
            "achat : beauté haut de gamme, électronique, mode.",
            "Les inviter à rejoindre le <strong>programme fidélité VIP</strong> "
            "— ces clients ont le bon profil pour devenir des acheteurs réguliers.",
            "Si pas de rachat après 45 jours : relancer une dernière fois avec "
            "–15% puis arrêter les relances.",
        ]
        steps_html = "".join(
            f"""<div style="display:flex; gap:10px; margin-bottom:10px;">
                <div style="background:{_C_PREM}; color:#FFF; font-size:0.7rem;
                            font-weight:800; border-radius:50%; min-width:20px;
                            height:20px; display:flex; align-items:center;
                            justify-content:center; flex-shrink:0;
                            margin-top:1px;">{i+1}</div>
                <div style="font-size:0.82rem; color:#374151;
                            line-height:1.6;">{s}</div>
            </div>"""
            for i, s in enumerate(prem_steps)
        )
        st.markdown(
            f"""
            <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                        border-top:5px solid {_C_PREM}; border-radius:10px;
                        padding:1.1rem 1.25rem; box-shadow:0 1px 3px #f3f4f6;">
                <div style="font-size:0.88rem; font-weight:700; color:{_C_PREM};
                            margin-bottom:12px;">
                    ⭐ Pour les {n_premium} clients Premium
                </div>
                {steps_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_act_bud:
        bud_steps = [
            f"Ajouter les {n_budget} clients Budget à la liste "
            f"<strong>newsletter promo hebdomadaire</strong> — promotions flash, "
            f"meilleures affaires de la semaine.",
            "Ne pas investir dans un email personnalisé coûteux — "
            "un email promo générique suffit pour ce profil.",
            "Leur proposer des produits à petit prix dans leur catégorie : "
            "beauté entrée de gamme, articles maison, jouets en promotion.",
            "<strong>Si pas de rachat après 60 jours</strong> : arrêter "
            "les relances. Ne pas dépenser plus de budget marketing sur eux.",
        ]
        steps_html = "".join(
            f"""<div style="display:flex; gap:10px; margin-bottom:10px;">
                <div style="background:{_C_BUD}; color:#FFF; font-size:0.7rem;
                            font-weight:800; border-radius:50%; min-width:20px;
                            height:20px; display:flex; align-items:center;
                            justify-content:center; flex-shrink:0;
                            margin-top:1px;">{i+1}</div>
                <div style="font-size:0.82rem; color:#374151;
                            line-height:1.6;">{s}</div>
            </div>"""
            for i, s in enumerate(bud_steps)
        )
        st.markdown(
            f"""
            <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                        border-top:5px solid {_C_BUD}; border-radius:10px;
                        padding:1.1rem 1.25rem; box-shadow:0 1px 3px #f3f4f6;">
                <div style="font-size:0.88rem; font-weight:700; color:{_C_BUD};
                            margin-bottom:12px;">
                    🛒 Pour les {n_budget} clients Budget
                </div>
                {steps_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    # ── Téléchargements + tableau détail ─────────────────────────────────────
    col_dl1, col_dl2 = st.columns(2, gap="medium")
    with col_dl1:
        st.download_button(
            label="⬇️ Télécharger les résultats (CSV)",
            data=df_result.to_csv(index=False).encode("utf-8"),
            file_name="prediction_segments.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_dl2:
        summary = pd.DataFrame({
            "Profil": ["Premium (C2+C3)", "Budget (C0+C1)"],
            "Nb clients": [n_premium, n_budget],
            "% du total": [f"{pct_premium:.1f}%", f"{pct_budget:.1f}%"],
            "Panier moyen (BRL)": [f"{avg_prem:.0f}", f"{avg_bud:.0f}"],
            "Revenue total (BRL)": [f"{rev_prem:,.0f}", f"{rev_bud:,.0f}"],
            "% du revenue": [f"{rev_prem/rev_total*100:.0f}%", f"{rev_bud/rev_total*100:.0f}%"],
        })
        st.download_button(
            label="⬇️ Résumé Budget / Premium (CSV)",
            data=summary.to_csv(index=False).encode("utf-8"),
            file_name="resume_budget_premium.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with st.expander("📄 VOIR LE DÉTAIL CLIENT PAR CLIENT"):
        display_cols = [c for c in df_result.columns if c not in _FINAL_FEATURES]
        st.dataframe(df_result[display_cols], use_container_width=True, hide_index=True)
