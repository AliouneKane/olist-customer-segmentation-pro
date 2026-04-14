"""Plotly chart functions for the Olist dashboard.

Each function takes a DataFrame and returns a go.Figure — no side effects.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Consistent color palette across all charts
_PALETTE = px.colors.qualitative.Set2


# Distribution


def pie_segment_distribution(profile_df: pd.DataFrame) -> go.Figure:
    """Donut chart of customer distribution across segments."""
    labels = [f"Cluster {c}" for c in profile_df["cluster"]]
    fig = px.pie(
        profile_df,
        names=labels,
        values="n_customers",
        color_discrete_sequence=_PALETTE,
        hole=0.35,
        title="Répartition des Clients par Segment",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(showlegend=True, margin={"t": 60, "b": 20})
    return fig


# Bar comparisons


def bar_segment_comparison(profile_df: pd.DataFrame, metric_col: str) -> go.Figure:
    """Bar chart comparing all segments on metric_col."""
    df = profile_df.copy()
    df["segment_label"] = df["cluster"].apply(lambda c: f"Cluster {c}")

    fig = px.bar(
        df,
        x="segment_label",
        y=metric_col,
        color="segment_label",
        color_discrete_sequence=_PALETTE,
        title=f"Comparaison des Segments — {metric_col}",
        labels={"segment_label": "Segment", metric_col: metric_col},
        text_auto=".2f",
    )
    fig.update_layout(showlegend=False, margin={"t": 60, "b": 40})
    return fig


def bar_algorithm_metrics(comparison_df: pd.DataFrame) -> go.Figure:
    """Grouped bar chart comparing algorithms on silhouette, Davies-Bouldin and CH."""
    metrics = ["silhouette", "davies_bouldin", "calinski_harabasz"]
    available = [m for m in metrics if m in comparison_df.columns]
    if not available:
        return go.Figure()

    fig = make_subplots(
        rows=1,
        cols=len(available),
        subplot_titles=available,
    )
    for col_i, metric in enumerate(available, start=1):
        for row_i, row in comparison_df.iterrows():
            fig.add_trace(
                go.Bar(
                    name=row["algorithm"] if col_i == 1 else None,
                    x=[row["algorithm"]],
                    y=[row[metric]],
                    marker_color=_PALETTE[int(row_i) % len(_PALETTE)],
                    showlegend=(col_i == 1),
                ),
                row=1,
                col=col_i,
            )
    fig.update_layout(
        title="Comparaison des Algorithmes de Clustering",
        barmode="group",
        height=400,
        margin={"t": 80},
    )
    return fig


# Radar chart


def radar_chart(
    profile_df: pd.DataFrame,
    feature_cols: list[str],
    selected_cluster: int | None = None,
) -> go.Figure:
    """Radar chart of per-cluster feature profiles (min-max normalized).

    The selected_cluster trace is highlighted with a filled area and thicker line.
    """
    cols = [c for c in feature_cols if c in profile_df.columns]
    if not cols:
        return go.Figure()

    # Min-max normalize across all clusters
    norm_df = profile_df[cols].copy()
    for c in cols:
        col_min = norm_df[c].min()
        col_max = norm_df[c].max()
        if col_max > col_min:
            norm_df[c] = (norm_df[c] - col_min) / (col_max - col_min)
        else:
            norm_df[c] = 0.5

    fig = go.Figure()
    categories = cols + [cols[0]]  # close the radar polygon

    for i, row in profile_df.iterrows():
        cluster_id = int(row["cluster"])
        values = norm_df.loc[i, cols].tolist() + [norm_df.loc[i, cols[0]]]
        is_selected = selected_cluster is not None and cluster_id == selected_cluster

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself" if is_selected else "none",
                name=f"Cluster {cluster_id}",
                line={
                    "color": _PALETTE[cluster_id % len(_PALETTE)],
                    "width": 3 if is_selected else 1,
                },
                opacity=1.0 if is_selected else 0.4,
            )
        )

    fig.update_layout(
        polar={"radialaxis": {"visible": True, "range": [0, 1]}},
        showlegend=True,
        title="Profil Radar des Segments (Médianes Normalisées)",
        height=500,
        margin={"t": 80},
    )
    return fig


# Heatmap


def heatmap_cluster_features(
    profile_df: pd.DataFrame,
    feature_cols: list[str],
) -> go.Figure:
    """Heatmap of per-cluster feature medians (raw values, RdYlGn scale)."""
    cols = [c for c in feature_cols if c in profile_df.columns]
    if not cols:
        return go.Figure()

    z = profile_df[cols].values
    y_labels = [f"Cluster {c}" for c in profile_df["cluster"]]

    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=cols,
            y=y_labels,
            colorscale="RdYlGn",
            text=np.round(z, 2),
            texttemplate="%{text}",
            showscale=True,
        )
    )
    fig.update_layout(
        title="Heatmap des Centroides par Segment",
        xaxis={"tickangle": -30},
        height=400,
        margin={"t": 80, "b": 80},
    )
    return fig


# Tables


def table_algorithm_comparison(comparison_df: pd.DataFrame) -> go.Figure:
    """Plotly table of algorithm metrics — best composite_score row highlighted in green."""
    cols_to_show = [
        c
        for c in [
            "algorithm",
            "n_clusters",
            "silhouette",
            "davies_bouldin",
            "calinski_harabasz",
            "composite_score",
        ]
        if c in comparison_df.columns
    ]
    df = comparison_df[cols_to_show].copy()

    # Round numeric columns
    for c in df.select_dtypes(include="float").columns:
        df[c] = df[c].round(4)

    # Highlight best composite_score row
    fill_colors = [["white"] * len(df)] * len(cols_to_show)
    if "composite_score" in df.columns:
        best_idx = df["composite_score"].idxmax()
        fill_colors = [
            ["#d4edda" if i == best_idx else "white" for i in range(len(df))]
            for _ in cols_to_show
        ]

    fig = go.Figure(
        go.Table(
            header={
                "values": [f"<b>{c}</b>" for c in cols_to_show],
                "fill_color": "#343a40",
                "font": {"color": "white", "size": 12},
                "align": "left",
            },
            cells={
                "values": [df[c].tolist() for c in cols_to_show],
                "fill_color": fill_colors,
                "align": "left",
                "font": {"size": 11},
            },
        )
    )
    fig.update_layout(
        title="Comparaison des Algorithmes (meilleur score en vert)",
        margin={"t": 60, "b": 10},
        height=350,
    )
    return fig
