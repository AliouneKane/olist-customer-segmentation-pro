"""Algorithm Comparison page — metrics table across all 6 algorithms.

Path: /comparison

Reads data/processed/model_comparison.csv. Shows an informational alert
gracefully when the file is absent (notebook 03 not executed yet).
"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html

from dashboard.components.charts import bar_algorithm_metrics, table_algorithm_comparison
from dashboard.components.data_store import load_model_comparison

dash.register_page(__name__, path="/comparison", name="Comparaison Algorithmes", order=2)


def layout() -> dbc.Container:
    """Builds the algorithm comparison page layout."""
    comparison_df = load_model_comparison()

    if comparison_df is None:
        return dbc.Container(
            [
                dbc.Row(
                    dbc.Col(
                        html.H2("Comparaison des Algorithmes", className="fw-bold mb-3")
                    )
                ),
                dbc.Alert(
                    [
                        html.I(className="bi bi-info-circle me-2"),
                        "Aucune donnée de comparaison disponible. ",
                        html.Strong("Exécuter notebooks/03_clustering.ipynb"),
                        " pour générer ",
                        html.Code("data/processed/model_comparison.csv"),
                        ".",
                    ],
                    color="warning",
                    className="mt-2",
                ),
            ],
            fluid=True,
        )

    # Compute composite_score if missing (silhouette↑ + CH↑ - DB↓, min-max normalised)
    if "composite_score" not in comparison_df.columns:
        import numpy as np

        def _minmax(s):
            rng = s.max() - s.min()
            return (s - s.min()) / rng if rng > 0 else s * 0 + 0.5

        sil_n = _minmax(comparison_df["silhouette"]) if "silhouette" in comparison_df.columns else 0
        db_n = _minmax(comparison_df["davies_bouldin"]) if "davies_bouldin" in comparison_df.columns else 0
        ch_n = _minmax(comparison_df["calinski_harabasz"]) if "calinski_harabasz" in comparison_df.columns else 0
        comparison_df = comparison_df.copy()
        comparison_df["composite_score"] = ((sil_n - db_n + ch_n) / 3).round(4)

    best_algo = (
        comparison_df.loc[comparison_df["composite_score"].idxmax(), "algorithm"]
        if "composite_score" in comparison_df.columns and "algorithm" in comparison_df.columns
        else "N/A"
    )

    return dbc.Container(
        [
            # ── Title ──────────────────────────────────────────────────────────
            dbc.Row(
                dbc.Col(
                    [
                        html.H2("Comparaison des Algorithmes", className="fw-bold mb-1"),
                        html.P(
                            [
                                "Meilleur score composite : ",
                                html.Strong(best_algo, className="text-success"),
                                "  (silhouette ↑ + Calinski-Harabasz ↑ − Davies-Bouldin ↓)",
                            ],
                            className="text-muted",
                        ),
                    ]
                ),
                className="mb-3",
            ),
            # ── Methodology note ───────────────────────────────────────────────
            dbc.Row(
                dbc.Col(
                    dbc.Alert(
                        [
                            html.I(className="bi bi-lightbulb me-2"),
                            html.Strong("Note : "),
                            "DBSCAN et HDBSCAN sont inclus à titre comparatif mais ",
                            html.Strong("non éligibles en production"),
                            " (algorithmes transductifs — pas de ",
                            html.Code("predict()"),
                            " pour de nouveaux clients).",
                        ],
                        color="info",
                        className="py-2",
                    )
                ),
                className="mb-3",
            ),
            # ── Bar chart ──────────────────────────────────────────────────────
            dbc.Row(
                dbc.Col(
                    dcc.Graph(
                        figure=bar_algorithm_metrics(comparison_df),
                        config={"displayModeBar": False},
                    )
                ),
                className="mb-4",
            ),
            # ── Table ──────────────────────────────────────────────────────────
            dbc.Row(
                dbc.Col(
                    dcc.Graph(
                        figure=table_algorithm_comparison(comparison_df),
                        config={"displayModeBar": False},
                    )
                )
            ),
        ],
        fluid=True,
    )
