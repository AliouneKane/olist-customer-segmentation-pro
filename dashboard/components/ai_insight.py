"""Gemini-powered action plan for each cluster.

Generates a short list of very specific, immediately actionable tasks
for the marketing team — distinct from the high-level recommendations
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

    return f"""Tu es responsable CRM opérationnel chez Olist, la principale marketplace brésilienne.

Profil médian du **Cluster {cluster_id}** ({n:,} clients, {pct:.1f}% de la base) :
- Récence : {recency:.0f} jours depuis le dernier achat
- Montant panier : {monetary:.2f} BRL
- Fréquence : {frequency:.1f} commande(s)
- Ratio fret/panier : {freight_ratio:.1%}
- Livraison : {delivery_str}
- Note satisfaction : {review:.1f}/5
- Paiement : {payment_str}, {installments:.1f} versements
- CLV proxy : {clv:.2f} BRL

Ta mission : produire exactement **5 tâches opérationnelles** à exécuter cette semaine.

Règles impératives :
- Chaque tâche commence par un verbe d'action au présent (Envoyer, Créer, Configurer, Appeler, Mettre en place…)
- Chaque tâche est **spécifique et mesurable** : inclure un chiffre, un délai, un canal ou un critère concret
- Ne pas répéter des conseils génériques type "personnaliser l'expérience" ou "fidéliser les clients"
- Ne pas expliquer pourquoi — juste quoi faire exactement
- Maximum 20 mots par tâche

Format de réponse — uniquement cette liste, rien d'autre :
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

    from dashboard.components.data_store import load_cluster_profile  # local import

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
