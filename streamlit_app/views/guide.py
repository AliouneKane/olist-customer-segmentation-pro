"""Guide du Dashboard — page d'aide pour les non-techniciens.

Explique chaque métrique, chaque segment, comment lire les graphiques,
et quoi regarder en priorité.
"""

from __future__ import annotations

import streamlit as st

from streamlit_app.styles import OLIST_BLUE, OLIST_YELLOW, SEGMENT_COLORS


def _section(title: str, icon: str = "") -> None:
    st.markdown(
        f"<h2 style='color:{OLIST_BLUE}; font-size:1.2rem; font-weight:700;"
        f" margin:1.5rem 0 0.5rem 0; padding-bottom:6px;"
        f" border-bottom:2px solid #e5e7eb;'>{icon} {title}</h2>",
        unsafe_allow_html=True,
    )


def _metric_card(
    name: str, definition: str, how_to_read: str, icon: str = "📌"
) -> None:
    st.markdown(
        f"""
        <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                    border-left:4px solid {OLIST_BLUE};
                    border-radius:0 8px 8px 0; padding:0.9rem 1.1rem;
                    margin-bottom:0.6rem; box-shadow:0 1px 3px #f3f4f6;">
            <div style="font-size:0.85rem; font-weight:700; color:{OLIST_BLUE};">
                {icon} {name}
            </div>
            <div style="font-size:0.82rem; color:#374151; margin-top:4px;
                        line-height:1.55;">
                <strong>Définition :</strong> {definition}
            </div>
            <div style="font-size:0.82rem; color:#6b7280; margin-top:4px;
                        line-height:1.55;">
                <strong>Comment le lire :</strong> {how_to_read}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _segment_card(
    cluster_id: int, name: str, icon: str, who: str, priority: str, action: str
) -> None:
    color = SEGMENT_COLORS[cluster_id]
    st.markdown(
        f"""
        <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                    border-top:4px solid {color};
                    border-radius:8px; padding:1rem 1.2rem;
                    margin-bottom:0.75rem; box-shadow:0 1px 3px #f3f4f6;">
            <div style="font-size:0.95rem; font-weight:700; color:{color}; margin-bottom:8px;">
                {icon} Cluster {cluster_id} — {name}
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;">
                <div>
                    <div style="font-size:0.68rem; color:#9ca3af; text-transform:uppercase;
                                letter-spacing:0.07em; font-weight:600; margin-bottom:3px;">
                        Qui sont-ils ?
                    </div>
                    <div style="font-size:0.82rem; color:#374151; line-height:1.5;">{who}</div>
                </div>
                <div>
                    <div style="font-size:0.68rem; color:#9ca3af; text-transform:uppercase;
                                letter-spacing:0.07em; font-weight:600; margin-bottom:3px;">
                        Priorité
                    </div>
                    <div style="font-size:0.82rem; color:#374151; line-height:1.5;">{priority}</div>
                </div>
                <div>
                    <div style="font-size:0.68rem; color:#9ca3af; text-transform:uppercase;
                                letter-spacing:0.07em; font-weight:600; margin-bottom:3px;">
                        Action immédiate
                    </div>
                    <div style="font-size:0.82rem; color:#374151; line-height:1.5;">{action}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render() -> None:
    """Renders the dashboard guide page."""

    # Hero
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,{OLIST_BLUE} 0%,#0033cc 100%);
                    border-radius:14px; padding:1.75rem 2.25rem; margin-bottom:1.5rem;">
            <div style="font-size:0.7rem; color:rgba(255,255,255,0.55);
                        text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px;">
                Mode d'emploi
            </div>
            <h1 style="color:#FFFFFF; font-size:1.6rem; font-weight:800; margin:0 0 8px 0;">
                📖 Guide du Dashboard
            </h1>
            <p style="color:rgba(255,255,255,0.85); font-size:0.9rem;
                      max-width:580px; line-height:1.7; margin:0;">
                Ce guide explique chaque chiffre, chaque graphique et chaque segment
                en langage clair — pensé pour les équipes marketing et métier,
                sans prérequis technique.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. PAR OÙ COMMENCER ?
    _section("Par où commencer ?", "🧭")

    st.markdown(
        f"""
        <div style="background:#f0f4ff; border:1px solid #c7d7fe;
                    border-radius:10px; padding:1.1rem 1.4rem; margin-bottom:1rem;">
            <div style="font-size:0.9rem; font-weight:700; color:{OLIST_BLUE};
                        margin-bottom:10px;">Parcours recommandé en 3 étapes :</div>
            <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px;">
                <div style="text-align:center;">
                    <div style="font-size:1.8rem;">📊</div>
                    <div style="font-weight:700; color:{OLIST_BLUE};
                                font-size:0.85rem; margin:4px 0 2px;">Étape 1</div>
                    <div style="font-size:0.8rem; color:#374151; line-height:1.5;">
                        <strong>Vue d'Ensemble</strong><br>
                        Regardez le camembert et les KPIs en haut. Identifiez quelle proportion
                        de clients est dans chaque segment.
                    </div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:1.8rem;">🔍</div>
                    <div style="font-weight:700; color:{OLIST_BLUE};
                                font-size:0.85rem; margin:4px 0 2px;">Étape 2</div>
                    <div style="font-size:0.8rem; color:#374151; line-height:1.5;">
                        <strong>Détail Segment</strong><br>
                        Sélectionnez un segment dans la sidebar. Lisez l'avatar,
                        le radar et les recommandations marketing.
                    </div>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:1.8rem;">🎯</div>
                    <div style="font-weight:700; color:{OLIST_BLUE};
                                font-size:0.85rem; margin:4px 0 2px;">Étape 3</div>
                    <div style="font-size:0.8rem; color:#374151; line-height:1.5;">
                        <strong>Priorisez</strong><br>
                        Concentrez-vous d'abord sur <em>Champions</em> (rétention)
                        et <em>Déçus</em> (récupération). Le ROI y est maximal.
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2. GLOSSAIRE DES MÉTRIQUES
    _section("Comprendre les métriques", "📐")

    st.markdown(
        "<p style='color:#6b7280; font-size:0.85rem; margin-bottom:0.75rem;'>"
        "Chaque chiffre du dashboard est expliqué ci-dessous. "
        "Cliquez sur les onglets pour naviguer.</p>",
        unsafe_allow_html=True,
    )

    tab_rfm, tab_exp, tab_sat, tab_pay = st.tabs(
        [
            "📦 RFM (comportement achat)",
            "🚚 Expérience livraison",
            "⭐ Satisfaction",
            "💳 Paiement & CLV",
        ]
    )

    with tab_rfm:
        _metric_card(
            "Récence (Recency)",
            icon="📅",
            definition="Nombre de jours écoulés depuis le dernier achat du client.",
            how_to_read="Plus le chiffre est <strong>élevé</strong>, plus le client est "
            "<strong>inactif</strong>. Un client avec Récence = 30 a acheté "
            "il y a 1 mois. Un client avec Récence = 300 n'a pas acheté depuis "
            "10 mois → risque de churn élevé.",
        )
        _metric_card(
            "Fréquence (Frequency)",
            icon="🔁",
            definition="Nombre total de commandes passées par le client.",
            how_to_read="La plupart des clients Olist n'achètent qu'<strong>une seule fois</strong> "
            "(e-commerce transactionnel). Un client avec Fréquence ≥ 2 est déjà "
            "exceptionnel et mérite une attention particulière.",
        )
        _metric_card(
            "Montant (Monetary)",
            icon="💰",
            definition="Montant médian d'une commande en Reais brésiliens (BRL).",
            how_to_read="C'est la valeur typique du panier du segment. "
            "1 BRL ≈ 0.18 EUR. Un segment avec Monetary = 200 BRL "
            "dépense environ 35 € par commande en médiane.",
        )

    with tab_exp:
        _metric_card(
            "Délai de livraison (avg_delivery_delay)",
            icon="📬",
            definition="Écart moyen en jours entre la date estimée et la date réelle de livraison. "
            "Négatif = livré en avance. Positif = livré en retard.",
            how_to_read="Une valeur <strong>négative</strong> (ex. -3j) signifie que les "
            "livraisons arrivent <em>avant</em> la date promise — c'est une bonne "
            "performance. Une valeur positive indique un retard moyen.",
        )
        _metric_card(
            "Ratio fret / panier (avg_freight_ratio)",
            icon="🚛",
            definition="Part des frais de livraison rapportée à la valeur totale de la commande.",
            how_to_read="Un ratio de <strong>0.84 (84 %)</strong> comme dans le Cluster 2 "
            "signifie que pour un panier de 37 BRL, le client paie 31 BRL de frais "
            "de port. C'est rédhibitoire et bloque les rachats.",
        )

    with tab_sat:
        _metric_card(
            "Note de satisfaction (avg_review_score)",
            icon="⭐",
            definition="Note moyenne laissée après commande, de 1 à 5.",
            how_to_read="<strong>4-5 :</strong> client satisfait, peu d'action nécessaire. "
            "<strong>3 :</strong> neutre, à surveiller. "
            "<strong>1-2 :</strong> insatisfaction sévère → action urgente. "
            "Le Cluster 5 a une note de 1.0/5 en médiane — c'est une urgence.",
        )

    with tab_pay:
        _metric_card(
            "CLV Proxy (Customer Lifetime Value)",
            icon="💎",
            definition="Estimation de la valeur totale qu'un client apportera sur la durée "
            "(Monetary × Frequency, en BRL).",
            how_to_read="Plus ce chiffre est élevé, plus le client est <strong>précieux</strong>. "
            "Le Cluster 4 (Champions) a un CLV de 476 BRL — "
            "soit 3× le CLV médian global. Un client Champion perdu = "
            "une perte 3× plus importante qu'un client standard.",
        )
        _metric_card(
            "Mode de paiement (payment_type_cc_flag)",
            icon="💳",
            definition="Proportion de clients du segment qui paient par carte de crédit (CC). "
            "0 = boleto (virement), 1 = carte de crédit.",
            how_to_read="Un segment à <strong>0.88</strong> paie à 88 % par carte. "
            "Cela indique un pouvoir d'achat plus élevé et une plus grande "
            "disposition à l'achat impulsif (promotions flash, cross-sell).",
        )
        _metric_card(
            "Nombre de versements (avg_installments)",
            icon="📋",
            definition="Nombre moyen de fois où le paiement est fractionné.",
            how_to_read="Au Brésil, le crédit sans intérêt en plusieurs fois est courant. "
            "Un segment avec <strong>8 versements</strong> en moyenne (Cluster 0) "
            "achète des produits coûteux et a besoin d'étalement de paiement "
            "— proposer 12-18 versements peut augmenter le panier.",
        )

    # 3. LIRE LES GRAPHIQUES
    _section("Comment lire les graphiques", "📈")

    col_a, col_b = st.columns(2, gap="medium")

    with col_a:
        st.markdown(
            f"""
            <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                        border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.75rem;">
                <div style="font-weight:700; color:{OLIST_BLUE};
                            font-size:0.9rem; margin-bottom:8px;">
                    🥧 Camembert — Répartition des segments
                </div>
                <div style="font-size:0.82rem; color:#374151; line-height:1.6;">
                    Chaque part représente le <strong>pourcentage de clients</strong>
                    dans ce segment. Une grande part = segment nombreux, pas forcément
                    le plus rentable. Regardez la taille + le CLV ensemble.
                </div>
            </div>
            <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                        border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.75rem;">
                <div style="font-weight:700; color:{OLIST_BLUE};
                            font-size:0.9rem; margin-bottom:8px;">
                    📊 Barres — Comparaison par métrique
                </div>
                <div style="font-size:0.82rem; color:#374151; line-height:1.6;">
                    Chaque barre = valeur <strong>médiane</strong> du segment (pas la moyenne).
                    La médiane est moins sensible aux valeurs extrêmes.
                    Comparez les hauteurs : la barre la plus haute sur "CLV" = segment
                    le plus précieux.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_b:
        st.markdown(
            f"""
            <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                        border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.75rem;">
                <div style="font-weight:700; color:{OLIST_BLUE};
                            font-size:0.9rem; margin-bottom:8px;">
                    🕸️ Radar — Profil multidimensionnel
                </div>
                <div style="font-size:0.82rem; color:#374151; line-height:1.6;">
                    Le radar montre <strong>7 dimensions</strong> en même temps, normalisées
                    de 0 à 1. Un segment avec une grande surface colorée est "fort" sur
                    beaucoup d'axes. Le segment sélectionné est mis en surbrillance.
                    Idéal pour comparer les profils d'un coup d'œil.
                </div>
            </div>
            <div style="background:#FFFFFF; border:1px solid #e5e7eb;
                        border-radius:10px; padding:1rem 1.2rem; margin-bottom:0.75rem;">
                <div style="font-weight:700; color:{OLIST_BLUE};
                            font-size:0.9rem; margin-bottom:8px;">
                    🌡️ Heatmap — Vue d'ensemble rapide
                </div>
                <div style="font-size:0.82rem; color:#374151; line-height:1.6;">
                    Chaque cellule = valeur médiane brute. <strong>Vert = élevé, Rouge = faible</strong>
                    (relatif aux autres clusters). Exemple : une cellule rouge sur "avg_review_score"
                    signifie que ce segment est le moins satisfait de tous.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 4. LES 6 SEGMENTS EN UN COUP D'ŒIL
    _section("Les 6 segments en un coup d'œil", "👥")

    _segment_card(
        0,
        "Premium Crédit",
        "💳",
        who="Acheteurs urbains à panier élevé (~231 BRL), paient en 8 versements par carte. "
        "Inactifs depuis ~8 mois.",
        priority="Réactivation — risque de churn silencieux élevé.",
        action="Email avec offre exclusive valable 30 jours + facilités 12-18 versements.",
    )
    _segment_card(
        1,
        "Économes Boleto",
        "🐷",
        who="Clients frugaux, paient uniquement par boleto (virement), panier ~98 BRL. "
        "Très sensibles au prix.",
        priority="Fidélisation par le prix — ne pas sur-dépenser en campagnes premium.",
        action="Newsletter 'meilleures affaires' + cashback boleto 3-5 %.",
    )
    _segment_card(
        2,
        "Périphériques Contraints",
        "📍",
        who="Clients éloignés des centres. Frais de port = 84 % du panier (~37 BRL). "
        "Achats bloqués par la logistique.",
        priority="Urgence logistique — sans action, ce segment n'achètera plus.",
        action="Livraison gratuite à partir de 60 BRL + mise en avant de vendeurs locaux.",
    )
    _segment_card(
        3,
        "Mainstream",
        "👥",
        who="41 % de la base. Panier standard ~96 BRL, carte de crédit, 2 versements, satisfait. "
        "Le cœur de cible Olist.",
        priority="Volume — acquisition et rétention de masse.",
        action="Programme de parrainage + upsell vers Premium avec offres à 3 versements.",
    )
    _segment_card(
        4,
        "Champions",
        "🏆",
        who="Seuls 3 % de la base mais CLV ~476 BRL (3× la moyenne). "
        "Acheteurs répétés, les plus récents.",
        priority="⚠️ PRIORITÉ ABSOLUE — ne jamais laisser sans contact > 60 jours.",
        action="Accès VIP, ventes privées, cadeau surprise sur prochain achat.",
    )
    _segment_card(
        5,
        "Déçus / Insatisfaits",
        "😞",
        who="Note 1/5 malgré une livraison en avance. Incident produit ou colis endommagé. "
        "Risque de bad buzz élevé.",
        priority="⚠️ URGENCE — chaque jour sans réponse amplifie le risque.",
        action="Email d'excuse + bon de réduction dans les 24h + enquête 2 questions.",
    )

    # 5. TABLEAU DE BORD PRIORITÉS
    _section("Tableau de bord des priorités marketing", "🎯")

    st.markdown(
        """
        <table style="width:100%; border-collapse:collapse; font-size:0.84rem;">
            <thead>
                <tr style="background:#0041FF; color:#FFFFFF;">
                    <th style="padding:10px 14px; text-align:left; border-radius:6px 0 0 0;">Priorité</th>
                    <th style="padding:10px 14px; text-align:left;">Segment</th>
                    <th style="padding:10px 14px; text-align:left;">Horizon</th>
                    <th style="padding:10px 14px; text-align:left;">Levier</th>
                    <th style="padding:10px 14px; text-align:left; border-radius:0 6px 0 0;">Impact attendu</th>
                </tr>
            </thead>
            <tbody>
                <tr style="background:#fef9c3;">
                    <td style="padding:9px 14px; font-weight:700;">🥇 #1</td>
                    <td style="padding:9px 14px;">🏆 Champions</td>
                    <td style="padding:9px 14px;">Immédiat</td>
                    <td style="padding:9px 14px;">Rétention VIP</td>
                    <td style="padding:9px 14px;">CLV ×2 possible sur 12 mois</td>
                </tr>
                <tr style="background:#fee2e2;">
                    <td style="padding:9px 14px; font-weight:700;">🥈 #2</td>
                    <td style="padding:9px 14px;">😞 Déçus</td>
                    <td style="padding:9px 14px;">Immédiat (&lt;24h)</td>
                    <td style="padding:9px 14px;">Récupération SAV</td>
                    <td style="padding:9px 14px;">Réduction du churn et du bad buzz</td>
                </tr>
                <tr style="background:#fef3c7;">
                    <td style="padding:9px 14px; font-weight:700;">🥉 #3</td>
                    <td style="padding:9px 14px;">💳 Premium Crédit</td>
                    <td style="padding:9px 14px;">Court terme (30j)</td>
                    <td style="padding:9px 14px;">Réactivation</td>
                    <td style="padding:9px 14px;">Récupérer 15-20 % d'inactifs</td>
                </tr>
                <tr style="background:#eff6ff;">
                    <td style="padding:9px 14px; font-weight:700;">#4</td>
                    <td style="padding:9px 14px;">📍 Périphériques</td>
                    <td style="padding:9px 14px;">Moyen terme</td>
                    <td style="padding:9px 14px;">Logistique</td>
                    <td style="padding:9px 14px;">+30 % fréquence d'achat possible</td>
                </tr>
                <tr style="background:#f0fdf4;">
                    <td style="padding:9px 14px; font-weight:700;">#5</td>
                    <td style="padding:9px 14px;">👥 Mainstream</td>
                    <td style="padding:9px 14px;">Long terme</td>
                    <td style="padding:9px 14px;">Volume + parrainage</td>
                    <td style="padding:9px 14px;">Acquisition organique via word-of-mouth</td>
                </tr>
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

    st.info(
        "💡 **Astuce :** Pour analyser un segment spécifique, sélectionnez-le dans la "
        "sidebar (menu *Segment Actif*) puis naviguez vers **Détail Segment**. "
        "L'analyse IA Gemini vous donnera une interprétation personnalisée en langage naturel.",
        icon="💡",
    )
