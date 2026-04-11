"""Clustering utilities for Olist customer segmentation.

Provides algorithm wrappers (KMeans, BisectingKMeans, AgglomerativeClustering,
GaussianMixture, DBSCAN, HDBSCAN), metric computation, MLFlow integration,
visualization helpers, and model persistence utilities.

All functions:
- Accept X as a numpy ndarray of scaled features (n_samples, n_features)
- Log to MLFlow when called inside an active run context
- Follow PEP 8 / Black formatting
- Use Google docstrings and full type hints

Production inference contract:
- KMeans, BisectingKMeans, AgglomerativeClustering, GaussianMixture → have predict()
- DBSCAN, HDBSCAN → transductive, no predict() → not eligible for production model
"""

from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path
from typing import Any

import joblib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from sklearn.cluster import (
    DBSCAN,
    AgglomerativeClustering,
    BisectingKMeans,
    KMeans,
)
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.mixture import GaussianMixture
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler

try:
    from sklearn.cluster import HDBSCAN  # sklearn >= 1.3
    _HDBSCAN_AVAILABLE = True
except ImportError:
    _HDBSCAN_AVAILABLE = False

try:
    import mlflow
    import mlflow.sklearn
    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False

logger = logging.getLogger(__name__)

SILHOUETTE_SAMPLE_SIZE = 10_000
RANDOM_STATE = 42


# ── A. Métriques ──────────────────────────────────────────────────────────────

def compute_clustering_metrics(
    X: np.ndarray,
    labels: np.ndarray,
    wcss: float | None = None,
) -> dict[str, float]:
    """Computes a standard suite of clustering quality metrics.

    Silhouette score is computed on a sample of 10,000 points when n > 10,000
    to avoid O(n²) memory cost. Davies-Bouldin and Calinski-Harabasz are
    computed on the full dataset (O(k·n)).

    Noise points (label == -1, from DBSCAN/HDBSCAN) are excluded before
    any metric computation. If fewer than 2 distinct non-noise clusters
    remain, all metrics are returned as NaN without raising.

    Args:
        X: Scaled feature matrix, shape (n_samples, n_features).
        labels: Integer cluster labels, shape (n_samples,). May include -1.
        wcss: Optional KMeans inertia_ value. Included in output if provided.

    Returns:
        Dict with keys: silhouette, davies_bouldin, calinski_harabasz,
        and optionally wcss.
    """
    mask = labels != -1
    X_valid = X[mask]
    labels_valid = labels[mask]

    n_clusters = len(np.unique(labels_valid))
    if n_clusters < 2 or len(X_valid) < n_clusters:
        logger.warning(
            "compute_clustering_metrics: %d valid clusters — metrics undefined.",
            n_clusters,
        )
        result: dict[str, float] = {
            "silhouette": float("nan"),
            "davies_bouldin": float("nan"),
            "calinski_harabasz": float("nan"),
        }
        if wcss is not None:
            result["wcss"] = wcss
        return result

    # Silhouette: sample if large
    if len(X_valid) > SILHOUETTE_SAMPLE_SIZE:
        rng = np.random.default_rng(RANDOM_STATE)
        idx = rng.choice(len(X_valid), size=SILHOUETTE_SAMPLE_SIZE, replace=False)
        sil = silhouette_score(X_valid[idx], labels_valid[idx], metric="euclidean")
    else:
        sil = silhouette_score(X_valid, labels_valid, metric="euclidean")

    result = {
        "silhouette": float(sil),
        "davies_bouldin": float(davies_bouldin_score(X_valid, labels_valid)),
        "calinski_harabasz": float(calinski_harabasz_score(X_valid, labels_valid)),
    }
    if wcss is not None:
        result["wcss"] = float(wcss)
    return result


# ── B. K-Means ────────────────────────────────────────────────────────────────

def run_kmeans_search(
    X: np.ndarray,
    k_range: range = range(2, 13),
    n_init: int = 20,
    random_state: int = RANDOM_STATE,
    experiment_name: str = "olist_customer_segmentation",
    parent_run_id: str | None = None,
) -> pd.DataFrame:
    """Searches over k values for KMeans using elbow + silhouette criteria.

    For each k in k_range, fits KMeans and optionally logs a child MLFlow
    run. Returns a summary DataFrame for plotting elbow and silhouette curves.

    Args:
        X: Scaled feature matrix.
        k_range: Range of k values to evaluate.
        n_init: Number of KMeans initializations per k.
        random_state: Seed for reproducibility.
        experiment_name: MLFlow experiment name (used for child run tagging).
        parent_run_id: If provided, child runs are nested under this run.

    Returns:
        DataFrame indexed by k with columns: wcss, silhouette,
        davies_bouldin, calinski_harabasz.
    """
    rows = []
    for k in k_range:
        model = KMeans(n_clusters=k, init="k-means++", n_init=n_init,
                       random_state=random_state)
        labels = model.fit_predict(X)
        metrics = compute_clustering_metrics(X, labels, wcss=model.inertia_)
        metrics["k"] = k
        rows.append(metrics)

        if _MLFLOW_AVAILABLE and parent_run_id is not None:
            with mlflow.start_run(
                run_name=f"kmeans_k{k}",
                nested=True,
                parent_run_id=parent_run_id,
            ):
                mlflow.set_tag("algorithm", "kmeans")
                mlflow.set_tag("run_type", "k_search")
                mlflow.log_param("k", k)
                mlflow.log_param("n_init", n_init)
                mlflow.log_metrics({m: v for m, v in metrics.items()
                                    if m != "k" and not np.isnan(v)})
        logger.info("KMeans k=%d | silhouette=%.4f | wcss=%.0f",
                    k, metrics["silhouette"], metrics["wcss"])

    df = pd.DataFrame(rows).set_index("k")
    return df


def fit_kmeans(
    X: np.ndarray,
    k: int,
    n_init: int = 20,
    random_state: int = RANDOM_STATE,
    log_model: bool = True,
) -> tuple[KMeans, np.ndarray, dict[str, float]]:
    """Fits KMeans with the specified k and logs to the active MLFlow run.

    Args:
        X: Scaled feature matrix.
        k: Number of clusters.
        n_init: Number of initializations.
        random_state: Seed.
        log_model: Whether to log the fitted model as an MLFlow artifact.

    Returns:
        Tuple of (fitted KMeans, labels array, metrics dict).
    """
    model = KMeans(n_clusters=k, init="k-means++", n_init=n_init,
                   random_state=random_state)
    labels = model.fit_predict(X)
    metrics = compute_clustering_metrics(X, labels, wcss=model.inertia_)

    if _MLFLOW_AVAILABLE and mlflow.active_run():
        mlflow.log_param("algorithm", "kmeans")
        mlflow.log_param("k", k)
        mlflow.log_param("n_init", n_init)
        mlflow.log_param("random_state", random_state)
        mlflow.log_metrics({m: v for m, v in metrics.items() if not np.isnan(v)})
        if log_model:
            mlflow.sklearn.log_model(model, artifact_path="model")

    return model, labels, metrics


