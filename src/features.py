"""Feature engineering module for Olist customer segmentation.

Provides functions to build the customer feature store from PostgreSQL,
apply log-transformations, and normalize features with StandardScaler.

All functions follow production conventions:
- Type hints on all parameters and return values
- Google-style docstrings
- No side effects — pure transformations returning new DataFrames
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sqlalchemy import Engine

logger = logging.getLogger(__name__)

# ── Geographic encoding constants ────────────────────────────────────────────

STATE_REGION: dict[str, str] = {
    "AC": "Norte",  "AM": "Norte",  "AP": "Norte",  "PA": "Norte",
    "RO": "Norte",  "RR": "Norte",  "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste",
    "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste",
    "MS": "Centro-Oeste", "MT": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

# Ordinal encoding: Sul (low freight) -> Norte (high freight)
REGION_FREIGHT_ORDER: dict[str, int] = {
    "Sul": 1, "Sudeste": 2, "Centro-Oeste": 3, "Nordeste": 4, "Norte": 5,
}

FINAL_FEATURES: list[str] = [
    "Log_Recency",
    "Log_Monetary",
    "Frequency_flag",
    "avg_freight_ratio",
    "avg_delivery_delay",
    "avg_review_score",
    "payment_type_cc_flag",
    "avg_installments",
    "region_freight_score",
]

OUTLIER_BOUNDS: dict[str, tuple[float | None, float | None]] = {
    "avg_freight_ratio":  (0.0, 2.0),
    "avg_delivery_delay": (-30.0, 60.0),
    "avg_installments":   (1.0, 12.0),
    # Monetary P99 is computed dynamically in build_customer_features
}


def build_customer_features(engine: Engine) -> pd.DataFrame:
    """Builds the customer-level feature store from PostgreSQL.

    Constructs 9 behavioral and RFM features per customer by:
    1. Fetching base RFM from get_customer_aggregation()
    2. Computing logistics features (freight ratio, delivery delay) from
       the merged order-item grain dataframe — with explicit deduplication
       at (order_id, order_item_id) for item-level metrics and at order_id
       for order-level metrics to avoid Cartesian-product inflation
    3. Computing payment features (installments, CC flag) from order_payments
    4. Encoding geographic features (region freight score)
    5. Applying outlier clipping and median imputation

    The output is raw (non-normalized). Pass it to scale_features() before
    clustering.

    Args:
        engine: SQLAlchemy engine connected to the PostgreSQL instance.

    Returns:
        DataFrame with one row per customer_unique_id and columns:
        customer_unique_id, Recency, Frequency, Monetary, Frequency_flag,
        avg_freight_ratio, avg_delivery_delay, avg_review_score,
        payment_type_cc_flag, avg_installments, region_freight_score,
        customer_state, customer_region.
    """
    from data_loader import get_customer_aggregation, get_merged_dataframe

    logger.info("Building customer feature store...")

    # ── Load sources ──────────────────────────────────────────────────────────
    df_agg    = get_customer_aggregation(engine)
    df_master = get_merged_dataframe(engine)
    pay_raw   = pd.read_sql_table("olist_order_payments", engine)

    # ── Temporal columns ──────────────────────────────────────────────────────
    _datetime_cols = [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in _datetime_cols:
        df_master[col] = pd.to_datetime(df_master[col], errors="coerce")

    df_master["actual_lead_time_days"] = (
        df_master["order_delivered_customer_date"]
        - df_master["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400

    df_master["estimated_lead_time_days"] = (
        df_master["order_estimated_delivery_date"]
        - df_master["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400

    df_master["delivery_delay_days"] = (
        df_master["actual_lead_time_days"] - df_master["estimated_lead_time_days"]
    )
    df_master["freight_ratio"] = df_master["freight_value"] / df_master["price"]
    df_master["is_late"]       = (df_master["delivery_delay_days"] > 0).astype(int)

    # ── Logistics features ────────────────────────────────────────────────────
    # Item-level dedup for freight ratio (avoid payment JOIN duplication)
    df_items  = df_master.drop_duplicates(subset=["order_id", "order_item_id"])
    df_orders = df_master.drop_duplicates(subset=["order_id"])

    customer_freight = df_items.groupby("customer_unique_id").agg(
        avg_freight_ratio=("freight_ratio", "mean"),
    ).reset_index()

    customer_logistics = df_orders.groupby("customer_unique_id").agg(
        avg_delivery_delay=("delivery_delay_days", "mean"),
    ).reset_index()
    customer_logistics = customer_logistics.merge(
        customer_freight, on="customer_unique_id", how="left"
    )

    # ── Payment features ──────────────────────────────────────────────────────
    orders_map   = df_master[["order_id", "customer_unique_id"]].drop_duplicates("order_id")
    pay_enriched = pay_raw.merge(orders_map, on="order_id", how="inner")

    dominant_pay = (
        pay_enriched
        .groupby(["customer_unique_id", "payment_type"])["payment_value"]
        .sum()
        .reset_index()
        .sort_values("payment_value", ascending=False)
        .drop_duplicates("customer_unique_id")[["customer_unique_id", "payment_type"]]
        .rename(columns={"payment_type": "dominant_payment_type"})
    )

    avg_install = (
        pay_enriched
        .groupby("customer_unique_id")["payment_installments"]
        .mean()
        .reset_index()
        .rename(columns={"payment_installments": "avg_installments"})
    )

    customer_payments = dominant_pay.merge(avg_install, on="customer_unique_id", how="left")
    customer_payments["payment_type_cc_flag"] = (
        customer_payments["dominant_payment_type"] == "credit_card"
    ).astype(int)

    # ── Geographic features ───────────────────────────────────────────────────
    customer_geo = (
        df_orders
        .groupby("customer_unique_id")["customer_state"]
        .agg(lambda x: x.mode().iloc[0])
        .reset_index()
    )
    customer_geo["customer_region"]      = customer_geo["customer_state"].map(STATE_REGION)
    customer_geo["region_freight_score"] = customer_geo["customer_region"].map(
        REGION_FREIGHT_ORDER
    )

    # ── Assembly ──────────────────────────────────────────────────────────────
    df_features = df_agg.copy()
    for df_extra in [
        customer_logistics[["customer_unique_id", "avg_freight_ratio", "avg_delivery_delay"]],
        customer_payments[["customer_unique_id", "avg_installments", "payment_type_cc_flag"]],
        customer_geo[["customer_unique_id", "customer_state", "customer_region",
                      "region_freight_score"]],
    ]:
        n_before = len(df_features)
        df_features = df_features.merge(df_extra, on="customer_unique_id", how="left")
        assert len(df_features) == n_before, "Merge created duplicate rows — check keys."

    # ── RFM base ──────────────────────────────────────────────────────────────
    max_date = pd.to_datetime(df_features["last_purchase_date"]).max()
    df_features["Recency"]        = (
        max_date - pd.to_datetime(df_features["last_purchase_date"])
    ).dt.days
    df_features["Frequency"]      = df_features["total_orders"]
    df_features["Monetary"]       = df_features["total_spent"]
    df_features["Frequency_flag"] = (df_features["Frequency"] >= 2).astype(int)

    # ── Outlier clipping ──────────────────────────────────────────────────────
    p99_monetary = df_features["Monetary"].quantile(0.99)
    df_features["Monetary"] = df_features["Monetary"].clip(upper=p99_monetary)
    for col, (lo, hi) in OUTLIER_BOUNDS.items():
        df_features[col] = df_features[col].clip(lower=lo, upper=hi)

    # ── Imputation ────────────────────────────────────────────────────────────
    imputation_map: dict[str, float] = {
        "avg_freight_ratio":    df_features["avg_freight_ratio"].median(),
        "avg_delivery_delay":   0.0,
        "avg_review_score":     df_features["avg_review_score"].median(),
        "payment_type_cc_flag": 0,
        "avg_installments":     1.0,
        "region_freight_score": 3,
    }
    df_features.fillna(imputation_map, inplace=True)

    imputed_cols = ["Recency", "Monetary"] + list(imputation_map.keys())
    n_null = df_features[imputed_cols].isnull().sum().sum()
    if n_null > 0:
        raise ValueError(
            f"build_customer_features: {n_null} nulls résiduels après imputation."
        )

    logger.info(
        "Feature store built: %d customers x %d columns.",
        len(df_features), df_features.shape[1],
    )
    return df_features


def apply_log_transforms(
    df: pd.DataFrame,
    cols: list[str] | None = None,
) -> pd.DataFrame:
    """Applies log1p transformation to specified columns.

    Creates new columns named ``Log_{col}`` for each column in ``cols``.
    The original columns are preserved unchanged.

    Args:
        df: Input DataFrame.
        cols: List of column names to transform. Defaults to
            ['Recency', 'Monetary'].

    Returns:
        DataFrame with additional ``Log_{col}`` columns appended.

    Raises:
        KeyError: If any column in ``cols`` is not present in ``df``.
    """
    if cols is None:
        cols = ["Recency", "Monetary"]

    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise KeyError(f"apply_log_transforms: colonnes introuvables : {missing}")

    out = df.copy()
    for col in cols:
        out[f"Log_{col}"] = np.log1p(out[col])
    return out


def scale_features(
    df: pd.DataFrame,
    feature_cols: list[str] | None = None,
    scaler_path: Path | None = None,
) -> tuple[pd.DataFrame, StandardScaler]:
    """Applies StandardScaler to selected feature columns.

    If ``scaler_path`` points to an existing file, that scaler is loaded
    and used for transform only (no re-fit). Otherwise a new scaler is
    fit on ``df`` and returned — and saved to ``scaler_path`` if provided.

    Args:
        df: Input DataFrame. Must contain all columns in ``feature_cols``
            and a ``customer_unique_id`` column used as the output index.
        feature_cols: Columns to scale. Defaults to FINAL_FEATURES.
        scaler_path: Optional path to a pre-fitted scaler (.pkl). If
            provided and the file exists, the scaler is loaded; otherwise
            a new scaler is fit and saved here.

    Returns:
        Tuple of:
        - DataFrame indexed by customer_unique_id with scaled features.
        - The fitted StandardScaler instance.

    Raises:
        KeyError: If ``feature_cols`` contains columns absent from ``df``.
        ValueError: If any null values remain in ``feature_cols``.
    """
    if feature_cols is None:
        feature_cols = FINAL_FEATURES

    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise KeyError(f"scale_features: colonnes introuvables : {missing}")

    n_null = df[feature_cols].isnull().sum().sum()
    if n_null > 0:
        raise ValueError(
            f"scale_features: {n_null} valeurs nulles dans feature_cols. "
            "Appliquer l'imputation avant le scaling."
        )

    X = df[feature_cols].values

    if scaler_path is not None and Path(scaler_path).exists():
        logger.info("Loading scaler from %s", scaler_path)
        scaler: StandardScaler = joblib.load(scaler_path)
        X_scaled = scaler.transform(X)
    else:
        logger.info("Fitting new StandardScaler on %d samples.", len(X))
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        if scaler_path is not None:
            Path(scaler_path).parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(scaler, scaler_path)
            logger.info("Scaler saved to %s", scaler_path)

    index = (
        df["customer_unique_id"].values
        if "customer_unique_id" in df.columns
        else df.index
    )
    X_scaled_df = pd.DataFrame(X_scaled, columns=feature_cols, index=index)
    X_scaled_df.index.name = "customer_unique_id"

    return X_scaled_df, scaler
