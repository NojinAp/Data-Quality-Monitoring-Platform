"""
Generates synthetic customers.csv, products.csv, orders.csv, and inventory.csv with
INTENTIONAL data quality problems baked in. 
Flaw categories injected, and which check they're meant to exercise:
  - Nulls / missing values        -> null_check.py
  - Duplicate rows                -> duplicate_check.py
  - Invalid business values       -> business_rules.py
  - Schema drift (new column      -> schema_check.py
    appearing partway through)
"""

import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)


# Config
NUM_CUSTOMERS = 2_000
NUM_PRODUCTS = 300
NUM_ORDERS = 20_000
OUTPUT_DIR = "."

CATEGORIES = ["Jackets", "Vests", "Accessories", "Footwear", "Knitwear"]
SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
SUPPLIERS = ["Supplier A", "Supplier B", "Supplier C", "Supplier D"]
WAREHOUSES = ["Toronto-DC", "Vancouver-DC", "Montreal-DC", "Calgary-DC"]
COUNTRIES = ["Canada", "United States", "United Kingdom", "Germany", "Japan", "Australia"]


def generate_customers(n: int) -> pd.DataFrame:
    """
    Flaws injected:
      - ~3% missing emails (null_check target)
      - ~1% duplicate customer_id (duplicate_check target - simulates a
        pipeline re-run that accidentally re-inserted a batch)
    """
    rows = []
    for i in range(1, n + 1):
        customer_id = i
        row = {
            "customer_id": customer_id,
            "name": fake.name(),
            "country": random.choice(COUNTRIES),
            "email": fake.email(),
            "created_date": fake.date_between(start_date="-3y", end_date="today"),
        }
        rows.append(row)

    df = pd.DataFrame(rows)

    # Inject missing emails
    null_email_idx = df.sample(frac=0.03, random_state=1).index
    df.loc[null_email_idx, "email"] = None

    # Inject duplicate customer_id rows (append copies of random existing rows)
    dup_rows = df.sample(frac=0.01, random_state=2)
    df = pd.concat([df, dup_rows], ignore_index=True)

    return df


def generate_products(n: int) -> pd.DataFrame:
    """
    Flaws injected:
      - ~2% negative or zero prices (business_rules target: price >= 0)
      - ~2% missing supplier (null_check target)
    """
    rows = []
    for i in range(1, n + 1):
        price = round(random.uniform(40, 900), 2)
        rows.append(
            {
                "product_id": i,
                "category": random.choice(CATEGORIES),
                "size": random.choice(SIZES),
                "price": price,
                "supplier": random.choice(SUPPLIERS),
            }
        )

    df = pd.DataFrame(rows)

    # Inject invalid prices (negative or zero)
    bad_price_idx = df.sample(frac=0.02, random_state=3).index
    df.loc[bad_price_idx, "price"] = df.loc[bad_price_idx, "price"].apply(
        lambda p: round(-abs(p) * random.uniform(0.1, 0.5), 2)
    )

    # Inject missing supplier
    null_supplier_idx = df.sample(frac=0.02, random_state=4).index
    df.loc[null_supplier_idx, "supplier"] = None

    return df


