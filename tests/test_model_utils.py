"""Unit tests for src/model_utils.py.

Focuses on the inference and persistence surface:
- compute_clustering_metrics (incl. noise handling, degenerate cases)
- save_model / load_model (disk round-trip + metadata sidecar)
- assign_clusters_to_new_customers (KMeans OK, DBSCAN raises)
- build_cluster_profile (shape, columns, CLV_proxy)
"""

import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler

# conftest.py already adds src/ to sys.path
from model_utils import (
    assign_clusters_to_new_customers,
    build_cluster_profile,
    compute_clustering_metrics,
    load_model,
    save_model,
)


# Fixtures


@pytest.fixture
def synthetic_X() -> np.ndarray:
    """200 points in 9-dimensional space with 3 clear clusters."""
    rng = np.random.default_rng(0)
    centers = np.array([[0, 0, 0, 0, 0, 0, 0, 0, 0],
                        [5, 5, 5, 5, 5, 5, 5, 5, 5],
                        [-5, -5, -5, -5, -5, -5, -5, -5, -5]], dtype=float)
    X = np.vstack([
        rng.normal(loc=c, scale=0.5, size=(67, 9)) for c in centers
    ])
    return X.astype(np.float64)


@pytest.fixture
def kmeans_model(synthetic_X: np.ndarray) -> KMeans:
    return KMeans(n_clusters=3, n_init=10, random_state=42).fit(synthetic_X)


@pytest.fixture
def sample_raw_df(synthetic_X: np.ndarray) -> pd.DataFrame:
    """Raw (non-scaled) customer DataFrame aligned with synthetic_X."""
    n = len(synthetic_X)
    rng = np.random.default_rng(1)
    return pd.DataFrame(
        {
            "customer_unique_id": [f"c{i}" for i in range(n)],
            "Monetary": rng.uniform(50, 500, size=n),
            "Frequency": rng.integers(1, 5, size=n).astype(float),
            "Frequency_flag": rng.integers(0, 2, size=n).astype(int),
            "avg_delivery_delay": rng.uniform(-2, 15, size=n),
        }
    )


# compute_clustering_metrics


def test_metrics_basic_keys(synthetic_X: np.ndarray, kmeans_model: KMeans) -> None:
    """compute_clustering_metrics must return the 3 standard metric keys."""
    labels = kmeans_model.predict(synthetic_X)
    metrics = compute_clustering_metrics(synthetic_X, labels)
    assert "silhouette" in metrics
    assert "davies_bouldin" in metrics
    assert "calinski_harabasz" in metrics


def test_metrics_basic_values(synthetic_X: np.ndarray, kmeans_model: KMeans) -> None:
    """Metrics for well-separated clusters must be finite and sensible."""
    labels = kmeans_model.predict(synthetic_X)
    m = compute_clustering_metrics(synthetic_X, labels)
    assert 0 < m["silhouette"] <= 1
    assert m["davies_bouldin"] > 0
    assert m["calinski_harabasz"] > 0


def test_metrics_wcss_optional(synthetic_X: np.ndarray, kmeans_model: KMeans) -> None:
    """wcss key must only appear when wcss is explicitly passed."""
    labels = kmeans_model.predict(synthetic_X)
    without_wcss = compute_clustering_metrics(synthetic_X, labels)
    with_wcss = compute_clustering_metrics(synthetic_X, labels, wcss=1234.5)
    assert "wcss" not in without_wcss
    assert with_wcss["wcss"] == pytest.approx(1234.5)


def test_metrics_noise_excluded(synthetic_X: np.ndarray) -> None:
    """Noise points (label -1) must not cause exceptions; metrics remain valid."""
    labels = KMeans(n_clusters=3, n_init=5, random_state=42).fit_predict(synthetic_X)
    noisy_labels = labels.copy()
    noisy_labels[:5] = -1  # inject some noise
    m = compute_clustering_metrics(synthetic_X, noisy_labels)
    assert np.isfinite(m["silhouette"])
    assert np.isfinite(m["davies_bouldin"])


def test_metrics_one_cluster_returns_nan(synthetic_X: np.ndarray) -> None:
    """With only 1 cluster, metrics must be NaN without raising."""
    labels = np.zeros(len(synthetic_X), dtype=int)
    m = compute_clustering_metrics(synthetic_X, labels)
    assert np.isnan(m["silhouette"])
    assert np.isnan(m["davies_bouldin"])
    assert np.isnan(m["calinski_harabasz"])


def test_metrics_all_noise_returns_nan(synthetic_X: np.ndarray) -> None:
    """With all noise labels (-1), metrics must be NaN without raising."""
    labels = np.full(len(synthetic_X), -1, dtype=int)
    m = compute_clustering_metrics(synthetic_X, labels)
    assert np.isnan(m["silhouette"])


# save_model / load_model


def test_save_load_roundtrip(kmeans_model: KMeans, synthetic_X: np.ndarray) -> None:
    """save_model + load_model must reproduce identical predict() output."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.pkl"
        save_model(kmeans_model, path)
        loaded = load_model(path)
        np.testing.assert_array_equal(
            kmeans_model.predict(synthetic_X),
            loaded.predict(synthetic_X),
        )


def test_save_model_creates_file(kmeans_model: KMeans) -> None:
    """save_model must write the .pkl file to disk."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.pkl"
        save_model(kmeans_model, path)
        assert path.exists()


