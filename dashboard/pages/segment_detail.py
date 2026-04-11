"""Segment Detail page — deep dive into a single cluster.

Path: /segment
"""

from __future__ import annotations

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from dashboard.components.charts import bar_segment_comparison, radar_chart
from dashboard.components.data_store import get_segment_ids, load_cluster_profile
from dashboard.components.kpi_cards import make_kpi_row
from dashboard.components.segment_recommendations import get_recommendation_card

dash.register_page(__name__, path="/segment", name="Détail Segment", order=1)

_RADAR_FEATURES = [
    "Monetary",
    "Recency",
    "avg_delivery_delay",
    "avg_review_score",
    "avg_freight_ratio",
    "avg_installments",
    "region_freight_score",
]


def layout() -> dbc.Container:
    """Builds the segment detail page layout."""
    try:
        segment_ids = get_segment_ids()
    except FileNotFoundError as exc:
        return dbc.Container(
            dbc.Alert(str(exc), color="warning", className="mt-4"),
            fluid=True,
        )

    dropdown_options = [
        {"label": f"Cluster {sid}", "value": sid} for sid in segment_ids
    ]
    default_segment = segment_ids[0] if segment_ids else None

    return dbc.Container(
        [
            # ── Title ──────────────────────────────────────────────────────────
            dbc.Row(
                dbc.Col(
                    html.H2("Analyse par Segment", className="fw-bold mb-3")
                )
            ),
            # ── Segment selector ───────────────────────────────────────────────
            dbc.Row(
                dbc.Col(
                    [
                        html.Label("Sélectionner un segment :", className="fw-semibold mb-2"),
                        dcc.Dropdown(
                            id="segment-selector",
                            options=dropdown_options,
                            value=default_segment,
                            clearable=False,
                            className="mb-4",
                            style={"maxWidth": "300px"},
                        ),
                    ]
                )
            ),
            # ── KPI cards (filtered by segment) ───────────────────────────────
            html.Div(id="segment-kpi-row"),
            # ── Radar + Recommendations ────────────────────────────────────────
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Spinner(
                            dcc.Graph(id="radar-chart"),
                            color="primary",
                        ),
                        xs=12,
                        md=7,
                    ),
                    dbc.Col(
                        html.Div(id="recommendation-card"),
                        xs=12,
                        md=5,
                    ),
                ],
                className="mb-4",
            ),
            # ── Profile table ──────────────────────────────────────────────────
            dbc.Row(
                dbc.Col(
                    [
                        html.H5("Médianes du Segment", className="fw-semibold mb-2"),
                        html.Div(id="profile-table"),
                    ]
                )
            ),
        ],
        fluid=True,
    )


@callback(
    Output("radar-chart", "figure"),
    Output("recommendation-card", "children"),
    Output("profile-table", "children"),
    Output("segment-kpi-row", "children"),
    Input("segment-selector", "value"),
)
def update_segment_detail(cluster_id: int | None):
    """Updates all segment-specific components when the dropdown changes."""
    if cluster_id is None:
        return {}, html.Div(), html.Div(), html.Div()

    profile_df = load_cluster_profile()  # lru_cache

    radar_cols = [c for c in _RADAR_FEATURES if c in profile_df.columns]
    radar_fig = radar_chart(profile_df, radar_cols, selected_cluster=int(cluster_id))

    rec_card = get_recommendation_card(int(cluster_id))

    kpi_row = make_kpi_row(profile_df, selected_cluster=int(cluster_id))

    # Profile table — one row per cluster, highlight selected
    segment_row = profile_df[profile_df["cluster"] == cluster_id]
    numeric_cols = segment_row.select_dtypes(include="number").columns.tolist()
    display_cols = ["cluster"] + [c for c in numeric_cols if c != "cluster"]
    display_cols = [c for c in display_cols if c in segment_row.columns]

    table_header = html.Thead(
        html.Tr([html.Th(c, className="text-nowrap") for c in display_cols])
    )
    table_rows = []
    for _, row in profile_df[display_cols].iterrows():
        is_selected = int(row["cluster"]) == int(cluster_id)
        cells = []
        for c in display_cols:
            val = row[c]
            if isinstance(val, float):
                text = f"{val:,.2f}"
            else:
                text = str(int(val))
            cells.append(html.Td(text))
        table_rows.append(
            html.Tr(
                cells,
                style={"backgroundColor": "#d4edda", "fontWeight": "bold"}
                if is_selected
                else {},
            )
        )

    profile_table = dbc.Table(
        [table_header, html.Tbody(table_rows)],
        bordered=True,
        hover=True,
        responsive=True,
        size="sm",
        className="mt-2",
    )

    return radar_fig, rec_card, profile_table, kpi_row