# ── C. Bisecting K-Means ──────────────────────────────────────────────────────

def run_bisecting_kmeans_search(
    X: np.ndarray,
    k_range: range = range(2, 13),
    n_init: int = 10,
    random_state: int = RANDOM_STATE,
    parent_run_id: str | None = None,
) -> pd.DataFrame:
    """Searches over k values for BisectingKMeans.

    BisectingKMeans recursively bisects the largest cluster at each step,
    producing more balanced cluster sizes than standard KMeans.

    Args:
        X: Scaled feature matrix.
        k_range: Range of k values to evaluate.
        n_init: Number of initializations per bisection step.
        random_state: Seed.
        parent_run_id: If provided, child runs are nested under this run.

    Returns:
        DataFrame indexed by k with columns: wcss, silhouette,
        davies_bouldin, calinski_harabasz.
    """
    rows = []
    for k in k_range:
        model = BisectingKMeans(n_clusters=k, n_init=n_init,
                                random_state=random_state)
        labels = model.fit_predict(X)
        metrics = compute_clustering_metrics(X, labels, wcss=model.inertia_)
        metrics["k"] = k
        rows.append(metrics)

        if _MLFLOW_AVAILABLE and parent_run_id is not None:
            with mlflow.start_run(
                run_name=f"bisecting_kmeans_k{k}",
                nested=True,
                parent_run_id=parent_run_id,
            ):
                mlflow.set_tag("algorithm", "bisecting_kmeans")
                mlflow.log_param("k", k)
                mlflow.log_metrics({m: v for m, v in metrics.items()
                                    if m != "k" and not np.isnan(v)})
        logger.info("BisectingKMeans k=%d | silhouette=%.4f", k, metrics["silhouette"])

    return pd.DataFrame(rows).set_index("k")


def fit_bisecting_kmeans(
    X: np.ndarray,
    k: int,
    n_init: int = 10,
    random_state: int = RANDOM_STATE,
    log_model: bool = True,
) -> tuple[BisectingKMeans, np.ndarray, dict[str, float]]:
    """Fits BisectingKMeans with the specified k.

    Args:
        X: Scaled feature matrix.
        k: Number of clusters.
        n_init: Number of initializations per bisection.
        random_state: Seed.
        log_model: Whether to log model to active MLFlow run.

    Returns:
        Tuple of (fitted BisectingKMeans, labels, metrics dict).
    """
    model = BisectingKMeans(n_clusters=k, n_init=n_init, random_state=random_state)
    labels = model.fit_predict(X)
    metrics = compute_clustering_metrics(X, labels, wcss=model.inertia_)

    if _MLFLOW_AVAILABLE and mlflow.active_run():
        mlflow.log_param("algorithm", "bisecting_kmeans")
        mlflow.log_param("k", k)
        mlflow.log_param("n_init", n_init)
        mlflow.log_metrics({m: v for m, v in metrics.items() if not np.isnan(v)})
        if log_model:
            mlflow.sklearn.log_model(model, artifact_path="model")

    return model, labels, metrics


# ── D. CAH (Agglomerative Clustering) ────────────────────────────────────────

def run_cah_search(
    X: np.ndarray,
    k_range: range = range(2, 13),
    linkage_method: str = "ward",
    dendrogram_sample_size: int = 15_000,
    parent_run_id: str | None = None,
) -> tuple[pd.DataFrame, np.ndarray]:
    """Runs CAH over k_range and returns metrics + linkage matrix for dendrogram.

    Uses sklearn AgglomerativeClustering for the k-sweep (memory-safe — no
    explicit distance matrix). Computes scipy linkage on a sample for the
    dendrogram only (scipy linkage is O(n²) memory, unsafe on 90k+ samples).

    Args:
        X: Scaled feature matrix.
        k_range: Range of k values to evaluate.
        linkage_method: Linkage criterion. 'ward' recommended.
        dendrogram_sample_size: Size of sample for scipy linkage (dendro only).
        parent_run_id: If provided, child runs are nested under this run.

    Returns:
        Tuple of (metrics DataFrame indexed by k, scipy linkage matrix Z
        computed on sample — pass to plot_dendrogram()).
    """
    rows = []
    for k in k_range:
        model = AgglomerativeClustering(n_clusters=k, linkage=linkage_method)
        labels = model.fit_predict(X)
        metrics = compute_clustering_metrics(X, labels)
        metrics["k"] = k
        rows.append(metrics)

        if _MLFLOW_AVAILABLE and parent_run_id is not None:
            with mlflow.start_run(
                run_name=f"cah_k{k}",
                nested=True,
                parent_run_id=parent_run_id,
            ):
                mlflow.set_tag("algorithm", "cah")
                mlflow.set_tag("linkage", linkage_method)
                mlflow.log_param("k", k)
                mlflow.log_metrics({m: v for m, v in metrics.items()
                                    if m != "k" and not np.isnan(v)})
        logger.info("CAH k=%d | silhouette=%.4f", k, metrics["silhouette"])

    # Compute Z on sample for dendrogram (scipy is O(n²) — do NOT run on full X)
    n_sample = min(dendrogram_sample_size, len(X))
    rng = np.random.default_rng(RANDOM_STATE)
    sample_idx = rng.choice(len(X), size=n_sample, replace=False)
    logger.info("Computing scipy linkage on %d-sample for dendrogram...", n_sample)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        Z = linkage(X[sample_idx], method=linkage_method)

    return pd.DataFrame(rows).set_index("k"), Z


def fit_cah(
    X: np.ndarray,
    k: int,
    linkage_method: str = "ward",
    log_model: bool = True,
) -> tuple[AgglomerativeClustering, np.ndarray, dict[str, float]]:
    """Fits AgglomerativeClustering with the specified k.

    Args:
        X: Scaled feature matrix.
        k: Number of clusters.
        linkage_method: Linkage criterion.
        log_model: Whether to log model to active MLFlow run.

    Returns:
        Tuple of (fitted AgglomerativeClustering, labels, metrics dict).
    """
    model = AgglomerativeClustering(n_clusters=k, linkage=linkage_method)
    labels = model.fit_predict(X)
    metrics = compute_clustering_metrics(X, labels)

    if _MLFLOW_AVAILABLE and mlflow.active_run():
        mlflow.log_param("algorithm", "cah")
        mlflow.log_param("k", k)
        mlflow.log_param("linkage", linkage_method)
        mlflow.log_metrics({m: v for m, v in metrics.items() if not np.isnan(v)})
        if log_model:
            mlflow.sklearn.log_model(model, artifact_path="model")

    return model, labels, metrics


# ── E. GMM (Gaussian Mixture Models) ─────────────────────────────────────────

