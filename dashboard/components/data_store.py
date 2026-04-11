"""Centralized data loading for the Olist Segmentation dashboard.

All parquet/CSV files are read once per container instance and cached via
lru_cache. The container is stateless — no mutable global state is kept.

Paths are resolved relative to the project root (two levels above this file),
so the same code works both locally and inside the Docker container where
WORKDIR=/app.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).parents[2]
_PROCESSED = _PROJECT_ROOT / "data" / "processed"

PROFILE_PATH = _PROCESSED / "cluster_profile.parquet"
FEATURES_PATH = _PROCESSED / "customer_features_labeled.parquet"
COMPARISON_PATH = _PROCESSED / "model_comparison.csv"


# ── Loaders ───────────────────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def load_cluster_profile() -> pd.DataFrame:
    """Returns the per-cluster profile DataFrame.

    Reads ``data/processed/cluster_profile.parquet``.
    Cached — file is read only once per container instance.

    Returns:
        DataFrame with columns: cluster, n_customers, pct_customers,
        CLV_proxy, and per-feature median values.

    Raises:
        FileNotFoundError: If the parquet file does not exist (notebook 03
            has not been executed yet).
    """
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(
            f"Cluster profile not found at {PROFILE_PATH}. "
            "Run notebooks/03_clustering.ipynb first."
        )
    return pd.read_parquet(PROFILE_PATH)


@lru_cache(maxsize=1)
def load_customer_features() -> pd.DataFrame:
    """Returns the labeled customer features DataFrame.

    Reads ``data/processed/customer_features_labeled.parquet``.
    Cached — file is read only once per container instance.

    Returns:
        DataFrame with customer_unique_id, all feature columns, and a
        ``cluster`` column.

    Raises:
        FileNotFoundError: If the parquet file does not exist.
    """
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"Labeled features not found at {FEATURES_PATH}. "
            "Run notebooks/03_clustering.ipynb first."
        )
    return pd.read_parquet(FEATURES_PATH)


@lru_cache(maxsize=1)
def load_model_comparison() -> pd.DataFrame | None:
    """Returns the algorithm comparison DataFrame, or None if not available.

    Reads ``data/processed/model_comparison.csv``.
    Returns None gracefully when the file is absent — the comparison page
    will show an informational alert instead of crashing.

    Returns:
        DataFrame with columns: algorithm, n_clusters, silhouette,
        davies_bouldin, calinski_harabasz, composite_score; or None.
    """
    if not COMPARISON_PATH.exists():
        return None
    return pd.read_csv(COMPARISON_PATH)


def get_segment_ids() -> list[int]:
    """Returns sorted unique cluster label integers from the profile.

    Returns:
        Sorted list of integer cluster labels (e.g. [0, 1, 2, 3, 4]).
    """
    profile = load_cluster_profile()
    return sorted(profile["cluster"].unique().tolist())