def generate_orders(customers: pd.DataFrame, products: pd.DataFrame, n: int) -> pd.DataFrame:
    """
    Flaws injected:
      - ~1% duplicate order_id (duplicate_check target)
      - ~2% missing customer_id (null_check target)
      - ~1.5% negative or zero quantity (business_rules: quantity > 0)
      - ~1% future order_date (business_rules: order_date <= today)
      - Schema drift: after row ~70% of the file, a "discount" column
        appears that didn't exist before (schema_check target)
    """
    customer_ids = customers["customer_id"].unique().tolist()
    product_ids = products["product_id"].unique().tolist()

    rows = []
    schema_change_point = int(n * 0.7)

    for i in range(1, n + 1):
        product_id = random.choice(product_ids)
        product_price = float(products.loc[products["product_id"] == product_id, "price"].iloc[0])
        quantity = random.randint(1, 5)
        order_date = fake.date_between(start_date="-1y", end_date="today")

        row = {
            "order_id": i,
            "customer_id": random.choice(customer_ids),
            "product_id": product_id,
            "quantity": quantity,
            "amount": round(product_price * quantity, 2),
            "order_date": order_date,
        }

        # Schema drift: discount column only exists in the back 30% of the file
        if i > schema_change_point:
            row["discount"] = round(random.uniform(0, 0.2), 2)

        rows.append(row)

    df = pd.DataFrame(rows)

    # Inject duplicate order_id
    dup_rows = df.sample(frac=0.01, random_state=5)
    df = pd.concat([df, dup_rows], ignore_index=True)

    # Inject missing customer_id
    null_cust_idx = df.sample(frac=0.02, random_state=6).index
    df.loc[null_cust_idx, "customer_id"] = None

    # Inject invalid quantity (negative or zero)
    bad_qty_idx = df.sample(frac=0.015, random_state=7).index
    df.loc[bad_qty_idx, "quantity"] = df.loc[bad_qty_idx, "quantity"].apply(
        lambda q: -abs(q) if random.random() < 0.7 else 0
    )

    # Inject future order_date
    future_idx = df.sample(frac=0.01, random_state=8).index
    df.loc[future_idx, "order_date"] = df.loc[future_idx, "order_date"].apply(
        lambda d: datetime.now().date() + timedelta(days=random.randint(1, 90))
    )

    return df


def generate_inventory(products: pd.DataFrame) -> pd.DataFrame:
    """
    Flaws injected:
      - ~2% negative stock_quantity (business_rules target: stock >= 0)
      - ~1% missing warehouse (null_check target)
    """
    rows = []
    for product_id in products["product_id"].unique():
        for warehouse in WAREHOUSES:
            rows.append(
                {
                    "product_id": product_id,
                    "warehouse": warehouse,
                    "stock_quantity": random.randint(0, 500),
                }
            )

    df = pd.DataFrame(rows)

    # Inject negative stock
    bad_stock_idx = df.sample(frac=0.02, random_state=9).index
    df.loc[bad_stock_idx, "stock_quantity"] = df.loc[bad_stock_idx, "stock_quantity"].apply(
        lambda s: -random.randint(1, 50)
    )

    # Inject missing warehouse
    null_wh_idx = df.sample(frac=0.01, random_state=10).index
    df.loc[null_wh_idx, "warehouse"] = None

    return df


def main():
    print(f"Generating {NUM_CUSTOMERS:,} customers, {NUM_PRODUCTS:,} products, "
          f"{NUM_ORDERS:,} orders...\n")

    customers = generate_customers(NUM_CUSTOMERS)
    products = generate_products(NUM_PRODUCTS)
    orders = generate_orders(customers, products, NUM_ORDERS)
    inventory = generate_inventory(products)

    customers.to_csv(f"{OUTPUT_DIR}/customers.csv", index=False)
    products.to_csv(f"{OUTPUT_DIR}/products.csv", index=False)
    orders.to_csv(f"{OUTPUT_DIR}/orders.csv", index=False)
    inventory.to_csv(f"{OUTPUT_DIR}/inventory.csv", index=False)

    # Summary
    print("Done. Files written:")
    print(f"  customers.csv  -> {len(customers):,} rows "
          f"({customers['email'].isna().sum()} missing emails, "
          f"{customers.duplicated(subset='customer_id').sum()} duplicate customer_ids)")
    print(f"  products.csv   -> {len(products):,} rows "
          f"({(products['price'] <= 0).sum()} invalid prices, "
          f"{products['supplier'].isna().sum()} missing suppliers)")
    print(f"  orders.csv     -> {len(orders):,} rows "
          f"({orders.duplicated(subset='order_id').sum()} duplicate order_ids, "
          f"{orders['customer_id'].isna().sum()} missing customer_ids, "
          f"{(orders['quantity'] <= 0).sum()} invalid quantities, "
          f"{(pd.to_datetime(orders['order_date']) > pd.Timestamp.now()).sum()} future dates, "
          f"discount column present in last {(orders['discount'].notna()).sum() if 'discount' in orders else 0} rows)")
    print(f"  inventory.csv  -> {len(inventory):,} rows "
          f"({(inventory['stock_quantity'] < 0).sum()} negative stock, "
          f"{inventory['warehouse'].isna().sum()} missing warehouses)")


if __name__ == "__main__":
    main()