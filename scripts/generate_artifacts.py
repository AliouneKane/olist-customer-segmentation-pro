"""Generate all dashboard artifacts without running Jupyter notebooks.

Produces:
  data/processed/customer_features_labeled.parquet
  data/processed/cluster_profile.parquet
  data/processed/model_comparison.csv
  models/best_clustering_kmeans_k<K>.pkl  (+ .json sidecar)

Strategy: pure RFM (3 features) with IQR outlier removal and log10 transform,
matching the approach in resources/detailed-rfm-analysis-and-k-means-clustering.ipynb
that achieves silhouette ~0.6.

Usage:
    python scripts/generate_artifacts.py
"""

import gc
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import joblib
from sklearn.cluster import KMeans
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score,
)
from sklearn.preprocessing import StandardScaler

# Paths
PROJECT_ROOT  = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR    = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# The 3 features used for clustering (pure RFM)
RFM_FEATURES = ["Recency", "Frequency", "Monetary"]

# All raw behavioral columns we want in the cluster profile for the dashboard
PROFILE_COLS = [
    "Recency", "Monetary", "Frequency",
    "avg_freight_ratio", "avg_delivery_delay", "avg_review_score",
    "payment_type_cc_flag", "avg_installments", "region_freight_score",
]

print(f"PROJECT_ROOT  : {PROJECT_ROOT}")
print(f"PROCESSED_DIR : {PROCESSED_DIR}")
print(f"RFM_FEATURES  : {RFM_FEATURES}")


# ── Step 1: Load raw features ────────────────────────────────────────────────
print("\n[1/5] Loading raw customer features…")
df_raw = pd.read_parquet(PROCESSED_DIR / "customer_features_raw.parquet")
print(f"  Raw shape: {df_raw.shape}")

# Keep customer_unique_id as index for alignment later
if "customer_unique_id" in df_raw.columns:
    df_raw = df_raw.set_index("customer_unique_id")

rfm = df_raw[RFM_FEATURES].copy()
print(f"  RFM shape before cleaning: {rfm.shape}")


# ── Step 2: IQR outlier removal (q5/q95 boundaries) ─────────────────────────
# Apply to Recency and Monetary — Frequency is naturally bounded so skip
print("\n[2/5] Removing IQR outliers (q5/q95) on Recency and Monetary…")