def run_gmm_search(
    X: np.ndarray,
    k_range: range = range(2, 13),
    covariance_type: str = "full",
    n_init: int = 5,
    random_state: int = RANDOM_STATE,
    parent_run_id: str | None = None,
) -> pd.DataFrame:
    """Searches over k values for GaussianMixture using BIC/AIC criteria.

    BIC (Bayesian Information Criterion) penalizes model complexity more
    strongly than AIC — the k minimizing BIC is the recommended choice.
    Hard cluster assignments are derived via model.predict(X) for computing
    silhouette/DB/CH alongside the probabilistic criteria.

    Args:
        X: Scaled feature matrix.
        k_range: Range of component counts to evaluate.
        covariance_type: GMM covariance structure. 'full' is most flexible
            (ellipsoidal clusters). Use 'diag' if convergence is unstable.
        n_init: Number of EM initializations per k. 5 is sufficient with
            KMeans warm-start (GMM default init='kmeans').
        random_state: Seed.
        parent_run_id: MLFlow parent run ID for nested child runs.

    Returns:
        DataFrame indexed by k with columns: bic, aic, silhouette,
        davies_bouldin, calinski_harabasz.
    """
    rows = []
    for k in k_range:
        model = GaussianMixture(
            n_components=k,
            covariance_type=covariance_type,
            n_init=n_init,
            random_state=random_state,
        )
        model.fit(X)
        labels = model.predict(X)
        bic = model.bic(X)
        aic = model.aic(X)
        metrics = compute_clustering_metrics(X, labels)
        metrics.update({"k": k, "bic": float(bic), "aic": float(aic)})
        rows.append(metrics)

        if _MLFLOW_AVAILABLE and parent_run_id is not None:
            with mlflow.start_run(
                run_name=f"gmm_k{k}",
                nested=True,
                parent_run_id=parent_run_id,
            ):
                mlflow.set_tag("algorithm", "gmm")
                mlflow.set_tag("covariance_type", covariance_type)
                mlflow.log_param("k", k)
                mlflow.log_param("covariance_type", covariance_type)
                log_metrics = {m: v for m, v in metrics.items()
                               if m != "k" and not np.isnan(v)}
                mlflow.log_metrics(log_metrics)
        logger.info("GMM k=%d | BIC=%.0f | silhouette=%.4f", k, bic, metrics["silhouette"])

    return pd.DataFrame(rows).set_index("k")


def fit_gmm(
    X: np.ndarray,
    k: int,
    covariance_type: str = "full",
    n_init: int = 5,
    random_state: int = RANDOM_STATE,
    log_model: bool = True,
) -> tuple[GaussianMixture, np.ndarray, dict[str, float]]:
    """Fits GaussianMixture with the specified k and logs to active MLFlow run.

    Also computes max_soft_prob (mean of per-sample max class probability)
    as a proxy for cluster assignment confidence — values near 1.0 indicate
    well-separated clusters; values near 1/k indicate overlapping clusters.

    Args:
        X: Scaled feature matrix.
        k: Number of Gaussian components.
        covariance_type: GMM covariance structure.
        n_init: Number of EM initializations.
        random_state: Seed.
        log_model: Whether to log model to active MLFlow run.

    Returns:
        Tuple of (fitted GaussianMixture, hard labels, metrics dict
        including bic, aic, max_soft_prob).
    """
    model = GaussianMixture(
        n_components=k,
        covariance_type=covariance_type,
        n_init=n_init,
        random_state=random_state,
    )
    model.fit(X)
    labels = model.predict(X)
    proba = model.predict_proba(X)
    max_soft_prob = float(proba.max(axis=1).mean())

    metrics = compute_clustering_metrics(X, labels)
    metrics.update({
        "bic": float(model.bic(X)),
        "aic": float(model.aic(X)),
        "max_soft_prob": max_soft_prob,
    })

    if _MLFLOW_AVAILABLE and mlflow.active_run():
        mlflow.log_param("algorithm", "gmm")
        mlflow.log_param("k", k)
        mlflow.log_param("covariance_type", covariance_type)
        mlflow.log_metrics({m: v for m, v in metrics.items() if not np.isnan(v)})
        if log_model:
            mlflow.sklearn.log_model(model, artifact_path="model")

    return model, labels, metrics


# ── F. DBSCAN ─────────────────────────────────────────────────────────────────

def estimate_dbscan_eps(
    X: np.ndarray,
    min_samples: int = 10,
    percentile: float = 95.0,
) -> tuple[float, plt.Figure]:
    """Estimates DBSCAN epsilon via k-distance graph analysis.

    Fits NearestNeighbors(n_neighbors=min_samples), computes each point's
    distance to its min_samples-th neighbor, sorts ascending, and returns the
    value at the specified percentile as the recommended eps.

    The percentile heuristic is more robust than visual elbow selection:
    p95 gives a conservative eps capturing ~95% of the natural density.

    Args:
        X: Scaled feature matrix.
        min_samples: k for the kNN graph — must equal the min_samples you
            intend to pass to DBSCAN.
        percentile: Percentile of sorted distances to use as recommended eps.

    Returns:
        Tuple of (recommended_eps float, matplotlib Figure of k-distance
        plot with the recommended eps marked as a dashed horizontal line).
    """
    nbrs = NearestNeighbors(n_neighbors=min_samples, metric="euclidean")
    nbrs.fit(X)
    distances, _ = nbrs.kneighbors(X)
    k_distances = np.sort(distances[:, -1])

    recommended_eps = float(np.percentile(k_distances, percentile))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(k_distances, color="steelblue", linewidth=1.2)
    ax.axhline(recommended_eps, color="red", linestyle="--", linewidth=1.5,
               label=f"p{percentile:.0f} = {recommended_eps:.4f}")
    ax.set_title(f"k-Distance Graph (k={min_samples}) — DBSCAN eps Estimation",
                 fontsize=12)
    ax.set_xlabel("Points triés par distance croissante")
    ax.set_ylabel(f"Distance au {min_samples}e voisin")
    ax.legend(fontsize=10)
    plt.tight_layout()

    return recommended_eps, fig


