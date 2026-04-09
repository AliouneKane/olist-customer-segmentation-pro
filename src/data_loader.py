import pandas as pd
from sqlalchemy import create_engine, Engine
from pathlib import Path
from dotenv import load_dotenv
import os
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_db_engine() -> Engine:
    """Creates a SQLAlchemy engine for PostgreSQL.

    Returns:
        Engine: SQLAlchemy engine object.
    """
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    db = os.getenv("POSTGRES_DB")
    
    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{db}"
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

if __name__ == "__main__":
    # Define paths
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    
    # Initialize DB connection
    try:
        db_engine = get_db_engine()
        # Test connection
        with db_engine.connect() as conn:
            logger.info("Database connection successful.")
        
        # Run ingestion
        ingest_csv_to_postgres(DATA_DIR, db_engine)
        logger.info("Data ingestion completed.")
    except Exception as ex:
        logger.error(f"Initialization error: {ex}")
