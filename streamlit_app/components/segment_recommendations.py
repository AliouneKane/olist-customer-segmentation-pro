"""Marketing segment names, personas and recommendations for the Olist dashboard.

Cluster profiles (KMeans k=4, silhouette=0.3792) observed on 75 937 clients
after IQR filtering on Recency and Monetary:

  C0  22 716 (30%) — Recency 390j, Monetary 103 BRL, freq=1   → Dormants
  C1   2 133  (3%) — Recency 204j, Monetary 209 BRL, freq=2   → Champions
  C2  25 347 (33%) — Recency 161j, Monetary 181 BRL, freq=1   → Acheteurs Premium
  C3  25 741 (34%) — Recency 161j, Monetary  64 BRL, freq=1   → Acheteurs Budget
"""

from __future__ import annotations

SEGMENT_NAMES: dict[int, str] = {
    0: "Dormants",
    1: "Champions",
    2: "Acheteurs Premium",
    3: "Acheteurs Budget",
}

SEGMENT_AVATARS: dict[int, str] = {
    0: "Client perdu de vue : dernier achat il y a plus d'un an (390 jours en médiane). Panier modeste (~103 BRL), acheteur unique. Sans réactivation, ces clients quitteront définitivement la plateforme.",
    1: "Client le plus précieux : acheteur fidèle (2 commandes en médiane), CLV de 418 BRL — 4× la moyenne. Satisfait (note 5/5), livraison souvent en avance. Moteur de croissance à chouchouter en priorité.",
    2: "Acheteur récent et engagé : commande passée il y a ~5 mois, panier élevé (~181 BRL). Une seule commande à ce stade — fort potentiel de repeat si l'expérience a été positive.",
    3: "Acheteur récent mais économe : commande passée il y a ~5 mois, panier modeste (~64 BRL). Représente 34% de la base — segment de volume à animer avec des promotions ciblées.",
}

RECOMMENDATIONS: dict[int, list[str]] = {
    0: [
        "Campagne de réactivation urgente : offre exclusive (–20%) valable 30 jours pour les inactifs > 12 mois",
        "Email de 'vous nous manquez' personnalisé avec les catégories déjà achetées",
        "Tester une promotion choc sur le panier minimum pour déclencher un premier re-achat",
        "Après 90 jours sans réaction : exclure des campagnes pour ne pas gaspiller le budget CRM",
    ],
    1: [
        "Accès VIP : ventes privées, avant-premières et coupons exclusifs réservés aux Champions",
        "Programme d'ambassadeurs : inviter à laisser des avis et parrainer de nouveaux clients",
        "Upgrade de livraison surpris ou cadeau sur le prochain achat pour renforcer l'attachement",
        "Contact régulier : ne jamais dépasser 60 jours sans interaction — ces clients partent en silence",
    ],
    2: [
        "Email post-achat à J+30 avec recommandations personnalisées basées sur la première commande",
        "Offre de deuxième achat : réduction dégressif (–10% à J+45, –15% à J+60) pour créer l'habitude",
        "Cross-sell intelligent : proposer des catégories complémentaires à l'achat déjà réalisé",
        "Programme fidélité : expliquer les avantages dès le premier achat pour construire la relation",
    ],
    3: [
        "Mettre en avant les offres 'prix bas garantis' et les promotions flash hebdomadaires",
        "Newsletter thématique 'meilleures affaires de la semaine' adaptée à leur budget",
        "Bundles économiques : regrouper des produits pour augmenter le panier moyen sans changer le prix perçu",
        "Programme de parrainage : ce segment représente 34% de la base — fort potentiel bouche-à-oreille",
    ],
}

# Bootstrap color names (used by the legacy Dash build if ever reactivated)
SEGMENT_COLORS: dict[int, str] = {
    0: "secondary",
    1: "success",
    2: "primary",
    3: "warning",
}

# Bootstrap Icons identifiers
SEGMENT_ICONS: dict[int, str] = {
    0: "bi-moon-stars",
    1: "bi-trophy",
    2: "bi-star",
    3: "bi-cart",
}


def get_segment_name(cluster_id: int) -> str:
    """Returns the human-readable name for a cluster."""
    return SEGMENT_NAMES.get(cluster_id, f"Cluster {cluster_id}")


def get_recommendation_card(cluster_id: int):  # type: ignore[return]
    """Builds a Bootstrap card with avatar description + marketing bullet points.

    Returns a dbc.Card if dash_bootstrap_components is available, else None.
    """
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
