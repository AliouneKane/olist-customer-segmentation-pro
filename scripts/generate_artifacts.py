"""Minimal artifact generation — no MLFlow, no seaborn, lean imports.

Generates the 4 files needed by the dashboard:
  data/processed/customer_features_labeled.parquet
  data/processed/cluster_profile.parquet
  data/processed/model_comparison.csv
  models/best_clustering_kmeans_k<K>.pkl  (+.json sidecar)

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

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT  = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR    = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from features import FINAL_FEATURES  # noqa: E402

print(f"PROJECT_ROOT  : {PROJECT_ROOT}")
print(f"PROCESSED_DIR : {PROCESSED_DIR}")
print(f"FINAL_FEATURES: {FINAL_FEATURES}")

# ── Load ──────────────────────────────────────────────────────────────────────
print("\n[1/4] Loading parquets…")
X_scaled_df = pd.read_parquet(PROCESSED_DIR / "customer_features_scaled.parquet")
if "customer_unique_id" in X_scaled_df.columns:
    X_scaled_df = X_scaled_df.set_index("customer_unique_id")

df_raw = pd.read_parquet(PROCESSED_DIR / "customer_features_raw.parquet")

X = X_scaled_df[FINAL_FEATURES].values.astype(np.float32)  # float32 halves RAM
assert not np.isnan(X).any(), "NaN in X"
print(f"  X shape : {X.shape}  ({X.nbytes / 1e6:.1f} MB)")

# ── KMeans k-search ───────────────────────────────────────────────────────────
print("\n[2/4] KMeans k-search (k=4,5,6)…")
results = {}
for k in [4, 5, 6]:
    km = KMeans(n_clusters=k, init="k-means++", n_init=10,
                random_state=42, max_iter=300)
    labels = km.fit_predict(X)
    sil = silhouette_score(X, labels, sample_size=20_000, random_state=42)
    db  = davies_bouldin_score(X, labels)
    ch  = calinski_harabasz_score(X, labels)
    results[k] = {"model": km, "labels": labels,
                  "silhouette": sil, "davies_bouldin": db,
                  "calinski_harabasz": ch, "wcss": float(km.inertia_)}
    print(f"  k={k}: sil={sil:.4f}  db={db:.4f}  ch={ch:.0f}")
    del km
    gc.collect()

# ── Select best k ─────────────────────────────────────────────────────────────
best_k = max(results, key=lambda k: results[k]["silhouette"])
best   = results[best_k]
print(f"\n  Best k = {best_k}  (silhouette={best['silhouette']:.4f})")

# ── Model comparison CSV ──────────────────────────────────────────────────────
print("\n[3/4] Building comparison table…")
rows = []
for k, r in results.items():
    rows.append({
        "algorithm": f"KMeans_k{k}",
        "silhouette": round(r["silhouette"], 4),
        "davies_bouldin": round(r["davies_bouldin"], 4),
        "calinski_harabasz": round(r["calinski_harabasz"], 1),
        "wcss": round(r["wcss"], 1),
        "n_clusters": k,
    })
comp_df = pd.DataFrame(rows)
# Composite score
def _minmax(s):
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng > 0 else s * 0 + 0.5

comp_df["composite_score"] = (
    (_minmax(comp_df["silhouette"])
     - _minmax(comp_df["davies_bouldin"])
     + _minmax(comp_df["calinski_harabasz"])) / 3
).round(4)
comp_df.to_csv(PROCESSED_DIR / "model_comparison.csv", index=False)
print(comp_df[["algorithm", "silhouette", "davies_bouldin", "composite_score"]].to_string(index=False))

# ── Label dataset + cluster profile ──────────────────────────────────────────
print("\n[4/4] Saving artifacts…")
df_labeled = df_raw.copy()
df_labeled["cluster"] = pd.Series(
    best["labels"], index=X_scaled_df.index
).values

RAW_PROFILE_COLS = [c for c in [
    "Recency", "Monetary", "Frequency",
    "avg_freight_ratio", "avg_delivery_delay", "avg_review_score",
    "payment_type_cc_flag", "avg_installments", "region_freight_score",
] if c in df_labeled.columns]

profile_rows = []
for cid in sorted(df_labeled["cluster"].unique()):
    mask = df_labeled["cluster"] == cid
    group = df_labeled[mask]
    row = {"cluster": int(cid), "n_customers": int(mask.sum()),
           "pct_customers": round(mask.sum() / len(df_labeled) * 100, 2)}
    for col in RAW_PROFILE_COLS:
        row[col] = round(float(group[col].median()), 4)
    if "Monetary" in row and "Frequency" in row:
        row["CLV_proxy"] = round(row["Monetary"] * max(row["Frequency"], 1), 2)
    profile_rows.append(row)
profile_df = pd.DataFrame(profile_rows)

MODEL_PATH   = MODELS_DIR / f"best_clustering_kmeans_k{best_k}.pkl"
LABELED_PATH = PROCESSED_DIR / "customer_features_labeled.parquet"
PROFILE_PATH = PROCESSED_DIR / "cluster_profile.parquet"

joblib.dump(best["model"], MODEL_PATH)
meta = {
    "algorithm": "KMeans", "k": int(best_k),
    "features": FINAL_FEATURES,
    "silhouette":        round(float(best["silhouette"]), 4),
    "davies_bouldin":    round(float(best["davies_bouldin"]), 4),
    "calinski_harabasz": round(float(best["calinski_harabasz"]), 1),
    "composite_score":   round(float(comp_df.loc[
        comp_df["algorithm"] == f"KMeans_k{best_k}", "composite_score"
    ].iloc[0]), 4),
}
MODEL_PATH.with_suffix(".json").write_text(json.dumps(meta, indent=2))

df_labeled.to_parquet(LABELED_PATH, index=False)
profile_df.to_parquet(PROFILE_PATH, index=False)

print(f"  ✅ {MODEL_PATH.name}")
print(f"  ✅ {MODEL_PATH.with_suffix('.json').name}")
print(f"  ✅ customer_features_labeled.parquet  ({LABELED_PATH.stat().st_size/1e6:.1f} MB)")
print(f"  ✅ cluster_profile.parquet")
print(f"  ✅ model_comparison.csv")
print(f"\nCluster profile:")
print(profile_df[["cluster","n_customers","pct_customers","CLV_proxy"]].to_string(index=False))
print("\n🎉 Done — all dashboard artifacts ready.")
