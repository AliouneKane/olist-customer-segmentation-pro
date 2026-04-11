"""Unit tests for src/features.py.

Tests cover the standalone transformation functions (apply_log_transforms,
scale_features) and the module-level constants (FINAL_FEATURES, STATE_REGION,
REGION_FREIGHT_ORDER, OUTLIER_BOUNDS).

build_customer_features() is not tested here because it requires a live
PostgreSQL connection — that is covered by integration tests.
"""

import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler

from features import (
    FINAL_FEATURES,
    OUTLIER_BOUNDS,
    REGION_FREIGHT_ORDER,
    STATE_REGION,
    apply_log_transforms,
    scale_features,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Minimal synthetic customer DataFrame with all FINAL_FEATURES present."""
    rng = np.random.default_rng(42)
    n = 50
    data = {
        "customer_unique_id": [f"cust_{i}" for i in range(n)],
        "Recency": rng.integers(1, 500, size=n).astype(float),
        "Monetary": rng.uniform(10, 1000, size=n),
        "Frequency": rng.integers(1, 10, size=n).astype(float),
        "Frequency_flag": rng.integers(0, 2, size=n).astype(int),
        "avg_freight_ratio": rng.uniform(0.05, 1.5, size=n),
        "avg_delivery_delay": rng.uniform(-5, 30, size=n),
        "avg_review_score": rng.uniform(1, 5, size=n),
        "payment_type_cc_flag": rng.integers(0, 2, size=n).astype(int),
        "avg_installments": rng.uniform(1, 10, size=n),
        "region_freight_score": rng.integers(1, 6, size=n).astype(float),
    }
    df = pd.DataFrame(data)
    # Add log-transformed columns (as produced by apply_log_transforms)
    df["Log_Recency"] = np.log1p(df["Recency"])
    df["Log_Monetary"] = np.log1p(df["Monetary"])
    return df


# ── FINAL_FEATURES ────────────────────────────────────────────────────────────


def test_final_features_count() -> None:
    """FINAL_FEATURES must contain exactly 9 feature names."""
    assert len(FINAL_FEATURES) == 9


def test_final_features_names() -> None:
    """Each expected feature name must be present in FINAL_FEATURES."""
    expected = {
        "Log_Recency",
        "Log_Monetary",
        "Frequency_flag",
        "avg_freight_ratio",
        "avg_delivery_delay",
        "avg_review_score",
        "payment_type_cc_flag",
        "avg_installments",
        "region_freight_score",
    }
    assert expected == set(FINAL_FEATURES)


# ── STATE_REGION / REGION_FREIGHT_ORDER ───────────────────────────────────────


def test_all_27_states_mapped() -> None:
    """All 27 Brazilian state codes must be present in STATE_REGION."""
    brazil_states = {
        "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
        "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
        "RO", "RR", "RS", "SC", "SE", "SP", "TO",
    }
    assert brazil_states == set(STATE_REGION.keys())


def test_region_values_valid() -> None:
    """Every state must map to a known region name."""
    valid_regions = set(REGION_FREIGHT_ORDER.keys())
    for state, region in STATE_REGION.items():
        assert region in valid_regions, (
            f"State {state!r} maps to unknown region {region!r}"
        )


def test_region_freight_order_range() -> None:
    """REGION_FREIGHT_ORDER values must be integers in [1, 5]."""
    for region, score in REGION_FREIGHT_ORDER.items():
        assert 1 <= score <= 5, f"{region!r} has score {score} outside [1, 5]"


def test_region_freight_order_unique() -> None:
    """Each region must have a unique ordinal score."""
    scores = list(REGION_FREIGHT_ORDER.values())
    assert len(scores) == len(set(scores)), (
        "Duplicate ordinal scores in REGION_FREIGHT_ORDER"
    )


# ── apply_log_transforms ──────────────────────────────────────────────────────


def test_log_transform_creates_columns() -> None:
    """apply_log_transforms must add Log_Recency and Log_Monetary columns."""
    df = pd.DataFrame({"Recency": [10.0, 100.0], "Monetary": [50.0, 500.0]})
    out = apply_log_transforms(df)
    assert "Log_Recency" in out.columns
    assert "Log_Monetary" in out.columns


def test_log_transform_values_correct() -> None:
    """Log_Recency = log1p(Recency), all values must be >= 0."""
    df = pd.DataFrame(
        {"Recency": [0.0, 10.0, 365.0], "Monetary": [1.0, 100.0, 1000.0]}
    )
    out = apply_log_transforms(df)
    np.testing.assert_allclose(out["Log_Recency"].values, np.log1p(df["Recency"].values))
    np.testing.assert_allclose(
        out["Log_Monetary"].values, np.log1p(df["Monetary"].values)
    )
    assert (out["Log_Recency"] >= 0).all()
    assert (out["Log_Monetary"] >= 0).all()


def test_log_transform_original_preserved() -> None:
    """Original columns must remain unchanged after the transformation."""
    df = pd.DataFrame({"Recency": [42.0], "Monetary": [99.0]})
    out = apply_log_transforms(df)
    assert out["Recency"].iloc[0] == 42.0
    assert out["Monetary"].iloc[0] == 99.0


def test_log_transform_custom_cols() -> None:
    """apply_log_transforms must respect a custom cols argument."""
    df = pd.DataFrame({"Recency": [10.0], "Monetary": [50.0], "Extra": [7.0]})
    out = apply_log_transforms(df, cols=["Extra"])
    assert "Log_Extra" in out.columns
    assert "Log_Recency" not in out.columns


def test_log_transform_missing_column_raises() -> None:
    """apply_log_transforms must raise KeyError for absent columns."""
    df = pd.DataFrame({"Recency": [10.0]})
    with pytest.raises(KeyError):
        apply_log_transforms(df, cols=["NonExistent"])


# ── scale_features ────────────────────────────────────────────────────────────


def test_scale_features_fit(sample_df: pd.DataFrame) -> None:
    """scale_features must return a DataFrame with approx. mean=0 and std=1."""
    scaled_df, scaler = scale_features(sample_df, feature_cols=FINAL_FEATURES)
    means = scaled_df.mean()
    stds = scaled_df.std()
    assert means.abs().max() < 0.1, "Scaled means are not close to 0"
    assert (stds - 1.0).abs().max() < 0.2, "Scaled stds are not close to 1"
    assert isinstance(scaler, StandardScaler)


def test_scale_features_index(sample_df: pd.DataFrame) -> None:
    """scale_features must index the output DataFrame by customer_unique_id."""
    scaled_df, _ = scale_features(sample_df, feature_cols=FINAL_FEATURES)
    assert scaled_df.index.name == "customer_unique_id"
    assert list(scaled_df.index) == list(sample_df["customer_unique_id"])


def test_scale_features_columns(sample_df: pd.DataFrame) -> None:
    """Output columns must exactly match the requested feature_cols."""
    scaled_df, _ = scale_features(sample_df, feature_cols=FINAL_FEATURES)
    assert list(scaled_df.columns) == FINAL_FEATURES


def test_scale_features_load(sample_df: pd.DataFrame) -> None:
    """scale_features must load and reuse an existing scaler without re-fitting."""
    with tempfile.TemporaryDirectory() as tmp:
        scaler_path = Path(tmp) / "scaler.pkl"
        # First call: fit and save
        scale_features(sample_df, feature_cols=FINAL_FEATURES, scaler_path=scaler_path)
        assert scaler_path.exists(), "Scaler file was not saved"

        # Second call: load — result must be identical to first call
        scaled_loaded, _ = scale_features(
            sample_df, feature_cols=FINAL_FEATURES, scaler_path=scaler_path
        )
        scaled_first, _ = scale_features(
            sample_df, feature_cols=FINAL_FEATURES, scaler_path=None
        )
        np.testing.assert_allclose(
            scaled_loaded.values,
            scaled_first.values,
            rtol=1e-5,
            err_msg="Loaded scaler produces different results than fitted scaler",
        )


def test_scale_features_saves_file(sample_df: pd.DataFrame) -> None:
    """scale_features must persist the scaler to disk when scaler_path is provided."""
    with tempfile.TemporaryDirectory() as tmp:
        scaler_path = Path(tmp) / "sub" / "scaler.pkl"
        scale_features(sample_df, feature_cols=FINAL_FEATURES, scaler_path=scaler_path)
        assert scaler_path.exists()
        scaler = joblib.load(scaler_path)
        assert isinstance(scaler, StandardScaler)


def test_scale_features_missing_column_raises(sample_df: pd.DataFrame) -> None:
    """scale_features must raise KeyError when feature_cols has an absent column."""
    with pytest.raises(KeyError):
        scale_features(sample_df, feature_cols=["NonExistentFeature"])


def test_scale_features_null_raises(sample_df: pd.DataFrame) -> None:
    """scale_features must raise ValueError when feature_cols contains nulls."""
    df_with_null = sample_df.copy()
    df_with_null.loc[0, "Log_Recency"] = np.nan
    with pytest.raises(ValueError):
        scale_features(df_with_null, feature_cols=FINAL_FEATURES)


# ── OUTLIER_BOUNDS ────────────────────────────────────────────────────────────


def test_outlier_bounds_clipping() -> None:
    """Values outside OUTLIER_BOUNDS must be clipped to the defined limits."""
    df = pd.DataFrame(
        {
            "avg_freight_ratio": [0.0, 1.0, 5.0],    # 5.0 > upper 2.0
            "avg_delivery_delay": [-100.0, 0.0, 200.0],  # -100 < -30, 200 > 60
            "avg_installments": [0.5, 6.0, 20.0],     # 0.5 < 1, 20 > 12
        }
    )
    for col, (lo, hi) in OUTLIER_BOUNDS.items():
        df[col] = df[col].clip(lower=lo, upper=hi)

    assert df["avg_freight_ratio"].max() <= 2.0
    assert df["avg_freight_ratio"].min() >= 0.0
    assert df["avg_delivery_delay"].max() <= 60.0
    assert df["avg_delivery_delay"].min() >= -30.0
    assert df["avg_installments"].max() <= 12.0
    assert df["avg_installments"].min() >= 1.0