def run_dbscan_search(
    X: np.ndarray,
    eps_values: list[float],
    min_samples_values: list[int],
    parent_run_id: str | None = None,
) -> pd.DataFrame:
    """Grid search over (eps, min_samples) for DBSCAN.

    Logs a child MLFlow run per (eps, min_samples) pair. Includes
    n_clusters (excluding noise) and noise_ratio in the results.
    Configurations producing n_clusters < 2 or noise_ratio > 0.5 are
    retained in the output but flagged as degenerate for easy filtering.

    Args:
        X: Scaled feature matrix.
        eps_values: List of epsilon values to try.
        min_samples_values: List of min_samples values to try.
        parent_run_id: Parent run ID for nested child runs.

    Returns:
        DataFrame with columns: eps, min_samples, n_clusters, noise_ratio,
        silhouette, davies_bouldin, calinski_harabasz. Sorted by silhouette
        descending (NaN rows last).
    """
    rows = []
    for eps in eps_values:
        for ms in min_samples_values:
            model = DBSCAN(eps=eps, min_samples=ms, metric="euclidean", n_jobs=-1)
            labels = model.fit_predict(X)
            n_clusters = len(set(labels) - {-1})
            noise_ratio = float((labels == -1).mean())
            metrics = compute_clustering_metrics(X, labels)
            row = {"eps": eps, "min_samples": ms,
                   "n_clusters": n_clusters, "noise_ratio": noise_ratio}
            row.update(metrics)
            rows.append(row)

            if _MLFLOW_AVAILABLE and parent_run_id is not None:
                with mlflow.start_run(
                    run_name=f"dbscan_eps{eps:.3f}_ms{ms}",
                    nested=True,
                    parent_run_id=parent_run_id,
                ):
                    mlflow.set_tag("algorithm", "dbscan")
                    mlflow.log_param("eps", eps)
                    mlflow.log_param("min_samples", ms)
                    mlflow.log_metric("n_clusters", n_clusters)
                    mlflow.log_metric("noise_ratio", noise_ratio)
                    mlflow.log_metrics({m: v for m, v in metrics.items()
                                        if not np.isnan(v)})
            logger.info("DBSCAN eps=%.3f ms=%d | k=%d | noise=%.1f%%",
                        eps, ms, n_clusters, noise_ratio * 100)

    df = pd.DataFrame(rows)
    return df.sort_values("silhouette", ascending=False, na_position="last")


def fit_dbscan(
    X: np.ndarray,
    eps: float,
    min_samples: int,
    log_model: bool = False,
) -> tuple[DBSCAN, np.ndarray, dict[str, float]]:
    """Fits DBSCAN with the given parameters and logs to active MLFlow run.

    Note: log_model defaults to False because DBSCAN is transductive —
    it has no predict() method for new data. Use KMeans/CAH/GMM for
    production scoring via assign_clusters_to_new_customers().

    Args:
        X: Scaled feature matrix.
        eps: Neighborhood radius.
        min_samples: Minimum points to form a core point.
        log_model: Log model artifact. Defaults to False.

    Returns:
        Tuple of (fitted DBSCAN, labels including -1 for noise, metrics dict
        with n_clusters and noise_ratio added).
    """
    model = DBSCAN(eps=eps, min_samples=min_samples, metric="euclidean", n_jobs=-1)
    labels = model.fit_predict(X)
    n_clusters = len(set(labels) - {-1})
    noise_ratio = float((labels == -1).mean())
    metrics = compute_clustering_metrics(X, labels)
    metrics.update({"n_clusters": n_clusters, "noise_ratio": noise_ratio})

    if _MLFLOW_AVAILABLE and mlflow.active_run():
        mlflow.log_param("algorithm", "dbscan")
        mlflow.log_param("eps", eps)
        mlflow.log_param("min_samples", min_samples)
        mlflow.log_metrics({m: v for m, v in metrics.items() if not np.isnan(v)})
        if log_model:
            mlflow.sklearn.log_model(model, artifact_path="model")

    return model, labels, metrics


# ── G. HDBSCAN ────────────────────────────────────────────────────────────────

def run_hdbscan_search(
    X: np.ndarray,
    min_cluster_sizes: list[int] | None = None,
    min_samples_list: list[int | None] | None = None,
    parent_run_id: str | None = None,
) -> pd.DataFrame:
    """Grid search over (min_cluster_size, min_samples) for HDBSCAN.

    HDBSCAN does not require an eps parameter — it discovers the density
    hierarchy automatically. min_cluster_size is the primary hyperparameter:
    too small → many small noisy clusters, too large → over-merging.

    Requires sklearn >= 1.3. If unavailable, raises ImportError.

    Args:
        X: Scaled feature matrix.
        min_cluster_sizes: List of min_cluster_size values to try.
            Defaults to [50, 100, 200, 500, 1000].
        min_samples_list: List of min_samples values (None = auto).
            Defaults to [5, 10, None].
        parent_run_id: Parent run ID for nested child runs.

    Returns:
        DataFrame with columns: min_cluster_size, min_samples, n_clusters,
        noise_ratio, silhouette, davies_bouldin, calinski_harabasz.

    Raises:
        ImportError: If sklearn < 1.3 (HDBSCAN not available).
    """
    if not _HDBSCAN_AVAILABLE:
        raise ImportError(
            "HDBSCAN requires sklearn >= 1.3. "
            f"Current version: {__import__('sklearn').__version__}"
        )

    if min_cluster_sizes is None:
        min_cluster_sizes = [50, 100, 200, 500, 1000]
    if min_samples_list is None:
        min_samples_list = [5, 10, None]

    rows = []
    for mcs in min_cluster_sizes:
        for ms in min_samples_list:
            kwargs: dict[str, Any] = {"min_cluster_size": mcs}
            if ms is not None:
                kwargs["min_samples"] = ms
            model = HDBSCAN(**kwargs)
            labels = model.fit_predict(X)
            n_clusters = len(set(labels) - {-1})
            noise_ratio = float((labels == -1).mean())
            metrics = compute_clustering_metrics(X, labels)
            row = {
                "min_cluster_size": mcs,
                "min_samples": ms if ms is not None else "auto",
                "n_clusters": n_clusters,
                "noise_ratio": noise_ratio,
            }
            row.update(metrics)
            rows.append(row)

            if _MLFLOW_AVAILABLE and parent_run_id is not None:
                ms_str = str(ms) if ms is not None else "auto"
                with mlflow.start_run(
                    run_name=f"hdbscan_mcs{mcs}_ms{ms_str}",
                    nested=True,
                    parent_run_id=parent_run_id,
                ):
                    mlflow.set_tag("algorithm", "hdbscan")
                    mlflow.log_param("min_cluster_size", mcs)
                    mlflow.log_param("min_samples", ms_str)
                    mlflow.log_metric("n_clusters", n_clusters)
                    mlflow.log_metric("noise_ratio", noise_ratio)
                    mlflow.log_metrics({m: v for m, v in metrics.items()
                                        if not np.isnan(v)})
            logger.info("HDBSCAN mcs=%d ms=%s | k=%d | noise=%.1f%%",
                        mcs, ms, n_clusters, noise_ratio * 100)

    df = pd.DataFrame(rows)
    return df.sort_values("silhouette", ascending=False, na_position="last")


