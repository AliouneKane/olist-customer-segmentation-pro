"""Overview page — segment distribution and global KPIs.

Path: /
"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from dashboard.components.charts import (
    bar_segment_comparison,
    heatmap_cluster_features,
    pie_segment_distribution,
)
from dashboard.components.data_store import load_cluster_profile
from dashboard.components.kpi_cards import make_kpi_row

dash.register_page(__name__, path="/", name="Vue d'Ensemble", order=0)

# Numeric feature columns available for the bar comparison dropdown
_METRIC_OPTIONS = [
    {"label": "CLV Proxy (BRL)", "value": "CLV_proxy"},
    {"label": "Montant médian (Monetary)", "value": "Monetary"},
    {"label": "Récence médiane (jours)", "value": "Recency"},
    {"label": "Délai livraison moyen", "value": "avg_delivery_delay"},
    {"label": "Score satisfaction moyen", "value": "avg_review_score"},
    {"label": "Ratio frais de port", "value": "avg_freight_ratio"},
    {"label": "Versements moyens", "value": "avg_installments"},
]

_HEATMAP_FEATURES = [
    "Monetary",
    "Recency",
    "avg_delivery_delay",
    "avg_review_score",
    "avg_freight_ratio",
    "avg_installments",
]


def layout() -> dbc.Container:
    """Builds the overview page layout (lazy — parquets read on page load)."""
    try:
        profile_df = load_cluster_profile()
    except FileNotFoundError as exc:
        return dbc.Container(
            dbc.Alert(str(exc), color="warning", className="mt-4"),
            fluid=True,
        )

    # Filter metric options to columns actually present in the profile
    metric_opts = [o for o in _METRIC_OPTIONS if o["value"] in profile_df.columns]
    default_metric = metric_opts[0]["value"] if metric_opts else None
    n_segments = len(profile_df)

    return dbc.Container(
        [
            # ── Title ──────────────────────────────────────────────────────────
            dbc.Row(
                dbc.Col(
                    [
                        html.H2(
                            "Vue d'Ensemble de la Segmentation",
                            className="fw-bold mb-1",
                        ),
                        html.P(
                            f"{n_segments} segments identifiés — données Olist 2016-2018",
                            className="text-muted",
                        ),
                    ]
                ),
                className="mb-3",
            ),
            # ── KPI cards ──────────────────────────────────────────────────────
            make_kpi_row(profile_df, selected_cluster=None),
            # ── Pie + Heatmap ──────────────────────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Graph(
                            figure=pie_segment_distribution(profile_df),
                            config={"displayModeBar": False},
                        ),
                        xs=12,
                        md=5,
                    ),
                    dbc.Col(
                        dcc.Graph(
                            figure=heatmap_cluster_features(
                                profile_df, _HEATMAP_FEATURES
                            ),
                            config={"displayModeBar": False},
                        ),
                        xs=12,
                        md=7,
                    ),
                ],
                className="mb-4",
            ),
            # ── Metric selector + Bar chart ────────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Label(
                                "Comparer les segments sur :",
                                className="fw-semibold mb-2",
                            ),
                            dcc.Dropdown(
                                id="metric-dropdown",
                                options=metric_opts,
                                value=default_metric,
                                clearable=False,
                                className="mb-3",
                            ),
                            dcc.Graph(id="bar-metric-chart"),
                        ],
                        xs=12,
                    )
                ]
            ),
        ],
        fluid=True,
    )


@callback(
    Output("bar-metric-chart", "figure"),
    Input("metric-dropdown", "value"),
)
def update_metric_bar(metric_col: str | None):
    """Updates the bar chart when the metric dropdown changes."""
    if not metric_col:
        return {}
    profile_df = load_cluster_profile()  # lru_cache — no I/O after first call
    if metric_col not in profile_df.columns:
        return {}
    return bar_segment_comparison(profile_df, metric_col)
