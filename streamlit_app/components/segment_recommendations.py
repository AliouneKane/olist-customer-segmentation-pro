"""Marketing segment names, personas and recommendations for the Olist dashboard.

Cluster profiles (UMAP+KMeans k=4, silhouette=0.4486) on 75 937 clients:

  C0  21 146 (28%) — Recency 124j, Monetary  64 BRL  → Acheteurs Budget  (récents, faible valeur)
  C1  18 775 (25%) — Recency 292j, Monetary  72 BRL  → Dormants Budget   (inactifs, faible valeur)
  C2  18 546 (24%) — Recency 131j, Monetary 180 BRL  → Acheteurs Premium (récents, valeur élevée)
  C3  17 470 (23%) — Recency 367j, Monetary 160 BRL  → Dormants Premium  (inactifs, valeur élevée)

Segmentation 2×2 : Récence (récent / inactif) × Montant (élevé / faible)
"""

from __future__ import annotations

SEGMENT_NAMES: dict[int, str] = {
    0: "Acheteurs Budget",
    1: "Dormants Budget",
    2: "Acheteurs Premium",
    3: "Dormants Premium",
}

SEGMENT_AVATARS: dict[int, str] = {
    0: "Client récent (~4 mois) mais économe : panier modeste (~64 BRL), première commande. Représente 28% de la base — cœur de volume à animer avec des promotions régulières et un programme de fidélité.",
    1: "Client inactif à faible valeur : panier modeste (~72 BRL) et inactif depuis ~10 mois. Le coût de réactivation risque de dépasser la valeur attendue — réserver les actions à bas coût uniquement.",
    2: "Client idéal : récent (~4 mois) et panier élevé (~180 BRL). C'est votre cœur de cible premium. Un suivi post-achat bien ciblé peut transformer ce premier achat en relation durable à forte valeur.",
    3: "Ancien client à valeur : panier élevé (~160 BRL) mais inactif depuis plus d'un an (367 jours). Ces clients ont déjà prouvé leur capacité à dépenser — une réactivation ciblée peut récupérer ce potentiel.",
}

RECOMMENDATIONS: dict[int, list[str]] = {
    0: [
        "Promotions flash hebdomadaires et offres 'prix bas garantis' sur les catégories populaires",
        "Programme de fidélité : accumuler des points sur chaque achat pour déclencher la récurrence",
        "Bundles économiques : regrouper des produits pour augmenter le panier sans changer le prix perçu",
        "Newsletter thématique 'meilleures affaires de la semaine' — fréquence bimensuelle",
    ],
    1: [
        "Campagne de réactivation à coût minimal uniquement (email automatisé, pas de remise élevée)",
        "Tester une offre symbolique (–5%) pour déclencher un retour sans sacrifier la marge",
        "Après 60 jours sans réaction : exclure définitivement des campagnes actives",
        "Analyser la cause de l'inactivité (mauvaise expérience produit ?) avant tout investissement",
    ],
    2: [
        "Email de nurturing à J+30 : remerciement + recommandations personnalisées basées sur le premier achat",
        "Offre de deuxième achat : –10% valable 45 jours pour créer l'habitude d'achat",
        "Cross-sell intelligent : proposer des catégories complémentaires à forte affinité",
        "Inviter à rejoindre le programme VIP — ces clients ont le potentiel de devenir Champions",
    ],
    3: [
        "Email de réactivation personnalisé : 'Vous nous manquez' + offre exclusive –20% valable 30 jours",
        "Rappeler leur dernier achat et proposer des produits complémentaires ou une mise à jour",
        "Offre dégressive : –15% à J+0, –20% à J+14, –25% à J+28 pour créer l'urgence",
        "Après 90 jours sans réaction : basculer vers canal SMS ou exclure pour préserver le budget CRM",
    ],
}

# Bootstrap color names (used by the legacy Dash build if ever reactivated)
SEGMENT_COLORS: dict[int, str] = {
    0: "warning",    # Acheteurs Budget  — amber
    1: "secondary",  # Dormants Budget   — gray
    2: "primary",    # Acheteurs Premium — blue
    3: "info",       # Dormants Premium  — teal
}

# Bootstrap Icons identifiers
SEGMENT_ICONS: dict[int, str] = {
    0: "bi-cart",
    1: "bi-hourglass",
    2: "bi-star",
    3: "bi-moon-stars",
}


def get_segment_name(cluster_id: int) -> str:
    """Returns the human-readable name for a cluster."""
    return SEGMENT_NAMES.get(cluster_id, f"Cluster {cluster_id}")


def get_recommendation_card(cluster_id: int):  # type: ignore[return]
    """Builds a Bootstrap card with avatar description + marketing bullet points."""
    try:
        import dash_bootstrap_components as dbc
        from dash import html
    except ImportError:
        return None

    name   = get_segment_name(cluster_id)
    avatar = SEGMENT_AVATARS.get(cluster_id, "")
    recs   = RECOMMENDATIONS.get(cluster_id, ["Analyser le profil avant de définir une stratégie."])
    color  = SEGMENT_COLORS.get(cluster_id, "secondary")
    icon   = SEGMENT_ICONS.get(cluster_id, "bi-person")

    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [html.I(className=f"bi {icon} me-2"), f"Stratégie — {name}"],
                    className="mb-0",
                ),
                className=f"bg-{color} text-white",
            ),
            dbc.CardBody(
                [
                    dbc.Alert(
                        [html.I(className="bi bi-person-circle me-2"), html.Em(avatar)],
                        color="light",
                        className="py-2 mb-3 border",
                    ),
                    html.H6("Actions marketing :", className="fw-semibold"),
                    html.Ul(
                        [html.Li(rec, className="mb-2") for rec in recs],
                        className="ps-3 mb-0",
                    ),
                ]
            ),
        ],
        className="shadow-sm mt-3",
    )