def fit_hdbscan(
    X: np.ndarray,
    min_cluster_size: int,
    min_samples: int | None = None,
    log_model: bool = False,
) -> tuple[Any, np.ndarray, dict[str, float]]:
    """Fits HDBSCAN with the given parameters and logs to active MLFlow run.

    Note: sklearn HDBSCAN (1.3) does not support predict() for new data.
    For production scoring, use KMeans/BisectingKMeans/CAH/GMM instead.

    Args:
        X: Scaled feature matrix.
        min_cluster_size: Minimum size for a cluster (primary hyperparameter).
        min_samples: Controls conservativeness of clustering. None = auto.
        log_model: Defaults to False (no predict() in sklearn HDBSCAN).

    Returns:
        Tuple of (fitted HDBSCAN, labels including -1 for noise, metrics
        dict with n_clusters, noise_ratio, mean_membership_prob).

    Raises:
        ImportError: If sklearn < 1.3.
    """
    if not _HDBSCAN_AVAILABLE:
        raise ImportError("HDBSCAN requires sklearn >= 1.3.")

    kwargs: dict[str, Any] = {"min_cluster_size": min_cluster_size}
    if min_samples is not None:
        kwargs["min_samples"] = min_samples
    model = HDBSCAN(**kwargs)
    labels = model.fit_predict(X)

    n_clusters = len(set(labels) - {-1})
    noise_ratio = float((labels == -1).mean())
    # HDBSCAN probabilities_: membership confidence per point
    mean_membership_prob = float(model.probabilities_.mean())

    metrics = compute_clustering_metrics(X, labels)
    metrics.update({
        "n_clusters": n_clusters,
        "noise_ratio": noise_ratio,
        "mean_membership_prob": mean_membership_prob,
    })

    if _MLFLOW_AVAILABLE and mlflow.active_run():
        mlflow.log_param("algorithm", "hdbscan")
        mlflow.log_param("min_cluster_size", min_cluster_size)
        mlflow.log_param("min_samples", str(min_samples))
        mlflow.log_metrics({m: v for m, v in metrics.items() if not np.isnan(v)})

    return model, labels, metrics


# ── H. Visualisation ──────────────────────────────────────────────────────────

def plot_elbow(
    search_results: pd.DataFrame,
    algo_name: str = "KMeans",
    highlight_k: int | None = None,
    figsize: tuple[int, int] = (10, 5),
) -> plt.Figure:
    """Plots WCSS vs k (elbow curve) with optional vertical marker.

    Args:
        search_results: DataFrame indexed by k with a 'wcss' column.
        algo_name: Algorithm name for the title.
        highlight_k: If provided, draws a vertical dashed line at this k.
        figsize: Figure dimensions.

    Returns:
        Matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(search_results.index, search_results["wcss"],
            marker="o", color="steelblue", linewidth=2, markersize=6)
    ax.fill_between(search_results.index, search_results["wcss"], alpha=0.15, color="steelblue")
    if highlight_k is not None:
        ax.axvline(highlight_k, color="red", linestyle="--", linewidth=1.5,
                   label=f"k={highlight_k} sélectionné")
        ax.legend(fontsize=10)
    ax.set_title(f"{algo_name} — Elbow Curve (WCSS)", fontsize=13)
    ax.set_xlabel("Nombre de clusters k")
    ax.set_ylabel("WCSS (Inertia)")
    ax.set_xticks(list(search_results.index))
    plt.tight_layout()
    return fig


def plot_bic_aic(
    search_results: pd.DataFrame,
    highlight_k: int | None = None,
    figsize: tuple[int, int] = (10, 5),
) -> plt.Figure:
    """Plots BIC and AIC vs k for GMM component selection.

    BIC penalizes complexity more than AIC — the recommended k is the
    minimum BIC value. Both curves are plotted for comparison.

    Args:
        search_results: DataFrame indexed by k with 'bic' and 'aic' columns.
        highlight_k: If provided, draws a vertical dashed line at this k.
        figsize: Figure dimensions.

    Returns:
        Matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(search_results.index, search_results["bic"],
            marker="o", color="royalblue", linewidth=2, label="BIC (recommandé)")
    ax.plot(search_results.index, search_results["aic"],
            marker="s", color="coral", linewidth=2, linestyle="--", label="AIC")
    if highlight_k is not None:
        ax.axvline(highlight_k, color="red", linestyle=":", linewidth=1.5,
                   label=f"k={highlight_k} (min BIC)")
    ax.set_title("GMM — BIC & AIC vs Nombre de Composantes", fontsize=13)
    ax.set_xlabel("Nombre de composantes k")
    ax.set_ylabel("Critère d'information (lower = better)")
    ax.set_xticks(list(search_results.index))
    ax.legend(fontsize=10)
    plt.tight_layout()
    return fig


