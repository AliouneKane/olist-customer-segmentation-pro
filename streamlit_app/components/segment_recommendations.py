"""Marketing segment names, personas and recommendations for the Olist dashboard.

Cluster profiles (KMeans k=6, silhouette=0.2132) observed on 93 358 clients :

  C0  15 222 (16%) — Recency 244j, Monetary 231 BRL, 8 versements, CC    → Premium Crédit
  C1  18 238 (20%) — Recency 226j, Monetary 98 BRL, boleto, 1 versement  → Économes Boleto
  C2   8 651  (9%) — Recency 222j, Monetary 37 BRL, freight 84%          → Périphériques Contraints
  C3  38 000 (41%) — Recency 209j, Monetary 96 BRL, CC, 2 versements     → Mainstream
  C4   2 801  (3%) — Recency 198j, Monetary 238 BRL, freq=2, CLV 476     → Champions
  C5  10 446 (11%) — Recency 205j, review=1.0, livraison anticipée       → Déçus / Insatisfaits

NOTE: This module is imported by both Dash (dashboard/) and Streamlit (dashboard/).
      Keep it free of framework-specific imports at the top level.
"""

from __future__ import annotations

# ── Segment naming — basé sur les profils réels ───────────────────────────────
SEGMENT_NAMES: dict[int, str] = {
    0: "Premium Crédit",
    1: "Économes Boleto",
    2: "Périphériques Contraints",
    3: "Mainstream",
    4: "Champions",
    5: "Déçus / Insatisfaits",
}

# ── Avatar client (phrase courte pour l'équipe marketing) ─────────────────────
SEGMENT_AVATARS: dict[int, str] = {
    0: "Acheteur urbain à fort pouvoir d'achat, privilégie l'achat en plusieurs fois par carte bancaire. Panier élevé (~231 BRL) mais inactif depuis ~8 mois.",
    1: "Client frugal, règle exclusivement par Boleto (virement bancaire) en une seule fois. Panier modeste (~98 BRL), sensible au prix.",
    2: "Client éloigné des grands centres : le fret représente 84% de la valeur du panier. Achats de faible valeur (~37 BRL) dissuadés par les frais de livraison.",
    3: "Acheteur type d'Olist : panier standard (~96 BRL), carte de crédit, 2 versements, satisfait. Représente 41% de la base — le cœur de cible.",
    4: "Client le plus fidèle : acheteur répété (fréquence ≥ 2), CLV le plus élevé (~476 BRL), le plus récent. Moteur de croissance à chouchouter.",
    5: "Client déçu : note de 1/5 malgré une livraison en avance. Incident probable (mauvais produit, colis endommagé). Risque de churn et bad-buzz élevé.",
}

# ── Recommandations marketing actionnables ────────────────────────────────────
RECOMMENDATIONS: dict[int, list[str]] = {
    0: [
        "Proposer des facilités de paiement étendues (12–18 versements) sur les catégories premium",
        "Campagne de réactivation : offre exclusive valable 30 jours pour les inactifs > 6 mois",
        "Cross-sell vers catégories complémentaires (électronique → accessoires, maison → déco)",
        "Programme points fidélité : récompenser la valeur du panier, pas la fréquence",
    ],
    1: [
        "Mettre en avant les offres 'prix bas garanti' et comparateurs de prix",
        "Boleto avec cashback symbolique (3–5%) pour encourager le repeat purchase",
        "Éviter les campagnes premium — cibler promotions flash et déstockages",
        "Newsletter thématique 'meilleures affaires de la semaine'",
    ],
    2: [
        "Offrir la livraison gratuite à partir d'un seuil (ex. panier ≥ 60 BRL) pour augmenter le panier moyen",
        "Mettre en avant des vendeurs locaux ou des points relais pour réduire les frais de port",
        "Tester des bundles : regrouper plusieurs produits pour diluer le coût de livraison",
        "Évaluer si une offre d'abonnement livraison (type Prime) est rentable sur ce segment",
    ],
    3: [
        "Segmenter en sous-groupes par catégorie produit pour personnaliser les recommandations",
        "Programme de parrainage : ce segment représente 41% — excellent vecteur de bouche-à-oreille",
        "Tester l'upsell vers le segment Premium Crédit avec des offres à 3 versements",
        "Campagnes saisonnières (Noël, Black Friday) : forte réactivité attendue",
    ],
    4: [
        "Accès VIP : ventes privées, avant-premières et coupons exclusifs avant tout le monde",
        "Programme d'ambassadeurs : inviter à laisser des avis et partager sur les réseaux",
        "Surprendre avec un cadeau surprise ou upgrade de livraison sur le prochain achat",
        "Ne jamais laisser plus de 60 jours sans contact — ces clients partent chez la concurrence en silence",
    ],
    5: [
        "Contact proactif immédiat : e-mail d'excuse + bon de réduction pour la prochaine commande",
        "Enquête rapide (2 questions) : identifier la cause de l'insatisfaction (produit vs. service)",
        "Priorité SAV : traiter ce segment en premier dans la file de tickets support",
        "Si aucun rachat dans les 90 jours post-incident : exclure des campagnes (coût d'acquisition > valeur attendue)",
    ],
}

# ── Couleur Bootstrap par segment (pour le Dash dashboard) ───────────────────
SEGMENT_COLORS: dict[int, str] = {
    0: "primary",
    1: "secondary",
    2: "warning",
    3: "info",
    4: "success",
    5: "danger",
}

# ── Icône Bootstrap Icons par segment ─────────────────────────────────────────
SEGMENT_ICONS: dict[int, str] = {
    0: "bi-credit-card-2-front",
    1: "bi-piggy-bank",
    2: "bi-geo-alt",
    3: "bi-people",
    4: "bi-trophy",
    5: "bi-emoji-frown",
}


def get_segment_name(cluster_id: int) -> str:
    """Returns the human-readable name for a cluster."""
    return SEGMENT_NAMES.get(cluster_id, f"Cluster {cluster_id}")


def get_recommendation_card(cluster_id: int):  # type: ignore[return]
    """Builds a Bootstrap card with avatar description + marketing bullet points.

    Returns a dbc.Card if dash_bootstrap_components is available, else None.
    This guards against import errors in Streamlit context.
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