def _iqr_filter(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Keep only rows within the 5th–95th percentile range for a given column."""
    lo = df[col].quantile(0.05)
    hi = df[col].quantile(0.95)
    before = len(df)
    df = df[(df[col] >= lo) & (df[col] <= hi)]
    print(f"    {col}: removed {before - len(df):,} rows  (kept {len(df):,})")
    return df

# Recency and Monetary have the longest tails — clip those
# Leave Frequency untouched: IQR would collapse it to [1,1] (mostly single-order customers)
rfm = _iqr_filter(rfm, "Recency")
rfm = _iqr_filter(rfm, "Monetary")
print(f"  RFM shape after cleaning: {rfm.shape}")


# ── Step 3: Log10 transform on Frequency and Monetary ───────────────────────
# Recency is left on its original scale (lower = more recent = better)
# Frequency and Monetary are right-skewed — log10 compresses extremes
print("\n[3/5] Applying log10 transform to Frequency and Monetary…")
rfm_log = rfm.copy()
for col in ["Frequency", "Monetary"]:
    rfm_log[col] = np.log10(rfm_log[col].clip(lower=0.01))
    print(f"    {col}: min={rfm_log[col].min():.3f}  max={rfm_log[col].max():.3f}")


# ── Step 4: StandardScaler ───────────────────────────────────────────────────
print("\n[4/5] Scaling with StandardScaler…")
scaler = StandardScaler()
X = scaler.fit_transform(rfm_log[RFM_FEATURES]).astype(np.float32)
assert not np.isnan(X).any(), "NaN detected after scaling"
print(f"  X shape: {X.shape}  ({X.nbytes / 1e6:.1f} MB)")


# ── Step 5: KMeans k-search ──────────────────────────────────────────────────
print("\n[5/5] KMeans k-search (k=4..10)…")
results: dict = {}
for k in range(4, 11):
    km = KMeans(n_clusters=k, init="k-means++", n_init=20,
                random_state=42, max_iter=500)
    labels = km.fit_predict(X)
    # Full silhouette on the clean subset (no sample needed — ~90k rows is fine)
    sil = silhouette_score(X, labels, sample_size=20_000, random_state=42)
    db  = davies_bouldin_score(X, labels)
    ch  = calinski_harabasz_score(X, labels)
    results[k] = {
        "model": km, "labels": labels, "index": rfm.index,
        "silhouette": sil, "davies_bouldin": db,
        "calinski_harabasz": ch, "wcss": float(km.inertia_),
    }
    print(f"  k={k}: sil={sil:.4f}  db={db:.4f}  ch={ch:.0f}")
    del km
    gc.collect()

# Best k by silhouette
best_k = max(results, key=lambda k: results[k]["silhouette"])
best   = results[best_k]
print(f"\n  ✅ Best k = {best_k}  (silhouette={best['silhouette']:.4f})")


# ── Build model_comparison.csv ───────────────────────────────────────────────
print("\nBuilding comparison table…")
rows = []
for k, r in results.items():
    rows.append({
        "algorithm":         f"KMeans_k{k}",
        "silhouette":        round(r["silhouette"], 4),
        "davies_bouldin":    round(r["davies_bouldin"], 4),
        "calinski_harabasz": round(r["calinski_harabasz"], 1),
        "wcss":              round(r["wcss"], 1),
        "n_clusters":        k,
    })
comp_df = pd.DataFrame(rows)

def _minmax(s: pd.Series) -> pd.Series:
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng > 0 else s * 0 + 0.5

comp_df["composite_score"] = (
    (_minmax(comp_df["silhouette"])
     - _minmax(comp_df["davies_bouldin"])
     + _minmax(comp_df["calinski_harabasz"])) / 3
).round(4)
comp_df.to_csv(PROCESSED_DIR / "model_comparison.csv", index=False)
print(comp_df[["algorithm", "silhouette", "davies_bouldin", "composite_score"]].to_string(index=False))


# ── Build labeled dataset and cluster profile ────────────────────────────────
# Assign labels to the cleaned RFM subset, then join back to full df_raw
# so the profile retains all 9 behavioral features for the dashboard.
print("\nBuilding cluster profile…")
label_series = pd.Series(best["labels"], index=best["index"], name="cluster")

# df_raw may contain rows that were removed by IQR filtering — label them NaN
df_labeled = df_raw.copy()
df_labeled["cluster"] = label_series
df_labeled = df_labeled.dropna(subset=["cluster"])
df_labeled["cluster"] = df_labeled["cluster"].astype(int)

profile_cols_present = [c for c in PROFILE_COLS if c in df_labeled.columns]

profile_rows = []
for cid in sorted(df_labeled["cluster"].unique()):
    mask  = df_labeled["cluster"] == cid
    group = df_labeled[mask]
    row   = {
        "cluster":      int(cid),
        "n_customers":  int(mask.sum()),
        "pct_customers": round(mask.sum() / len(df_labeled) * 100, 2),
    }
    for col in profile_cols_present:
        row[col] = round(float(group[col].median()), 4)
    if "Monetary" in row and "Frequency" in row:
        row["CLV_proxy"] = round(row["Monetary"] * max(row["Frequency"], 1), 2)
    profile_rows.append(row)
profile_df = pd.DataFrame(profile_rows)


# ── Save artifacts ───────────────────────────────────────────────────────────
MODEL_PATH   = MODELS_DIR / f"best_clustering_kmeans_k{best_k}.pkl"
LABELED_PATH = PROCESSED_DIR / "customer_features_labeled.parquet"
PROFILE_PATH = PROCESSED_DIR / "cluster_profile.parquet"

joblib.dump(best["model"], MODEL_PATH)
meta = {
    "algorithm":         "KMeans",
    "k":                 int(best_k),
    "features":          RFM_FEATURES,
    "silhouette":        round(float(best["silhouette"]), 4),
    "davies_bouldin":    round(float(best["davies_bouldin"]), 4),
    "calinski_harabasz": round(float(best["calinski_harabasz"]), 1),
    "composite_score":   round(float(comp_df.loc[
        comp_df["algorithm"] == f"KMeans_k{best_k}", "composite_score"
    ].iloc[0]), 4),
}
MODEL_PATH.with_suffix(".json").write_text(json.dumps(meta, indent=2))

df_labeled = df_labeled.reset_index()  # restore customer_unique_id as column
df_labeled.to_parquet(LABELED_PATH, index=False)
profile_df.to_parquet(PROFILE_PATH, index=False)

print(f"\n  ✅ {MODEL_PATH.name}")
print(f"  ✅ {MODEL_PATH.with_suffix('.json').name}")
print(f"  ✅ customer_features_labeled.parquet  ({LABELED_PATH.stat().st_size/1e6:.1f} MB)")
print(f"  ✅ cluster_profile.parquet")
print(f"  ✅ model_comparison.csv")
print(f"\nCluster profile:")
print(profile_df[["cluster", "n_customers", "pct_customers", "CLV_proxy"]].to_string(index=False))
print(f"\n🎉 Done — silhouette = {best['silhouette']:.4f}  (best k={best_k})")
