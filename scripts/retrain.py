"""Retrain pipeline — Neon PostgreSQL → features → UMAP+KMeans → GCS.

Pulls fresh data from Neon, runs the full training pipeline, compares the new
silhouette against the current production model (fetched from GCS metadata).
Uploads new artifacts to GCS only if the model improves.

Usage:
    python scripts/retrain.py [--force]

Options:
    --force    Upload artifacts even if silhouette does not improve.

Exit codes:
    0  Artifacts updated and uploaded to GCS.
    1  No update — current model is still best.
    2  Error during training.
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.cluster import KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import StandardScaler

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")
sys.path.insert(0, str(_PROJECT_ROOT))

from src.artifact_store import get_gcs_metadata, upload_artifacts
from src.data_loader import get_db_engine, get_merged_dataframe, get_customer_aggregation
from src.features import OUTLIER_BOUNDS, REGION_FREIGHT_ORDER, STATE_REGION

_PROFILE_COLS = [
    "Recency", "Monetary", "Frequency",
    "avg_freight_ratio", "avg_delivery_delay", "avg_review_score",
    "payment_type_cc_flag", "avg_installments", "region_freight_score",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

try:
    import umap as umap_module
    _UMAP_AVAILABLE = True
except ImportError:
    _UMAP_AVAILABLE = False
    logger.warning("umap-learn not installed — falling back to pure RFM KMeans")

try:
    import mlflow
    _MLFLOW_AVAILABLE = True
except ImportError:
    _MLFLOW_AVAILABLE = False

_MODELS_DIR = _PROJECT_ROOT / "models"
_PROCESSED = _PROJECT_ROOT / "data" / "processed"
_MODELS_DIR.mkdir(parents=True, exist_ok=True)
_PROCESSED.mkdir(parents=True, exist_ok=True)

_RFM_FEATURES = ["Recency", "Frequency", "Monetary"]
_SILHOUETTE_TOLERANCE = 0.005  # minimum improvement to trigger an update


# ── Feature engineering from PostgreSQL ──────────────────────────────────────


def _build_features_from_db() -> pd.DataFrame:
    """Pull data from Neon and build the raw customer feature store."""
    logger.info("Connecting to Neon PostgreSQL…")
    engine = get_db_engine()

    logger.info("Fetching aggregated customer data…")
    df_agg = get_customer_aggregation(engine)

    logger.info("Fetching merged order/item/payment/review data…")
    df_master = get_merged_dataframe(engine)

    pay_raw = pd.read_sql_table("olist_order_payments", engine)

    # ── Datetime columns ──────────────────────────────────────────────────────
    dt_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in dt_cols:
        df_master[col] = pd.to_datetime(df_master[col], errors="coerce")

    df_master["actual_lead_time_days"] = (
        df_master["order_delivered_customer_date"] - df_master["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    df_master["estimated_lead_time_days"] = (
        df_master["order_estimated_delivery_date"] - df_master["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    df_master["delivery_delay_days"] = (
        df_master["actual_lead_time_days"] - df_master["estimated_lead_time_days"]
    )
    df_master["freight_ratio"] = df_master["freight_value"] / df_master["price"].clip(lower=0.01)

    df_items = df_master.drop_duplicates(subset=["order_id", "order_item_id"])
    df_orders = df_master.drop_duplicates(subset=["order_id"])

    customer_freight = (
        df_items.groupby("customer_unique_id")
        .agg(avg_freight_ratio=("freight_ratio", "mean"))
        .reset_index()
    )
    customer_logistics = (
        df_orders.groupby("customer_unique_id")
        .agg(avg_delivery_delay=("delivery_delay_days", "mean"))
        .reset_index()
        .merge(customer_freight, on="customer_unique_id", how="left")
    )

    # ── Payments ──────────────────────────────────────────────────────────────
    orders_map = df_master[["order_id", "customer_unique_id"]].drop_duplicates("order_id")
    pay_enriched = pay_raw.merge(orders_map, on="order_id", how="inner")

    dominant_pay = (
        pay_enriched.groupby(["customer_unique_id", "payment_type"])["payment_value"]
        .sum()
        .reset_index()
        .sort_values("payment_value", ascending=False)
        .drop_duplicates("customer_unique_id")[["customer_unique_id", "payment_type"]]
        .rename(columns={"payment_type": "dominant_payment_type"})
    )
    avg_install = (
        pay_enriched.groupby("customer_unique_id")["payment_installments"]
        .mean()
        .reset_index()
        .rename(columns={"payment_installments": "avg_installments"})
    )
    customer_payments = dominant_pay.merge(avg_install, on="customer_unique_id", how="left")
    customer_payments["payment_type_cc_flag"] = (
        customer_payments["dominant_payment_type"] == "credit_card"
    ).astype(int)

    # ── Geography ─────────────────────────────────────────────────────────────
    customer_geo = (
        df_orders.groupby("customer_unique_id")["customer_state"]
        .agg(lambda x: x.mode().iloc[0])
        .reset_index()
    )
    customer_geo["customer_region"] = customer_geo["customer_state"].map(STATE_REGION)
    customer_geo["region_freight_score"] = customer_geo["customer_region"].map(
        REGION_FREIGHT_ORDER
    )

    # ── Assemble ──────────────────────────────────────────────────────────────
    df = df_agg.copy()
    for extra in [
        customer_logistics[["customer_unique_id", "avg_freight_ratio", "avg_delivery_delay"]],
        customer_payments[["customer_unique_id", "avg_installments", "payment_type_cc_flag"]],
        customer_geo[["customer_unique_id", "customer_state", "customer_region", "region_freight_score"]],
    ]:
        df = df.merge(extra, on="customer_unique_id", how="left")

    # ── RFM columns ───────────────────────────────────────────────────────────
    max_date = pd.to_datetime(df["last_purchase_date"]).max()
    df["Recency"] = (max_date - pd.to_datetime(df["last_purchase_date"])).dt.days
    df["Frequency"] = df["total_orders"]
    df["Monetary"] = df["total_spent"]
    df["Frequency_flag"] = (df["Frequency"] >= 2).astype(int)

    # ── Clip + impute ─────────────────────────────────────────────────────────
    df["Monetary"] = df["Monetary"].clip(upper=df["Monetary"].quantile(0.99))
    for col, (lo, hi) in OUTLIER_BOUNDS.items():
        if col in df.columns:
            df[col] = df[col].clip(lower=lo, upper=hi)

    df.fillna(
        {
            "avg_freight_ratio": df["avg_freight_ratio"].median(),
            "avg_delivery_delay": 0.0,
            "avg_review_score": df["avg_review_score"].median(),
            "payment_type_cc_flag": 0,
            "avg_installments": 1.0,
            "region_freight_score": 3,
        },
        inplace=True,
    )

    logger.info("Feature store built: %d customers", len(df))
    return df


# ── Training pipeline ─────────────────────────────────────────────────────────


def _iqr_filter(df: pd.DataFrame, col: str) -> pd.DataFrame:
    lo, hi = df[col].quantile(0.05), df[col].quantile(0.95)
    return df[(df[col] >= lo) & (df[col] <= hi)]


def _run_pipeline(df_raw: pd.DataFrame) -> dict:
    rfm = df_raw.set_index("customer_unique_id")[_RFM_FEATURES].copy()

    logger.info("IQR filtering…")
    rfm = _iqr_filter(rfm, "Recency")
    rfm = _iqr_filter(rfm, "Monetary")
    logger.info("  %d customers after filtering", len(rfm))

    rfm_log = rfm.copy()
    for col in ["Frequency", "Monetary"]:
        rfm_log[col] = np.log10(rfm_log[col].clip(lower=0.01))

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(rfm_log[_RFM_FEATURES]).astype(np.float32)

    if _UMAP_AVAILABLE:
        logger.info("UMAP reduction…")
        reducer = umap_module.UMAP(
            n_components=2, n_neighbors=750, min_dist=0.0, random_state=42, n_jobs=1
        )
        X = reducer.fit_transform(X_scaled).astype(np.float32)
        pipeline_name = "UMAP+KMeans"
    else:
        X = X_scaled
        pipeline_name = "KMeans (pure RFM)"

    logger.info("KMeans k-search (k=3..8) on %s…", pipeline_name)
    results: dict = {}
    for k in range(3, 9):
        km = KMeans(n_clusters=k, init="k-means++", n_init=20, random_state=42, max_iter=500)
        labels = km.fit_predict(X)
        sil = silhouette_score(X, labels, sample_size=20_000, random_state=42)
        db = davies_bouldin_score(X, labels)
        ch = calinski_harabasz_score(X, labels)
        results[k] = {
            "model": km, "labels": labels, "index": rfm.index,
            "silhouette": sil, "davies_bouldin": db,
            "calinski_harabasz": ch, "wcss": float(km.inertia_),
        }
        logger.info("  k=%d  sil=%.4f  db=%.4f", k, sil, db)
        del km
        gc.collect()

    best_k = max(results, key=lambda k: results[k]["silhouette"])
    logger.info("Best k=%d  silhouette=%.4f", best_k, results[best_k]["silhouette"])
    return {"results": results, "best_k": best_k, "pipeline_name": pipeline_name,
            "df_raw": df_raw, "rfm_index": rfm.index, "scaler": scaler}


def _save_artifacts(run_data: dict) -> None:
    best_k = run_data["best_k"]
    best = run_data["results"][best_k]
    results = run_data["results"]
    df_raw = run_data["df_raw"]
    pipeline_name = run_data["pipeline_name"]
    scaler = run_data["scaler"]

    # Remove stale model files from previous best k
    for old in _MODELS_DIR.glob("best_clustering_kmeans_k*.pkl"):
        old.unlink()
    for old in _MODELS_DIR.glob("best_clustering_kmeans_k*.json"):
        old.unlink()

    # model_comparison.csv
    def _minmax(s: pd.Series) -> pd.Series:
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else s * 0 + 0.5

    rows = [
        {
            "algorithm": f"KMeans_k{k}",
            "silhouette": round(r["silhouette"], 4),
            "davies_bouldin": round(r["davies_bouldin"], 4),
            "calinski_harabasz": round(r["calinski_harabasz"], 1),
            "wcss": round(r["wcss"], 1),
            "n_clusters": k,
        }
        for k, r in results.items()
    ]
    comp_df = pd.DataFrame(rows)
    comp_df["composite_score"] = (
        (_minmax(comp_df["silhouette"])
         - _minmax(comp_df["davies_bouldin"])
         + _minmax(comp_df["calinski_harabasz"])) / 3
    ).round(4)
    comp_df.to_csv(_PROCESSED / "model_comparison.csv", index=False)

    # Labeled dataset + cluster profile
    label_series = pd.Series(best["labels"], index=best["index"], name="cluster")
    df_labeled = df_raw.set_index("customer_unique_id").copy()
    df_labeled["cluster"] = label_series
    df_labeled = df_labeled.dropna(subset=["cluster"])
    df_labeled["cluster"] = df_labeled["cluster"].astype(int)

    profile_cols_present = [c for c in _PROFILE_COLS if c in df_labeled.columns]
    profile_rows = []
    for cid in sorted(df_labeled["cluster"].unique()):
        mask = df_labeled["cluster"] == cid
        group = df_labeled[mask]
        row = {"cluster": int(cid), "n_customers": int(mask.sum()),
               "pct_customers": round(mask.sum() / len(df_labeled) * 100, 2)}
        for col in profile_cols_present:
            row[col] = round(float(group[col].median()), 4)
        if "Monetary" in row and "Frequency" in row:
            row["CLV_proxy"] = round(row["Monetary"] * max(row["Frequency"], 1), 2)
        profile_rows.append(row)
    profile_df = pd.DataFrame(profile_rows)

    model_path = _MODELS_DIR / f"best_clustering_kmeans_k{best_k}.pkl"
    joblib.dump(best["model"], model_path)
    joblib.dump(scaler, _MODELS_DIR / "standard_scaler.pkl")

    meta = {
        "algorithm": pipeline_name,
        "k": int(best_k),
        "features": _RFM_FEATURES,
        "umap_n_neighbors": 750 if _UMAP_AVAILABLE else None,
        "silhouette": round(float(best["silhouette"]), 4),
        "davies_bouldin": round(float(best["davies_bouldin"]), 4),
        "calinski_harabasz": round(float(best["calinski_harabasz"]), 1),
        "composite_score": round(float(
            comp_df.loc[comp_df["algorithm"] == f"KMeans_k{best_k}", "composite_score"].iloc[0]
        ), 4),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_customers": len(df_labeled),
    }
    model_path.with_suffix(".json").write_text(json.dumps(meta, indent=2))

    df_labeled.reset_index().to_parquet(_PROCESSED / "customer_features_labeled.parquet", index=False)
    profile_df.to_parquet(_PROCESSED / "cluster_profile.parquet", index=False)

    logger.info("Artifacts saved locally")


def _update_retrain_log(new_sil: float, prev_sil: float | None, updated: bool) -> None:
    log_path = _PROCESSED / "retrain_log.json"
    history: list = []
    if log_path.exists():
        try:
            history = json.loads(log_path.read_text())
        except json.JSONDecodeError:
            history = []
    history.append({
        "date": datetime.now(timezone.utc).isoformat(),
        "new_silhouette": round(new_sil, 4),
        "previous_silhouette": round(prev_sil, 4) if prev_sil is not None else None,
        "artifacts_updated": updated,
    })
    log_path.write_text(json.dumps(history, indent=2))


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Retrain the Olist segmentation model.")
    parser.add_argument("--force", action="store_true",
                        help="Upload artifacts even if silhouette does not improve")
    args = parser.parse_args()

    # Current production silhouette (from GCS metadata)
    current_meta = get_gcs_metadata()
    current_sil: float | None = float(current_meta["silhouette"]) if current_meta else None
    if current_sil is not None:
        logger.info("Current production silhouette: %.4f", current_sil)
    else:
        logger.info("No model found in GCS — first run")

    mlflow_run = None
    if _MLFLOW_AVAILABLE:
        mlflow.set_experiment("olist_retrain")
        mlflow_run = mlflow.start_run(
            run_name=f"retrain_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
        )

    try:
        df_raw = _build_features_from_db()
        run_data = _run_pipeline(df_raw)
        new_sil = float(run_data["results"][run_data["best_k"]]["silhouette"])

        if _MLFLOW_AVAILABLE:
            mlflow.log_params({
                "best_k": run_data["best_k"],
                "pipeline": run_data["pipeline_name"],
                "n_customers": len(df_raw),
            })
            mlflow.log_metrics({
                "silhouette": new_sil,
                "davies_bouldin": run_data["results"][run_data["best_k"]]["davies_bouldin"],
            })
            if current_sil is not None:
                mlflow.log_metric("silhouette_delta", new_sil - current_sil)

        should_update = args.force or (
            current_sil is None or new_sil >= current_sil - _SILHOUETTE_TOLERANCE
        )

        if should_update:
            reason = "--force" if args.force else (
                "first run" if current_sil is None
                else f"silhouette {new_sil:.4f} ≥ {current_sil:.4f} - {_SILHOUETTE_TOLERANCE}"
            )
            logger.info("Saving and uploading artifacts (%s)", reason)
            _save_artifacts(run_data)
            _update_retrain_log(new_sil, current_sil, updated=True)
            upload_artifacts(run_data["best_k"])
            if _MLFLOW_AVAILABLE:
                mlflow.set_tag("artifacts_updated", "true")
            logger.info("✅ Retrain complete — new silhouette %.4f", new_sil)
            return 0
        else:
            logger.info(
                "No update — new silhouette %.4f does not improve current %.4f",
                new_sil, current_sil,
            )
            _update_retrain_log(new_sil, current_sil, updated=False)
            if _MLFLOW_AVAILABLE:
                mlflow.set_tag("artifacts_updated", "false")
            return 1

    except Exception:
        logger.exception("Retrain failed")
        return 2
    finally:
        if mlflow_run and _MLFLOW_AVAILABLE:
            mlflow.end_run()


if __name__ == "__main__":
    sys.exit(main())
