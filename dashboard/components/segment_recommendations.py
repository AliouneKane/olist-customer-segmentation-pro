"""Marketing segment names and recommendations for the Olist dashboard.

Cluster IDs are integers assigned by the clustering algorithm. The names
and recommendations below are placeholders — update them once you have
interpreted the actual cluster profiles from notebooks/03_clustering.ipynb.

The naming convention follows the RFM-inspired framework commonly used in
e-commerce CRM (Champions, Loyal Customers, At-Risk, etc.).
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

# ── Segment naming ────────────────────────────────────────────────────────────
# Map cluster integer label → human-readable segment name
# Update keys and names to match actual clustering output.
SEGMENT_NAMES: dict[int, str] = {
    0: "Champions",
    1: "Clients Fidèles",
    2: "Clients à Risque",
    3: "Dormants",
    4: "Nouveaux Clients",
}

# ── Marketing recommendations ─────────────────────────────────────────────────
# 2–4 actionable bullet points per segment
RECOMMENDATIONS: dict[int, list[str]] = {
    0: [
        "Programme VIP exclusif : accès anticipé aux nouvelles catégories",
        "Récompenser la fidélité avec des remises sur le prochain panier",
        "Inviter à rejoindre le programme d'ambassadeurs / avis produits",
    ],
    1: [
        "Upsell vers des catégories complémentaires à l'historique d'achat",
        "Newsletter personnalisée basée sur le mode de paiement dominant",
        "Offres groupées (bundle) pour augmenter le ticket moyen",
    ],
    2: [
        "Campagne win-back : coupon de réduction à durée limitée",
        "Enquête satisfaction pour identifier les points de friction",
        "Email de relance personnalisé avec les produits les mieux notés",
    ],
    3: [
        "Campagne de réactivation : 'Vous nous manquez — 20% sur votre prochain achat'",
        "Ciblage via les canaux à faible coût (push notification, SMS)",
        "Évaluer le ROI : si inactif depuis > 18 mois, exclure des campagnes payantes",
    ],
    4: [
        "Onboarding e-mail : guide des meilleures catégories et vendeurs",
        "Offre de bienvenue conditionnelle (ex. : réduction si 2e achat < 30 jours)",
        "Enquête post-achat pour mieux segmenter dès la 2e commande",
    ],
}

# ── Color coding per segment ──────────────────────────────────────────────────
SEGMENT_COLORS: dict[int, str] = {
    0: "success",
    1: "primary",
    2: "warning",
    3: "danger",
    4: "info",
}


def get_segment_name(cluster_id: int) -> str:
    """Returns the human-readable name for a cluster, with a fallback.

    Args:
        cluster_id: Integer cluster label.

    Returns:
        Segment name string (e.g. "Champions") or "Cluster N" if not found.
    """
    return SEGMENT_NAMES.get(cluster_id, f"Cluster {cluster_id}")


def get_recommendation_card(cluster_id: int) -> dbc.Card:
    """Builds a Bootstrap card with the segment name and marketing bullet points.

    Args:
        cluster_id: Integer cluster label.

    Returns:
        dbc.Card component with segment name header and recommendation list.
    """
    name = get_segment_name(cluster_id)
    recs = RECOMMENDATIONS.get(cluster_id, ["Analyser le profil avant de définir une stratégie."])
    color = SEGMENT_COLORS.get(cluster_id, "secondary")

    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [html.I(className="bi bi-bullseye me-2"), f"Stratégie : {name}"],
                    className="mb-0",
                ),
                className=f"bg-{color} text-white",
            ),
            dbc.CardBody(
                html.Ul(
                    [html.Li(rec, className="mb-2") for rec in recs],
                    className="ps-3 mb-0",
                )
            ),
        ],
        className="shadow-sm mt-3",
    )