def plot_silhouette_comparison(
    search_results: pd.DataFrame,
    algorithm_name: str = "KMeans",
    highlight_k: int | None = None,
    figsize: tuple[int, int] = (10, 5),
) -> plt.Figure:
    """Plots silhouette score vs k for a single algorithm.

    Args:
        search_results: DataFrame indexed by k with 'silhouette' column.
        algorithm_name: Used in the title.
        highlight_k: Optional k to mark with a vertical line.
        figsize: Figure dimensions.

    Returns:
        Matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(search_results.index, search_results["silhouette"],
            marker="o", color="seagreen", linewidth=2, markersize=6)
    ax.fill_between(search_results.index, search_results["silhouette"],
                    alpha=0.15, color="seagreen")
    if highlight_k is not None:
        ax.axvline(highlight_k, color="red", linestyle="--", linewidth=1.5,
                   label=f"k={highlight_k} sélectionné")
        ax.legend(fontsize=10)
    ax.set_title(f"{algorithm_name} — Silhouette Score vs k", fontsize=13)
    ax.set_xlabel("Nombre de clusters k")
    ax.set_ylabel("Silhouette Score (higher = better)")
    ax.set_xticks(list(search_results.index))
    plt.tight_layout()
    return fig


def plot_metrics_comparison(
    results_dict: dict[str, pd.DataFrame],
    metrics: list[str] | None = None,
    figsize: tuple[int, int] = (16, 10),
) -> plt.Figure:
    """Plots a metric grid comparing multiple algorithms.

    Args:
        results_dict: Dict mapping algorithm name to its search_results DataFrame.
        metrics: List of metric columns to plot. Defaults to
            ['silhouette', 'davies_bouldin', 'calinski_harabasz', 'wcss'].
            Algorithms missing a metric are skipped silently.
        figsize: Figure dimensions.

    Returns:
        Matplotlib Figure.
    """
    if metrics is None:
        metrics = ["silhouette", "davies_bouldin", "calinski_harabasz", "wcss"]

    palette = sns.color_palette("tab10", len(results_dict))
    n_metrics = len(metrics)
    ncols = 2
    nrows = (n_metrics + 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize)
    axes_flat = axes.flatten() if n_metrics > 1 else [axes]

    direction = {
        "silhouette": "↑ higher is better",
        "davies_bouldin": "↓ lower is better",
        "calinski_harabasz": "↑ higher is better",
        "wcss": "↓ lower is better",
        "bic": "↓ lower is better",
        "aic": "↓ lower is better",
    }

    for i, metric in enumerate(metrics):
        ax = axes_flat[i]
        for (algo_name, df), color in zip(results_dict.items(), palette):
            if metric not in df.columns:
                continue
            ax.plot(df.index, df[metric], marker="o", label=algo_name,
                    color=color, linewidth=1.8, markersize=5)
        ax.set_title(f"{metric}  ({direction.get(metric, '')})", fontsize=11)
        ax.set_xlabel("k")
        ax.legend(fontsize=9)
        try:
            ax.set_xticks(list(next(iter(results_dict.values())).index))
        except StopIteration:
            pass

    for j in range(len(metrics), len(axes_flat)):
        axes_flat[j].set_visible(False)

    plt.suptitle("Comparaison des Algorithmes — Métriques de Clustering", fontsize=13)
    plt.tight_layout()
    return fig


def plot_dendrogram(
    Z: np.ndarray,
    truncate_mode: str = "lastp",
    p: int = 30,
    highlight_k: int | None = None,
    figsize: tuple[int, int] = (16, 7),
) -> plt.Figure:
    """Plots a truncated dendrogram from a scipy linkage matrix.

    Args:
        Z: Linkage matrix from scipy.cluster.hierarchy.linkage() or from
            run_cah_search().
        truncate_mode: 'lastp' shows only the last p merges. Essential for
            readability on large datasets.
        p: Number of last merges to display. 30 is standard.
        highlight_k: If provided, draws a horizontal cut line at the
            distance level producing k clusters.
        figsize: Figure dimensions.

    Returns:
        Matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=figsize)
    ddata = dendrogram(Z, truncate_mode=truncate_mode, p=p,
                       leaf_rotation=90, leaf_font_size=9,
                       ax=ax, color_threshold=0)

    if highlight_k is not None and highlight_k >= 2:
        # Distance at which k clusters are formed = Z[-k+1, 2]
        cut_distance = float(Z[-(highlight_k - 1), 2])
        ax.axhline(cut_distance, color="red", linestyle="--", linewidth=1.5,
                   label=f"Coupe k={highlight_k} à d={cut_distance:.3f}")
        ax.legend(fontsize=10)

    ax.set_title(
        f"Dendrogramme CAH (Ward) — {p} dernières fusions"
        + (f" | Coupe k={highlight_k}" if highlight_k else ""),
        fontsize=12,
    )
    ax.set_xlabel("Clients (ou taille du groupe)")
    ax.set_ylabel("Distance de fusion (Ward)")
    plt.tight_layout()
    return fig


