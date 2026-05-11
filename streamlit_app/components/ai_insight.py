"""Gemini-powered action plan for each cluster.

Generates a short list of very specific, immediately actionable tasks
for the marketing team : distinct from the high-level recommendations
already shown in the Strategy card.

Requires GEMINI_API_KEY in .env (or as environment variable).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

_GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai  # type: ignore

    _api_key = os.getenv("GEMINI_API_KEY", "")
    if _api_key:
        genai.configure(api_key=_api_key)
        _model = genai.GenerativeModel("gemini-2.5-flash")
        _GEMINI_AVAILABLE = True
except Exception:
    pass


def _build_prompt(cluster_id: int, profile_row: dict) -> str:
    """Builds the Gemini prompt asking for concrete, specific next actions."""
    from streamlit_app.components.segment_recommendations import (
        SEGMENT_NAMES,
        SEGMENT_TOP_CATEGORIES,
        SEGMENT_PRODUCT_RECS,
    )

    n = int(profile_row.get("n_customers", 0))
    pct = float(profile_row.get("pct_customers", 0))
    recency = float(profile_row.get("Recency", 0))
    monetary = float(profile_row.get("Monetary", 0))
    frequency = float(profile_row.get("Frequency", 1))
    freight_ratio = float(profile_row.get("avg_freight_ratio", 0))
    delivery_delay = float(profile_row.get("avg_delivery_delay", 0))
    review = float(profile_row.get("avg_review_score", 3))
    installments = float(profile_row.get("avg_installments", 1))
    cc_flag = float(profile_row.get("payment_type_cc_flag", 0))
    clv = float(profile_row.get("CLV_proxy", 0))

    payment_str = "carte de crédit" if cc_flag >= 0.5 else "Boleto"
    delivery_str = (
        f"{abs(delivery_delay):.1f} jours en avance"
        if delivery_delay < 0
        else f"{delivery_delay:.1f} jours de retard"
    )

    segment_name = SEGMENT_NAMES.get(cluster_id, f"Cluster {cluster_id}")
    top_cats = ", ".join(SEGMENT_TOP_CATEGORIES.get(cluster_id, []))
    top_prods = "\n".join(f"  - {p}" for p in SEGMENT_PRODUCT_RECS.get(cluster_id, []))

    return f"""Tu es responsable CRM et e-merchandising chez Olist, la principale marketplace brésilienne.

Profil médian du segment **{segment_name}** : Cluster {cluster_id} ({n:,} clients, {pct:.1f}% de la base) :

Comportement d'achat :
- Récence : {recency:.0f} jours depuis le dernier achat
- Panier médian : {monetary:.0f} BRL
- Fréquence : {frequency:.1f} commande(s)
- CLV proxy : {clv:.0f} BRL
- Paiement : {payment_str}, {installments:.1f} versement(s) en moyenne

Expérience logistique :
- Ratio fret/panier : {freight_ratio:.1%}
- Livraison : {delivery_str}
- Satisfaction : {review:.1f}/5

Préférences produit (catégories dominantes dans ce cluster) :
- Top catégories : {top_cats}
- Produits typiques consommés :
{top_prods}

Ta mission : produire exactement **5 tâches opérationnelles** à exécuter cette semaine, \
en couvrant les deux axes suivants :
- **Axe CRM / fréquence** : actions sur la cadence de communication, les canaux, les offres
- **Axe produit** : actions sur les produits spécifiques à pousser, les mises en avant, \
les cross-sells dans les catégories dominantes de ce segment

Règles impératives :
- Chaque tâche commence par un verbe d'action (Envoyer, Créer, Lancer, Mettre en avant…)
- Chaque tâche est spécifique : inclure un produit ou une catégorie réelle, un chiffre, un délai ou un canal
- Alterner entre actions sur la fréquence de contact et actions sur les produits à pousser
- Écrire en français simple, clair, compréhensible par quelqu'un sans formation marketing : \
pas de jargon, pas d'anglais, pas de termes techniques
- Chaque tâche doit pouvoir être comprise et exécutée par n'importe quel membre de l'équipe
- Maximum 25 mots par tâche

Format de réponse : uniquement cette liste numérotée, rien d'autre :
1. [tâche]
2. [tâche]
3. [tâche]
4. [tâche]
5. [tâche]"""


@lru_cache(maxsize=10)
def get_ai_insight(cluster_id: int, profile_hash: str) -> str | None:  # noqa: ARG001
    """Calls Gemini and returns 5 specific action tasks. Cached per cluster.

    Args:
        cluster_id: Integer cluster label.
        profile_hash: Hash of profile values used as cache key.

    Returns:
        Markdown string with 5 numbered action items, or None if unavailable.
    """
    if not _GEMINI_AVAILABLE:
        return None

    from streamlit_app.components.data_store import load_cluster_profile  # local import

    profile_df = load_cluster_profile()
    row = profile_df[profile_df["cluster"] == cluster_id]
    if row.empty:
        return None

    profile_dict = row.iloc[0].to_dict()
    prompt = _build_prompt(cluster_id, profile_dict)

    try:
        response = _model.generate_content(prompt)
        return response.text
    except Exception as exc:
        return f"_Erreur API Gemini : {exc}_"
