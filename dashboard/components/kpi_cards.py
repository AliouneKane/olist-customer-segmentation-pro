"""KPI card components for the Olist Segmentation dashboard.

Provides reusable Bootstrap card components that display a single numeric
KPI with a title, formatted value, and subtitle.
"""

from __future__ import annotations

import dash_bootstrap_components as dbc
import pandas as pd
from dash import html


def make_kpi_card(
    title: str,
    value: str,
    subtitle: str,
    color: str = "primary",
) -> dbc.Card:
    """Creates a single Bootstrap KPI card.

    Args:
        title: Card header text (e.g. "Total Customers").
        value: Main numeric value as a string (e.g. "12,450").
        subtitle: Secondary label below the value (e.g. "across all segments").
        color: Bootstrap color name for the card border (default "primary").

    Returns:
        dbc.Card component.
    """
    return dbc.Card(
        dbc.CardBody(
            [
                html.H6(title, className="card-subtitle text-muted mb-1"),
                html.H3(value, className="card-title fw-bold mb-0"),
                html.Small(subtitle, className="text-muted"),
            ]
        ),
        color=color,
        outline=True,
        className="shadow-sm h-100",
    )


def make_kpi_row(
    profile_df: pd.DataFrame,
    selected_cluster: int | None = None,
) -> dbc.Row:
    """Builds a row of 3 KPI cards from the cluster profile.

    When selected_cluster is None, shows global aggregates across all
    segments. When a cluster is specified, shows metrics for that segment.

    Args:
        profile_df: Output of build_cluster_profile(). Must have
            n_customers, pct_customers, CLV_proxy columns.
        selected_cluster: Optional cluster label to filter to.

    Returns:
        dbc.Row with 3 dbc.Col / dbc.Card children.
    """
    if selected_cluster is not None:
        row = profile_df[profile_df["cluster"] == selected_cluster]
        if row.empty:
            row = profile_df.iloc[[0]]
        n_customers = int(row["n_customers"].iloc[0])
        pct = float(row["pct_customers"].iloc[0])
        clv = float(row["CLV_proxy"].iloc[0]) if "CLV_proxy" in row.columns else 0.0
        subtitle_n = f"Cluster {selected_cluster}"
        subtitle_pct = "du total clients"
        subtitle_clv = "CLV proxy médian (BRL)"
    else:
        n_customers = int(profile_df["n_customers"].sum())
        pct = 100.0
        clv = float(profile_df["CLV_proxy"].median()) if "CLV_proxy" in profile_df.columns else 0.0
        n_segments = len(profile_df)
        subtitle_n = f"sur {n_segments} segments"
        subtitle_pct = "couverture"
        subtitle_clv = "CLV proxy médian global (BRL)"

    return dbc.Row(
        [
            dbc.Col(
                make_kpi_card(
                    title="Clients",
                    value=f"{n_customers:,}",
                    subtitle=subtitle_n,
                    color="primary",
                ),
                xs=12,
                md=4,
            ),
            dbc.Col(
                make_kpi_card(
                    title="Part du Portefeuille",
                    value=f"{pct:.1f}%",
                    subtitle=subtitle_pct,
                    color="info",
                ),
                xs=12,
                md=4,
            ),
            dbc.Col(
                make_kpi_card(
                    title="CLV Proxy",
                    value=f"R$ {clv:,.0f}",
                    subtitle=subtitle_clv,
                    color="success",
                ),
                xs=12,
                md=4,
            ),
        ],
        className="g-3 mb-4",
    )
