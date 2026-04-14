"""Data loading for the dashboard — all files cached with lru_cache."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

# Paths

_PROJECT_ROOT = Path(__file__).parents[2]
_PROCESSED = _PROJECT_ROOT / "data" / "processed"

PROFILE_PATH = _PROCESSED / "cluster_profile.parquet"
FEATURES_PATH = _PROCESSED / "customer_features_labeled.parquet"
COMPARISON_PATH = _PROCESSED / "model_comparison.csv"


# Loaders


@lru_cache(maxsize=1)
def load_cluster_profile() -> pd.DataFrame:
    """Load cluster_profile.parquet. Raises FileNotFoundError if not yet generated."""
    if not PROFILE_PATH.exists():
        raise FileNotFoundError(
            f"Cluster profile not found at {PROFILE_PATH}. "
            "Run notebooks/03_clustering.ipynb first."
        )
    return pd.read_parquet(PROFILE_PATH)


@lru_cache(maxsize=1)
def load_customer_features() -> pd.DataFrame:
    """Load customer_features_labeled.parquet. Raises FileNotFoundError if missing."""
    if not FEATURES_PATH.exists():
        raise FileNotFoundError(
            f"Labeled features not found at {FEATURES_PATH}. "
            "Run notebooks/03_clustering.ipynb first."
        )
    return pd.read_parquet(FEATURES_PATH)


@lru_cache(maxsize=1)
def load_model_comparison() -> pd.DataFrame | None:
    """Load model_comparison.csv. Returns None if the file doesn't exist yet."""
    if not COMPARISON_PATH.exists():
        return None
    return pd.read_csv(COMPARISON_PATH)


def get_segment_ids() -> list[int]:
    """Return sorted list of cluster IDs from the profile (e.g. [0, 1, 2, 3, 4, 5])."""
    profile = load_cluster_profile()
    return sorted(profile["cluster"].unique().tolist())