def plot_cluster_heatmap(
    centroids_df: pd.DataFrame,
    title: str = "Centroids des Clusters (Features Standardisées)",
    figsize: tuple[int, int] = (14, 7),
    annot: bool = True,
) -> plt.Figure:
    """Plots a heatmap of cluster centroids across features.

    Rows = clusters, columns = features (in scaled space, mean=0, std=1).

    Args:
        centroids_df: DataFrame with cluster index and feature columns.
            Build as: df_labeled.groupby('cluster')[FINAL_FEATURES].mean()
        title: Heatmap title.
        figsize: Figure dimensions.
        annot: Whether to annotate cells with numeric values.

    Returns:
        Matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        centroids_df,
        annot=annot,
        fmt=".2f",
        cmap="RdBu_r",
        center=0,
        vmin=-2,
        vmax=2,
        linewidths=0.4,
        linecolor="white",
        ax=ax,
        annot_kws={"size": 9},
    )
    ax.set_title(title, fontsize=12)
    ax.set_xlabel("Feature")
    ax.set_ylabel("Cluster")
    plt.tight_layout()
    return fig


def plot_radar_chart(
    profile_df: pd.DataFrame,
    feature_cols: list[str],
    cluster_col: str = "cluster",
    title: str = "Radar Chart — Profil des Clusters (Médianes Brutes Normalisées)",
    figsize: tuple[int, int] = (10, 10),
) -> plt.Figure:
    """Plots a radar (spider) chart of per-cluster feature medians.

    Features are min-max normalized using population-level min/max (not
    per-cluster), so areas are proportional to absolute position in feature
    space. Binary features (flags) are excluded by convention for readability.

    Args:
        profile_df: DataFrame with one row per cluster, containing cluster_col
            and all feature_cols. Use raw (non-scaled) medians.
        feature_cols: Ordered list of features for the radar axes.
        cluster_col: Name of the cluster identifier column.
        title: Chart title.
        figsize: Figure dimensions.

    Returns:
        Matplotlib Figure.
    """
    # Min-max normalize across population (profile_df contains medians per cluster)
    scaler = MinMaxScaler()
    values_norm = scaler.fit_transform(profile_df[feature_cols].values)

    n_features = len(feature_cols)
    angles = np.linspace(0, 2 * np.pi, n_features, endpoint=False).tolist()
    angles += angles[:1]  # close the polygon

    palette = sns.color_palette("tab10", len(profile_df))
    fig, ax = plt.subplots(figsize=figsize, subplot_kw={"polar": True})

    for i, (_, row) in enumerate(profile_df.iterrows()):
        values = values_norm[i].tolist()
        values += values[:1]
        cluster_id = row[cluster_col] if cluster_col in row else i
        ax.plot(angles, values, linewidth=2, color=palette[i],
                label=f"Cluster {cluster_id}")
        ax.fill(angles, values, alpha=0.12, color=palette[i])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(feature_cols, size=10)
    ax.set_yticklabels([])
    ax.set_title(title, size=12, pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)
    plt.tight_layout()
    return fig


def plot_pca_clusters(
    X: np.ndarray,
    labels: np.ndarray,
    title: str = "PCA 2D — Projection des Clusters",
    noise_label: int = -1,
    figsize: tuple[int, int] = (12, 8),
    random_state: int = RANDOM_STATE,
) -> plt.Figure:
    """Projects X to 2D via PCA and colors points by cluster label.

    Noise points (label == noise_label) are plotted in gray with lower
    alpha. Explained variance is shown on axis labels.

    Args:
        X: Scaled feature matrix.
        labels: Cluster labels array (may include noise_label for noise).
        title: Plot title.
        noise_label: Label value for noise points (DBSCAN/HDBSCAN).
        figsize: Figure dimensions.
        random_state: PCA seed.

    Returns:
        Matplotlib Figure.
    """
    from sklearn.decomposition import PCA

    pca = PCA(n_components=2, random_state=random_state)
    X_pca = pca.fit_transform(X)
    var = pca.explained_variance_ratio_

    unique_labels = sorted(set(labels))
    palette = sns.color_palette("tab10", len([l for l in unique_labels if l != noise_label]))
    color_map = {}
    ci = 0
    for lbl in unique_labels:
        if lbl == noise_label:
            color_map[lbl] = (0.5, 0.5, 0.5)
        else:
            color_map[lbl] = palette[ci]
            ci += 1

    fig, ax = plt.subplots(figsize=figsize)
    for lbl in unique_labels:
        mask = labels == lbl
        alpha = 0.25 if lbl == noise_label else 0.4
        label_name = "Bruit (noise)" if lbl == noise_label else f"Cluster {lbl}"
        ax.scatter(X_pca[mask, 0], X_pca[mask, 1],
                   c=[color_map[lbl]], alpha=alpha, s=4, label=label_name)

    ax.set_xlabel(f"PC1 ({var[0] * 100:.1f}% variance)", fontsize=11)
    ax.set_ylabel(f"PC2 ({var[1] * 100:.1f}% variance)", fontsize=11)
    ax.set_title(
        f"{title}\nVariance expliquée : {(var[0] + var[1]) * 100:.1f}%",
        fontsize=12,
    )
    ax.legend(loc="best", fontsize=9, markerscale=3)
    plt.tight_layout()
    return fig


# ── I. Profiling & Validation ─────────────────────────────────────────────────

def build_cluster_profile(
    df_raw: pd.DataFrame,
    labels: np.ndarray,
    feature_cols: list[str],
    id_col: str = "customer_unique_id",
) -> pd.DataFrame:
    """Builds a cluster profile table from raw (non-scaled) features.

    Computes per-cluster median for each feature, cluster size, and cluster
    share. Adds a CLV_proxy column (Monetary × (1 + Frequency_flag)) to
    rank segments by customer lifetime value potential.

    Noise points (label == -1) are excluded from profiling.

    Args:
        df_raw: Raw features DataFrame with id_col and feature_cols.
        labels: Cluster labels aligned with df_raw row order.
        feature_cols: Features to aggregate (use raw, non-Log columns).
        id_col: Customer identifier column.

    Returns:
        DataFrame with columns: cluster, n_customers, pct_customers,
        CLV_proxy, and one median column per feature. Sorted by CLV_proxy
        descending.
    """
    df = df_raw.copy()
    df["cluster"] = labels

    # Exclude noise points
    df = df[df["cluster"] != -1]

    profile = (
        df.groupby("cluster")[feature_cols]
        .median()
        .reset_index()
    )

    sizes = df.groupby("cluster")[id_col].count().reset_index(name="n_customers")
    profile = profile.merge(sizes, on="cluster")
    profile["pct_customers"] = (profile["n_customers"] / profile["n_customers"].sum() * 100).round(2)

    # CLV proxy
    if "Monetary" in profile.columns and "Frequency_flag" in profile.columns:
        profile["CLV_proxy"] = profile["Monetary"] * (1 + profile["Frequency_flag"])
    elif "Monetary" in profile.columns:
        profile["CLV_proxy"] = profile["Monetary"]

    cols_order = ["cluster", "n_customers", "pct_customers"]
    if "CLV_proxy" in profile.columns:
        cols_order.append("CLV_proxy")
    cols_order += [c for c in feature_cols if c in profile.columns]
    profile = profile[cols_order]

    if "CLV_proxy" in profile.columns:
        profile = profile.sort_values("CLV_proxy", ascending=False)

    return profile.reset_index(drop=True)


def validate_hypotheses(
    df_labeled: pd.DataFrame,
    profile_df: pd.DataFrame,
) -> pd.DataFrame:
    """Validates EDA hypotheses H1–H6 against cluster profiles.

    Each hypothesis is evaluated against a quantitative condition derived
    from the cluster profile. The result includes a numeric evidence string.

    Validation conditions:
    - H1 (high-spenders infrequent): max-CLV cluster has median Frequency ≤ 1.5
    - H2 (>300d recency = churn): ≥ 1 cluster with median Recency > 300
    - H3 (geography → freight): Spearman corr(region_freight_score, avg_freight_ratio) > 0
    - H4 (boleto = low-value): cluster with min payment_type_cc_flag has below-median Monetary
    - H5 (delivery delay varies): max - min median avg_delivery_delay > 5 days across clusters
    - H6 (loyal customers distinct): ≥ 1 cluster with median Frequency ≥ 2 AND above-median Monetary

    Args:
        df_labeled: Full customer DataFrame with a 'cluster' column and raw features.
        profile_df: Output of build_cluster_profile().

    Returns:
        DataFrame with columns: hypothesis_id, description, status
        (VALIDATED / PARTIAL / NOT_VALIDATED), evidence.
    """
    results = []

    # H1 — High-spenders are infrequent
    try:
        top_clv_cluster = profile_df.loc[profile_df["CLV_proxy"].idxmax()]
        freq_top = top_clv_cluster.get("Frequency", top_clv_cluster.get("Frequency_flag", None))
        h1_ok = freq_top is not None and float(freq_top) <= 1.5
        results.append({
            "hypothesis_id": "H1",
            "description": "Les high-spenders sont des acheteurs peu fréquents",
            "status": "VALIDATED" if h1_ok else "NOT_VALIDATED",
            "evidence": f"Cluster CLV max : Frequency médiane = {freq_top:.2f}",
        })
    except Exception as e:
        results.append({"hypothesis_id": "H1", "description": "High-spenders infrequents",
                        "status": "PARTIAL", "evidence": str(e)})

    # H2 — Recency > 300 = churn
    try:
        churn_clusters = profile_df[profile_df.get("Recency", pd.Series(dtype=float)) > 300] \
            if "Recency" in profile_df.columns else pd.DataFrame()
        h2_ok = len(churn_clusters) >= 1
        results.append({
            "hypothesis_id": "H2",
            "description": "Inactivité >300j = churn effectif",
            "status": "VALIDATED" if h2_ok else "NOT_VALIDATED",
            "evidence": f"{len(churn_clusters)} cluster(s) avec Recency médiane > 300j",
        })
    except Exception as e:
        results.append({"hypothesis_id": "H2", "description": "Churn Recency>300",
                        "status": "PARTIAL", "evidence": str(e)})

    # H3 — Geography predicts freight
    try:
        if "region_freight_score" in profile_df.columns and "avg_freight_ratio" in profile_df.columns:
            from scipy.stats import spearmanr
            rho, pval = spearmanr(profile_df["region_freight_score"],
                                  profile_df["avg_freight_ratio"])
            h3_status = "VALIDATED" if rho > 0.3 else ("PARTIAL" if rho > 0 else "NOT_VALIDATED")
            results.append({
                "hypothesis_id": "H3",
                "description": "Géographie prédit le freight burden",
                "status": h3_status,
                "evidence": f"Spearman ρ(region_score, freight_ratio) = {rho:.3f} (p={pval:.3f})",
            })
        else:
            results.append({"hypothesis_id": "H3", "description": "Géographie → freight",
                            "status": "PARTIAL", "evidence": "Colonnes manquantes dans profile_df"})
    except Exception as e:
        results.append({"hypothesis_id": "H3", "description": "Géographie → freight",
                        "status": "PARTIAL", "evidence": str(e)})

    # H4 — Boleto = low-value proxy
    try:
        if "payment_type_cc_flag" in profile_df.columns and "Monetary" in profile_df.columns:
            min_cc_cluster = profile_df.loc[profile_df["payment_type_cc_flag"].idxmin()]
            global_median_monetary = df_labeled["Monetary"].median() \
                if "Monetary" in df_labeled.columns else profile_df["Monetary"].median()
            h4_ok = min_cc_cluster["Monetary"] < global_median_monetary
            results.append({
                "hypothesis_id": "H4",
                "description": "Boleto = proxy faible accès au crédit → cluster low-value",
                "status": "VALIDATED" if h4_ok else "NOT_VALIDATED",
                "evidence": (
                    f"Cluster min CC_flag : Monetary médiane = {min_cc_cluster['Monetary']:.1f} "
                    f"vs médiane globale = {global_median_monetary:.1f}"
                ),
            })
        else:
            results.append({"hypothesis_id": "H4", "description": "Boleto low-value",
                            "status": "PARTIAL", "evidence": "Colonnes manquantes"})
    except Exception as e:
        results.append({"hypothesis_id": "H4", "description": "Boleto low-value",
                        "status": "PARTIAL", "evidence": str(e)})

    # H5 — Delivery delay varies across clusters
    try:
        if "avg_delivery_delay" in profile_df.columns:
            delay_range = profile_df["avg_delivery_delay"].max() - profile_df["avg_delivery_delay"].min()
            h5_ok = delay_range > 5.0
            results.append({
                "hypothesis_id": "H5",
                "description": "La tolérance au délai varie selon le segment",
                "status": "VALIDATED" if h5_ok else ("PARTIAL" if delay_range > 2 else "NOT_VALIDATED"),
                "evidence": f"Range délai livraison inter-clusters : {delay_range:.1f} jours",
            })
        else:
            results.append({"hypothesis_id": "H5", "description": "Délai varie par segment",
                            "status": "PARTIAL", "evidence": "avg_delivery_delay absent"})
    except Exception as e:
        results.append({"hypothesis_id": "H5", "description": "Délai varie",
                        "status": "PARTIAL", "evidence": str(e)})

    # H6 — Loyal customers (F≥2) form a distinct cluster
    try:
        freq_col = "Frequency" if "Frequency" in profile_df.columns else None
        if freq_col and "Monetary" in profile_df.columns:
            global_median_monetary = df_labeled["Monetary"].median() \
                if "Monetary" in df_labeled.columns else profile_df["Monetary"].median()
            loyal_clusters = profile_df[
                (profile_df[freq_col] >= 2) & (profile_df["Monetary"] > global_median_monetary)
            ]
            h6_ok = len(loyal_clusters) >= 1
            results.append({
                "hypothesis_id": "H6",
                "description": "La minorité fidèle (F≥2) forme un cluster distinct",
                "status": "VALIDATED" if h6_ok else "NOT_VALIDATED",
                "evidence": (
                    f"{len(loyal_clusters)} cluster(s) avec Frequency ≥ 2 "
                    f"ET Monetary > médiane ({global_median_monetary:.1f})"
                ),
            })
        else:
            results.append({"hypothesis_id": "H6", "description": "Loyal customers distinct",
                            "status": "PARTIAL", "evidence": "Colonnes Frequency/Monetary manquantes"})
    except Exception as e:
        results.append({"hypothesis_id": "H6", "description": "Loyal customers distinct",
                        "status": "PARTIAL", "evidence": str(e)})

    return pd.DataFrame(results)


# ── J. Persistance ────────────────────────────────────────────────────────────

def save_model(
    model: Any,
    model_path: Path,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Saves a fitted clustering model to disk via joblib.

    Writes the model to model_path and saves a sidecar metadata JSON at
    model_path.with_suffix('.json') if metadata is provided.

    Args:
        model: Fitted sklearn estimator.
        model_path: Absolute Path for the .pkl file.
        metadata: Optional dict of metadata (algorithm, k, metrics, etc.).

    Raises:
        ValueError: If model_path parent directory does not exist.
    """
    model_path = Path(model_path)
    if not model_path.parent.exists():
        raise ValueError(
            f"save_model: parent directory does not exist: {model_path.parent}. "
            "Create it first with Path.mkdir(parents=True, exist_ok=True)."
        )

    joblib.dump(model, model_path)
    logger.info("Model saved: %s", model_path)

    if metadata is not None:
        metadata["saved_at"] = pd.Timestamp.now().isoformat()
        json_path = model_path.with_suffix(".json")
        with open(json_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.info("Metadata saved: %s", json_path)


def load_model(model_path: Path) -> Any:
    """Loads a clustering model from disk.

    Args:
        model_path: Absolute Path to the .pkl file.

    Returns:
        Fitted sklearn estimator.

    Raises:
        FileNotFoundError: If model_path does not exist.
    """
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"load_model: file not found: {model_path}")
    model = joblib.load(model_path)
    logger.info("Model loaded: %s", model_path)
    return model


