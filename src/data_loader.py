import pandas as pd
from sqlalchemy import create_engine, Engine
from pathlib import Path
from dotenv import load_dotenv
import os
import logging
from typing import List

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables — explicit path so it works from any CWD (notebooks, scripts, etc.)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def get_db_engine() -> Engine:
    """Creates a SQLAlchemy engine for PostgreSQL.

    Prefers DATABASE_URL if set (Neon.tech / Cloud SQL), otherwise falls back
    to individual POSTGRES_* env vars (local docker-compose).

    Returns:
        Engine: SQLAlchemy engine object.

    Raises:
        EnvironmentError: If no usable connection info is found.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Strip unsupported psycopg2 params (e.g. channel_binding)
        if "channel_binding" in database_url:
            from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
            parsed = urlparse(database_url)
            params = parse_qs(parsed.query)
            params.pop("channel_binding", None)
            clean_query = urlencode({k: v[0] for k, v in params.items()})
            database_url = urlunparse(parsed._replace(query=clean_query))
        logger.info("Using DATABASE_URL (Neon / Cloud SQL)")
        return create_engine(database_url, connect_args={"sslmode": "require"})

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    db = os.getenv("POSTGRES_DB")

    missing = [
        k
        for k, v in {
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": password,
            "POSTGRES_HOST": host,
            "POSTGRES_PORT": port,
            "POSTGRES_DB": db,
        }.items()
        if v is None
    ]
    if missing:
        raise EnvironmentError(
            f"Variables manquantes dans .env : {', '.join(missing)}. "
            "Définissez DATABASE_URL ou les variables POSTGRES_* dans .env."
        )

    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    logger.info("Using local PostgreSQL (%s:%s/%s)", host, port, db)
    return create_engine(connection_string)


def ingest_csv_to_postgres(data_dir: Path, engine: Engine) -> None:
    """Reads all CSV files from the data directory and uploads them to PostgreSQL.

    Args:
        data_dir (Path): Path to the directory containing CSV files.
        engine (Engine): SQLAlchemy engine object.
    """
    csv_files: List[Path] = list(data_dir.glob("*.csv"))

    if not csv_files:
        logger.warning(f"No CSV files found in {data_dir}")
        return

    for file_path in csv_files:
        table_name = file_path.stem.replace("_dataset", "")
        logger.info(f"Ingesting {file_path.name} into table '{table_name}'...")

        try:
            # Load CSV into DataFrame
            df = pd.read_csv(file_path)

            # Upload to PostgreSQL
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            logger.info(f"Successfully ingested {len(df)} rows into {table_name}.")
        except Exception as e:
            logger.error(f"Failed to ingest {file_path.name}: {e}")


def get_merged_dataframe(engine: Engine) -> pd.DataFrame:
    """Fetches a merged dataframe of delivered orders from PostgreSQL.

    Args:
        engine (Engine): SQLAlchemy engine object.

    Returns:
        pd.DataFrame: Merged dataframe.
    """
    query = """
    SELECT 
        o.order_id, o.customer_id, o.order_status, o.order_purchase_timestamp, 
        o.order_approved_at, o.order_delivered_carrier_date, o.order_delivered_customer_date, o.order_estimated_delivery_date,
        c.customer_unique_id, c.customer_zip_code_prefix, c.customer_city, c.customer_state,
        oi.order_item_id, oi.product_id, oi.seller_id, oi.shipping_limit_date, oi.price, oi.freight_value,
        p.product_category_name, p.product_weight_g, p.product_length_cm, p.product_height_cm, p.product_width_cm,
        t.product_category_name_english,
        s.seller_zip_code_prefix, s.seller_city, s.seller_state,
        op.payment_sequential, op.payment_type, op.payment_installments, op.payment_value,
        r.review_id, r.review_score, r.review_creation_date, r.review_answer_timestamp
    FROM 
        olist_orders o
    JOIN 
        olist_customers c ON o.customer_id = c.customer_id
    LEFT JOIN 
        olist_order_items oi ON o.order_id = oi.order_id
    LEFT JOIN 
        olist_products p ON oi.product_id = p.product_id
    LEFT JOIN 
        product_category_name_translation t ON p.product_category_name = t.product_category_name
    LEFT JOIN 
        olist_sellers s ON oi.seller_id = s.seller_id
    LEFT JOIN 
        olist_order_payments op ON o.order_id = op.order_id
    LEFT JOIN 
        olist_order_reviews r ON o.order_id = r.order_id
    WHERE 
        o.order_status = 'delivered'
    """
    logger.info("Fetching and merging data from PostgreSQL...")
    df = pd.read_sql(query, engine)
    logger.info(f"Successfully fetched {len(df)} rows.")
    return df


def get_customer_aggregation(engine: Engine) -> pd.DataFrame:
    """Fetches customer-level aggregated data from PostgreSQL.

    Args:
        engine (Engine): SQLAlchemy engine object.

    Returns:
        pd.DataFrame: Aggregated dataframe at the customer_unique_id level.
    """
    query = """
    SELECT 
        c.customer_unique_id,
        MIN(o.order_purchase_timestamp) as first_purchase_date,
        MAX(o.order_purchase_timestamp) as last_purchase_date,
        COUNT(DISTINCT o.order_id) as total_orders,
        SUM(op.payment_value) as total_spent,
        AVG(r.review_score) as avg_review_score
    FROM 
        olist_customers c
    JOIN 
        olist_orders o ON c.customer_id = o.customer_id
    LEFT JOIN
        olist_order_payments op ON o.order_id = op.order_id
    LEFT JOIN
        olist_order_reviews r ON o.order_id = r.order_id
    WHERE 
        o.order_status = 'delivered'
    GROUP BY 
        c.customer_unique_id
    """
    logger.info("Fetching customer-level aggregated data from PostgreSQL...")
    df = pd.read_sql(query, engine)
    logger.info(f"Successfully fetched {len(df)} customer records.")
    return df


KAGGLE_DATASET = "olistbr/brazilian-ecommerce"


def download_kaggle_dataset(tmp_dir: Path) -> None:
    """Downloads and unzips the Olist dataset from Kaggle into tmp_dir.

    Args:
        tmp_dir: Directory where CSV files will be extracted.

    Raises:
        ImportError: If the kaggle package is not installed.
        OSError: If Kaggle credentials (~/.kaggle/kaggle.json) are missing.
    """
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    logger.info("Downloading Kaggle dataset '%s'...", KAGGLE_DATASET)
    api.dataset_download_files(KAGGLE_DATASET, path=tmp_dir, unzip=True)
    logger.info("Download complete.")


def refresh_data_from_kaggle() -> None:
    """Downloads the Olist dataset from Kaggle and ingests it into PostgreSQL.

    Orchestrates download_kaggle_dataset() + ingest_csv_to_postgres() in a
    temporary directory that is automatically cleaned up after ingestion.
    """
    import tempfile

    engine = get_db_engine()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        download_kaggle_dataset(tmp_dir)
        ingest_csv_to_postgres(tmp_dir, engine)
    logger.info("Kaggle data successfully loaded into PostgreSQL.")


if __name__ == "__main__":
    refresh_data_from_kaggle()
