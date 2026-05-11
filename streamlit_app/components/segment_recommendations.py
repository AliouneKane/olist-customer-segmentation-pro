"""Marketing segment names, personas and recommendations for the Olist dashboard.

Cluster profiles (UMAP+KMeans k=4, silhouette=0.4486) on 75 937 clients:

  C0  21 146 (28%) : Recency 124j, Monetary  64 BRL  → Acheteurs Budget  (récents, faible valeur)
  C1  18 775 (25%) : Recency 292j, Monetary  72 BRL  → Dormants Budget   (inactifs, faible valeur)
  C2  18 546 (24%) : Recency 131j, Monetary 180 BRL  → Acheteurs Premium (récents, valeur élevée)
  C3  17 470 (23%) : Recency 367j, Monetary 160 BRL  → Dormants Premium  (inactifs, valeur élevée)

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
    0: (
        "Ce sont des clients qui ont acheté récemment (il y a environ 4 mois) mais qui dépensent peu "
        "(environ 64 BRL par commande). Ce sont souvent des femmes ou des hommes entre 22 et 40 ans, "
        "avec un budget serré, qui habitent surtout à São Paulo, Minas Gerais ou Rio de Janeiro. "
        "Ils achètent surtout des produits de beauté, des articles pour la maison et des jouets pour enfants. "
        "Ils aiment les promotions et cherchent toujours le meilleur prix. "
        "C'est notre plus grand groupe de clients : il faut les garder avec des offres régulières."
    ),
    1: (
        "Ces clients ont arrêté d'acheter depuis environ 10 mois et dépensaient peu (72 BRL en moyenne). "
        "Ce sont souvent des personnes de 30 à 55 ans, avec peu de moyens, "
        "qui habitent dans le Nordeste ou dans le Nord du Brésil : des régions où les frais de livraison "
        "sont élevés, ce qui les décourage souvent de recommander. "
        "Ils achetaient surtout des articles de maison basiques et des vêtements pas chers. "
        "Il ne faut pas dépenser trop pour les relancer : juste un email simple suffit."
    ),
    2: (
        "Ce sont nos meilleurs clients actifs : ils ont acheté il y a environ 4 mois "
        "et dépensent beaucoup (180 BRL par commande). "
        "C'est souvent une femme entre 25 et 45 ans, ou un homme passionné de technologie, "
        "avec un bon salaire, qui habite à São Paulo, Rio ou dans le Sud du pays. "
        "Ils paient par carte de crédit et achètent des produits de beauté haut de gamme, "
        "des téléphones, des vêtements de marque. "
        "Ce groupe a le plus grand potentiel : il faut le chouchouter et lui proposer des offres exclusives."
    ),
    3: (
        "Ces clients dépensaient bien (160 BRL par commande) mais n'ont plus rien acheté depuis plus d'un an. "
        "Ce sont souvent des hommes ou des femmes de 30 à 52 ans avec un bon salaire, "
        "habitant principalement à São Paulo ou Rio de Janeiro. "
        "Ils achetaient surtout de l'électronique cher, du mobilier et des montres ou bijoux. "
        "Ils payaient par carte de crédit en plusieurs fois. "
        "Ils sont partis probablement parce que personne ne les a relancés. "
        "Une belle offre de retour peut convaincre une bonne partie d'entre eux de revenir."
    ),
}

RECOMMENDATIONS: dict[int, list[str]] = {
    0: [
        "Promotions flash hebdomadaires et offres 'prix bas garantis' sur les catégories populaires",
        "Programme de fidélité : accumuler des points sur chaque achat pour déclencher la récurrence",
        "Bundles économiques : regrouper des produits pour augmenter le panier sans changer le prix perçu",
        "Newsletter thématique 'meilleures affaires de la semaine' : fréquence bimensuelle",
    ],
    1: [
        "Campagne de réactivation à coût minimal uniquement (email automatisé, pas de remise élevée)",
        "Tester une offre symbolique (-5%) pour déclencher un retour sans sacrifier la marge",
        "Après 60 jours sans réaction : exclure définitivement des campagnes actives",
        "Analyser la cause de l'inactivité (mauvaise expérience produit ?) avant tout investissement",
    ],
    2: [
        "Email de nurturing à J+30 : remerciement + recommandations personnalisées basées sur le premier achat",
        "Offre de deuxième achat : -10% valable 45 jours pour créer l'habitude d'achat",
        "Cross-sell intelligent : proposer des catégories complémentaires à forte affinité",
        "Inviter à rejoindre le programme VIP : ces clients ont le potentiel de devenir Champions",
    ],
    3: [
        "Email de réactivation personnalisé : 'Vous nous manquez' + offre exclusive -20% valable 30 jours",
        "Rappeler leur dernier achat et proposer des produits complémentaires ou une mise à jour",
        "Offre dégressive : -15% à J+0, -20% à J+14, -25% à J+28 pour créer l'urgence",
        "Après 90 jours sans réaction : basculer vers canal SMS ou exclure pour préserver le budget CRM",
    ],
}

# Top product categories per cluster (dominant tiers from UMAP+KMeans labeling)
SEGMENT_TOP_CATEGORIES: dict[int, list[str]] = {
    0: ["Beauté & Santé", "Maison & Ameublement", "Enfants & Loisirs"],
    1: ["Maison & Ameublement", "Mode & Accessoires", "Loisirs & Culture"],
    2: ["Beauté & Santé", "Électronique & Technologie", "Mode & Accessoires"],
    3: ["Électronique & Technologie", "Maison & Ameublement", "Mode & Accessoires"],
}

# Specific product recommendations within dominant categories
SEGMENT_PRODUCT_RECS: dict[int, list[str]] = {
    0: [
        "Cosmétiques entrée de gamme (crèmes, soins corps, maquillage basique)",
        "Articles ménagers essentiels (ustensiles de cuisine, rangement, nettoyage)",
        "Jouets et articles bébé en promotion (peluches, jouets d'éveil, couches)",
        "Livres pratiques et papeterie (auto-formation, scolaire)",
    ],
    1: [
        "Articles de maison basiques (linge de maison, vaisselle, petit électroménager)",
        "Accessoires mode abordables (sacs, ceintures, bijoux fantaisie)",
        "Livres et DVDs d'occasion ou en promotion",
        "Outils et fournitures bricolage entrée de gamme",
    ],
    2: [
        "Soins beauté premium (sérums, parfums, coffrets cadeau cosmétiques)",
        "Smartphones et accessoires tech récents (écouteurs, coques, montres connectées)",
        "Vêtements et chaussures de marque (mode féminine et masculine tendance)",
        "Montres et bijoux (cadeaux, accessoires lifestyle)",
    ],
    3: [
        "Électronique haut de gamme (TV, ordinateurs, appareils photo)",
        "Mobilier et décoration premium (canapé, luminaires, art mural)",
        "Montres et bijoux de valeur (cadeaux d'exception)",
        "Accessoires tech premium (tablettes, audio haute fidélité)",
    ],
}

# Socio-demographic & ad targeting profiles for Facebook Ads / Google Ads
SEGMENT_ADS_TARGETING: dict[int, dict] = {
    0: {
        "age": "22-40 ans",
        "genre": "Femme (dominante) · Homme",
        "localisation": "Sudeste (SP, MG, RJ) · Toutes régions urbaines",
        "revenu": "Classe C : R$ 2 000-5 000 / mois",
        "interets_facebook": [
            "Promotions et bons plans",
            "Beauté et soins personnels",
            "Shopping en ligne",
            "Famille et enfants",
        ],
        "audiences_google": [
            "In-market : Beauty & Personal Care",
            "In-market : Baby & Children Products",
            "In-market : Home & Garden",
            "Affinité : Bargain Hunters",
        ],
        "comportements": "Acheteurs occasionnels · Sensibles au prix · Mobile-first",
        "message_cle": "Prix bas garantis · Livraison rapide · Offres flash",
    },
    1: {
        "age": "30-55 ans",
        "genre": "Tous",
        "localisation": "Nordeste (BA, CE, PE) · Norte (PA, AM) · Intérieur",
        "revenu": "Classe C / D : R$ 1 000-3 000 / mois",
        "interets_facebook": [
            "Achats en ligne",
            "Comparateurs de prix",
            "Maison et décoration",
            "Mode et accessoires",
        ],
        "audiences_google": [
            "In-market : Home Furnishings",
            "In-market : Apparel & Accessories",
            "Affinité : Value Shoppers",
            "Remarketing : inactifs 6-18 mois",
        ],
        "comportements": "Inactifs depuis 6-18 mois · Boleto dominant · Peu d'installments",
        "message_cle": "On vous a manqué · Offre de retour · Fret réduit pour votre région",
    },
    2: {
        "age": "25-45 ans",
        "genre": "Femme (Beauté) · Homme (Tech) · Mix",
        "localisation": "Sudeste (SP, RJ) · Sul (SC, PR) · Capitales",
        "revenu": "Classe A / B : R$ 5 000+ / mois",
        "interets_facebook": [
            "Lifestyle et tendances",
            "Technologie et gadgets",
            "Beauté et soins premium",
            "Mode et shopping",
        ],
        "audiences_google": [
            "In-market : Consumer Electronics",
            "In-market : Luxury Beauty",
            "In-market : Clothing & Accessories",
            "Affinité : Technophiles · Fashion & Style",
        ],
        "comportements": "Acheteurs actifs · CB avec installments · Affinité marques premium",
        "message_cle": "Exclusivité · Qualité premium · Livraison express · Programme VIP",
    },
    3: {
        "age": "30-52 ans",
        "genre": "Mix : légère dominance masculine (Électronique)",
        "localisation": "Sudeste (SP, RJ, MG dominant) · Sul",
        "revenu": "Classe B : R$ 3 000-7 000 / mois",
        "interets_facebook": [
            "Technologie et informatique",
            "Maison et décoration haut de gamme",
            "Lifestyle et voyages",
            "Montres et bijoux",
        ],
        "audiences_google": [
            "In-market : Computers & Peripherals",
            "In-market : Home Improvement",
            "In-market : Jewelry & Watches",
            "Remarketing : inactifs 12-24 mois · panier élevé",
        ],
        "comportements": "Ex-acheteurs premium · Inactifs 12-24 mois · CB installments",
        "message_cle": "Offre exclusive de retour · Nouveautés depuis votre dernier achat",
    },
}

# Bootstrap color names (used by the legacy Dash build if ever reactivated)
SEGMENT_COLORS: dict[int, str] = {
    0: "warning",  # Acheteurs Budget  : amber
    1: "secondary",  # Dormants Budget   : gray
    2: "primary",  # Acheteurs Premium : blue
    3: "info",  # Dormants Premium  : teal
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

    name = get_segment_name(cluster_id)
    avatar = SEGMENT_AVATARS.get(cluster_id, "")
    recs = RECOMMENDATIONS.get(
        cluster_id, ["Analyser le profil avant de définir une stratégie."]
    )
    color = SEGMENT_COLORS.get(cluster_id, "secondary")
    icon = SEGMENT_ICONS.get(cluster_id, "bi-person")

    return dbc.Card(
        [
            dbc.CardHeader(
                html.H5(
                    [html.I(className=f"bi {icon} me-2"), f"Stratégie : {name}"],
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
