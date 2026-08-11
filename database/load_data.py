"""
Loads customers.csv, products.csv, orders.csv, inventory.csv into their
matching raw_* tables in Azure SQL.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from connection import engine

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

FILES_TO_TABLES = {
    DATA_DIR / "customers.csv": "raw_customers",
    DATA_DIR / "products.csv": "raw_products",
    DATA_DIR / "orders.csv": "raw_orders",
    DATA_DIR / "inventory.csv": "raw_inventory",
}


def load_file(csv_path: str, table_name: str):
    print(f"Loading {csv_path} -> {table_name} ...")

    df = pd.read_csv(csv_path)

    # Stamp every row with when it was loaded
    df["loaded_at"] = datetime.now(timezone.utc)

    df.to_sql(
        table_name,
        engine,
        if_exists="append",   
        index=False,          
        chunksize=1000,       
        method="multi",       
    )

    print(f"  -> {len(df):,} rows loaded")


def main():
    for csv_file, table_name in FILES_TO_TABLES.items():
        load_file(csv_file, table_name)

    print("\nDone. Row counts now in the database:")
    with engine.connect() as conn:
        from sqlalchemy import text
        for table_name in FILES_TO_TABLES.values():
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
            print(f"  {table_name}: {count:,} rows")


if __name__ == "__main__":
    main()