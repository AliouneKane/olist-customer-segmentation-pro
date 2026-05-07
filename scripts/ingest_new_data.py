"""Ingest new orders from data/incoming/*.csv into Neon PostgreSQL.

Reads all CSV files in data/incoming/, inserts new rows into the relevant
Neon tables (olist_orders, olist_customers, olist_order_items,
olist_order_payments, olist_order_reviews) with deduplication on order_id.

Expected CSV columns:
    order_id, customer_id, customer_unique_id, customer_state,
    order_purchase_date, order_delivered_date, order_estimated_delivery_date,
    price, freight_value, payment_type, payment_installments, payment_value,
    review_score

Usage:
    python scripts/ingest_new_data.py [--incoming-dir PATH]
"""

from __future__ import annotations

import argparse
import logging
import sys
import uuid
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import text

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")
sys.path.insert(0, str(_PROJECT_ROOT))

from src.data_loader import get_db_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_INCOMING_DIR = _PROJECT_ROOT / "data" / "incoming"


def _load_incoming_csvs(incoming_dir: Path) -> pd.DataFrame:
    """Load and concatenate all CSVs from incoming_dir (skip template)."""
    files = [
        f for f in incoming_dir.glob("*.csv")
        if "template" not in f.name
    ]
    if not files:
        logger.info("No new CSV files found in %s", incoming_dir)
        return pd.DataFrame()

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df["_source_file"] = f.name
        dfs.append(df)
        logger.info("  Loaded %s (%d rows)", f.name, len(df))

    return pd.concat(dfs, ignore_index=True)


def _get_existing_order_ids(engine) -> set[str]:
    """Fetch order_ids already in Neon to avoid duplicates."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT order_id FROM olist_orders"))
        return {row[0] for row in result}


def _split_into_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split flat incoming CSV into the 5 Neon table DataFrames."""

    # ── olist_orders ─────────────────────────────────────────────────────────
    orders = pd.DataFrame({
        "order_id": df["order_id"],
        "customer_id": df["customer_id"],
        "order_status": "delivered",
        "order_purchase_timestamp": pd.to_datetime(df["order_purchase_date"]),
        "order_approved_at": pd.to_datetime(df["order_purchase_date"]),
        "order_delivered_carrier_date": pd.to_datetime(df["order_delivered_date"]),
        "order_delivered_customer_date": pd.to_datetime(df["order_delivered_date"]),
        "order_estimated_delivery_date": pd.to_datetime(df["order_estimated_delivery_date"]),
    })

    # ── olist_customers ───────────────────────────────────────────────────────
    customers = pd.DataFrame({
        "customer_id": df["customer_id"],
        "customer_unique_id": df["customer_unique_id"],
        "customer_zip_code_prefix": "00000",
        "customer_city": "unknown",
        "customer_state": df["customer_state"],
    }).drop_duplicates("customer_id")

    # ── olist_order_items ─────────────────────────────────────────────────────
    items = pd.DataFrame({
        "order_id": df["order_id"],
        "order_item_id": 1,
        "product_id": df["order_id"].apply(lambda x: str(uuid.uuid5(uuid.NAMESPACE_DNS, x))),
        "seller_id": "unknown-seller",
        "shipping_limit_date": pd.to_datetime(df["order_estimated_delivery_date"]),
        "price": df["price"],
        "freight_value": df["freight_value"],
    })

    # ── olist_order_payments ──────────────────────────────────────────────────
    payments = pd.DataFrame({
        "order_id": df["order_id"],
        "payment_sequential": 1,
        "payment_type": df["payment_type"],
        "payment_installments": df["payment_installments"],
        "payment_value": df["payment_value"],
    })

    # ── olist_order_reviews ───────────────────────────────────────────────────
    reviews = pd.DataFrame({
        "review_id": df["order_id"].apply(lambda x: str(uuid.uuid5(uuid.NAMESPACE_DNS, x + "-review"))),
        "order_id": df["order_id"],
        "review_score": df["review_score"],
        "review_comment_title": "",
        "review_comment_message": "",
        "review_creation_date": pd.to_datetime(df["order_delivered_date"]),
        "review_answer_timestamp": pd.to_datetime(df["order_delivered_date"]),
    })

    return {
        "olist_orders": orders,
        "olist_customers": customers,
        "olist_order_items": items,
        "olist_order_payments": payments,
        "olist_order_reviews": reviews,
    }


def ingest(incoming_dir: Path) -> int:
    """Run the full ingestion pipeline. Returns number of new orders inserted."""
    df_raw = _load_incoming_csvs(incoming_dir)
    if df_raw.empty:
        return 0

    engine = get_db_engine()

    # Deduplicate against existing orders in Neon
    existing_ids = _get_existing_order_ids(engine)
    df_new = df_raw[~df_raw["order_id"].isin(existing_ids)].copy()

    if df_new.empty:
        logger.info("All %d orders already exist in Neon — nothing to insert", len(df_raw))
        return 0

    logger.info(
        "%d new orders to insert (%d already existed)",
        len(df_new), len(df_raw) - len(df_new),
    )

    tables = _split_into_tables(df_new)
    for table_name, df_table in tables.items():
        df_table.to_sql(table_name, engine, if_exists="append", index=False)
        logger.info("  Inserted %d rows into %s", len(df_table), table_name)

    logger.info("✅ Ingestion complete — %d new orders added to Neon", len(df_new))
    return len(df_new)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--incoming-dir",
        type=Path,
        default=_INCOMING_DIR,
        help="Directory containing incoming CSV files",
    )
    args = parser.parse_args()

    n = ingest(args.incoming_dir)
    if n == 0:
        logger.info("No new data — skipping retrain trigger")
        sys.exit(1)  # exit 1 = no new data, retrain.yml skips retrain step
    sys.exit(0)  # exit 0 = new data ingested, retrain should run


if __name__ == "__main__":
    main()