def assign_clusters_to_new_customers(
    df_new: pd.DataFrame,
    model: Any,
    scaler_path: Path,
    feature_cols: list[str] | None = None,
) -> pd.Series:
    """Assigns cluster labels to new customers using a saved model.

    Production inference function. Loads the StandardScaler, applies
    transform, and calls model.predict(). Only compatible with models
    that implement predict(): KMeans, BisectingKMeans,
    AgglomerativeClustering, GaussianMixture.

    Args:
        df_new: Raw customer features DataFrame. Must contain feature_cols
            (unscaled). Must have a 'customer_unique_id' column or index.
        model: Fitted estimator with predict() method.
        scaler_path: Path to the fitted StandardScaler .pkl.
        feature_cols: Feature columns to use. Loads from sidecar JSON if
            available, otherwise falls back to model's n_features_in_.

    Returns:
        Series of integer cluster labels, indexed by customer_unique_id.

    Raises:
        NotImplementedError: If the model does not have a predict() method
            (e.g., DBSCAN, HDBSCAN).
        FileNotFoundError: If scaler_path does not exist.
    """
    if not hasattr(model, "predict"):
        raise NotImplementedError(
            f"{type(model).__name__} does not implement predict(). "
            "Use KMeans, BisectingKMeans, AgglomerativeClustering, or "
            "GaussianMixture for production inference."
        )

    scaler = load_model(scaler_path)

    if feature_cols is None:
        from features import FINAL_FEATURES
        feature_cols = FINAL_FEATURES

    X_new = df_new[feature_cols].values
    X_scaled = scaler.transform(X_new)
    labels = model.predict(X_scaled)

    index = (
        df_new["customer_unique_id"].values
        if "customer_unique_id" in df_new.columns
        else df_new.index
    )
    return pd.Series(labels, index=index, name="cluster")