def test_save_model_metadata_sidecar(kmeans_model: KMeans) -> None:
    """save_model must write a valid JSON sidecar when metadata is provided."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.pkl"
        meta = {"algorithm": "kmeans", "k": 3, "silhouette": 0.85}
        save_model(kmeans_model, path, metadata=meta)
        json_path = path.with_suffix(".json")
        assert json_path.exists()
        with open(json_path) as f:
            loaded_meta = json.load(f)
        assert loaded_meta["algorithm"] == "kmeans"
        assert loaded_meta["k"] == 3
        assert "saved_at" in loaded_meta  # auto-added by save_model


def test_save_model_missing_parent_raises(kmeans_model: KMeans) -> None:
    """save_model must raise ValueError when the parent directory is absent."""
    path = Path("/non/existent/path/model.pkl")
    with pytest.raises(ValueError, match="parent directory does not exist"):
        save_model(kmeans_model, path)


def test_load_model_missing_file_raises() -> None:
    """load_model must raise FileNotFoundError for a non-existent path."""
    with pytest.raises(FileNotFoundError):
        load_model(Path("/tmp/does_not_exist_xyz.pkl"))


# assign_clusters_to_new_customers


def test_assign_clusters_kmeans(
    kmeans_model: KMeans,
    sample_raw_df: pd.DataFrame,
    synthetic_X: np.ndarray,
) -> None:
    """assign_clusters_to_new_customers must return a Series indexed by customer_unique_id."""
    from features import FINAL_FEATURES

    rng = np.random.default_rng(7)
    n = len(sample_raw_df)
    # Build a DataFrame that has all FINAL_FEATURES (use synthetic_X values)
    df_new = pd.DataFrame(synthetic_X, columns=FINAL_FEATURES)
    df_new.insert(0, "customer_unique_id", [f"new_{i}" for i in range(n)])

    with tempfile.TemporaryDirectory() as tmp:
        scaler = StandardScaler().fit(synthetic_X)
        scaler_path = Path(tmp) / "scaler.pkl"
        import joblib
        joblib.dump(scaler, scaler_path)

        result = assign_clusters_to_new_customers(
            df_new, kmeans_model, scaler_path, feature_cols=FINAL_FEATURES
        )

    assert isinstance(result, pd.Series)
    assert result.name == "cluster"
    assert len(result) == n
    assert list(result.index) == list(df_new["customer_unique_id"])
    assert set(result.unique()).issubset({0, 1, 2})


def test_assign_clusters_dbscan_raises(synthetic_X: np.ndarray) -> None:
    """assign_clusters_to_new_customers must raise NotImplementedError for DBSCAN."""
    dbscan = DBSCAN(eps=1.0, min_samples=5).fit(synthetic_X)
    with tempfile.TemporaryDirectory() as tmp:
        scaler_path = Path(tmp) / "scaler.pkl"
        # File can be a dummy — error should be raised before loading it
        scaler_path.write_bytes(b"")
        df_dummy = pd.DataFrame({"customer_unique_id": ["x"]})
        with pytest.raises(NotImplementedError):
            assign_clusters_to_new_customers(df_dummy, dbscan, scaler_path)


# build_cluster_profile


def test_profile_shape(
    sample_raw_df: pd.DataFrame, kmeans_model: KMeans, synthetic_X: np.ndarray
) -> None:
    """build_cluster_profile must return one row per cluster."""
    labels = kmeans_model.predict(synthetic_X)
    feature_cols = ["Monetary", "Frequency", "avg_delivery_delay"]
    profile = build_cluster_profile(sample_raw_df, labels, feature_cols)
    n_clusters = len(np.unique(labels[labels != -1]))
    assert len(profile) == n_clusters


def test_profile_required_columns(
    sample_raw_df: pd.DataFrame, kmeans_model: KMeans, synthetic_X: np.ndarray
) -> None:
    """build_cluster_profile must always include n_customers and pct_customers."""
    labels = kmeans_model.predict(synthetic_X)
    feature_cols = ["Monetary", "Frequency"]
    profile = build_cluster_profile(sample_raw_df, labels, feature_cols)
    assert "n_customers" in profile.columns
    assert "pct_customers" in profile.columns
    assert "cluster" in profile.columns


def test_profile_clv_proxy(
    sample_raw_df: pd.DataFrame, kmeans_model: KMeans, synthetic_X: np.ndarray
) -> None:
    """build_cluster_profile must compute CLV_proxy = Monetary * (1 + Frequency_flag)."""
    labels = kmeans_model.predict(synthetic_X)
    feature_cols = ["Monetary", "Frequency_flag"]
    profile = build_cluster_profile(sample_raw_df, labels, feature_cols)
    assert "CLV_proxy" in profile.columns
    # CLV_proxy >= Monetary (since Frequency_flag >= 0)
    assert (profile["CLV_proxy"] >= profile["Monetary"]).all()


def test_profile_pct_sums_to_100(
    sample_raw_df: pd.DataFrame, kmeans_model: KMeans, synthetic_X: np.ndarray
) -> None:
    """pct_customers across all clusters must sum to approximately 100."""
    labels = kmeans_model.predict(synthetic_X)
    feature_cols = ["Monetary"]
    profile = build_cluster_profile(sample_raw_df, labels, feature_cols)
    assert profile["pct_customers"].sum() == pytest.approx(100.0, abs=0.1)


def test_profile_noise_excluded(
    sample_raw_df: pd.DataFrame, synthetic_X: np.ndarray
) -> None:
    """Noise points (label -1) must be excluded from the cluster profile."""
    labels = KMeans(n_clusters=3, n_init=5, random_state=42).fit_predict(synthetic_X)
    labels[:10] = -1  # inject noise
    feature_cols = ["Monetary"]
    profile = build_cluster_profile(sample_raw_df, labels, feature_cols)
    assert -1 not in profile["cluster"].values
    assert profile["n_customers"].sum() == (labels != -1).sum()
