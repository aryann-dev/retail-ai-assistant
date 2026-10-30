"""Database access for Retail AI Assistant (PostgreSQL / Neon)."""
import os
from datetime import date
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

CATEGORY_FILES = {
    "ACCESSORIES.csv": "accessories",
    "BAGS_BACKPACKS.csv": "bags",
    "BEAUTY.csv": "beauty",
    "BLAZERS.csv": "blazers",
    "HOODIES_SWEATSHIRTS.csv": "hoodies",
    "JACKETS.csv": "jackets",
    "JEANS.csv": "jeans",
    "LINEN.csv": "linen",
    "OVERSHIRTS.csv": "overshirts",
    "PERFUMES.csv": "perfumes",
    "POLO SHIRTS.csv": "polo shirts",
    "SHIRTS.csv": "shirts",
    "SHOES.csv": "shoes",
    "SHORTS.csv": "shorts",
    "SUITS.csv": "suits",
    "SWEATERS_CARDIGANS.csv": "sweaters",
    "TROUSERS.csv": "trousers",
}


def connect():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set. Add it to the .env file.")
    return psycopg.connect(DATABASE_URL, connect_timeout=30)


def create_schema():
    sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with connect() as conn:
        conn.execute(sql)


def query_df(sql, params=None):
    """Run a SELECT and return the rows as a pandas DataFrame."""
    with connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        columns = [d.name for d in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=columns)


def parse_price(price_str):
    """Turn a catalog price such as "₹ 4,990.00" into a number."""
    digits = "".join(c for c in str(price_str) if c.isdigit() or c == ".")
    try:
        return float(digits) if digits else 0.0
    except ValueError:
        return 0.0


def read_catalog_csvs():
    """Read the Kaggle category CSVs into one list of unique products.
    A product is identified by its Zara link: different products can share a name and price,
    and the same product can appear in two category files (the first category is kept)."""
    products = []
    seen = set()
    for filename, category in CATEGORY_FILES.items():
        try:
            df = pd.read_csv(filename)
        except FileNotFoundError:
            print(f"Skipped {filename} (not found)")
            continue
        for _, row in df.iterrows():
            link = str(row.get("link", "")).strip()
            if link in seen:
                continue
            seen.add(link)
            details = str(row.get("details", ""))
            products.append({
                "name": str(row.get("product_name", "N/A")).strip().upper(),
                "category": category,
                "price": parse_price(row.get("price", "0")),
                "details": None if details == "nan" else details,
                "link": link,
            })
        print(f"Loaded {filename}")
    return products


# ---------- Queries used by the app ----------

def get_products():
    """All products with their stock, ordered by id."""
    return query_df("""
        SELECT p.id, p.name, p.category, p.price::float AS price, p.details,
               COALESCE(i.current_stock, 0) AS current_stock,
               COALESCE(i.reorder_level, 10) AS reorder_level
        FROM products p
        LEFT JOIN inventory i ON i.product_id = p.id
        ORDER BY p.id
    """)


def get_stock(product_id):
    """Return (current_stock, reorder_level) for one product, or None."""
    with connect() as conn:
        return conn.execute(
            "SELECT current_stock, reorder_level FROM inventory WHERE product_id = %s",
            (product_id,),
        ).fetchone()


def get_sales():
    """All sales with product name and category."""
    return query_df("""
        SELECT to_char(s.sale_date, 'YYYY-MM-DD') AS date, s.product_id,
               p.name AS product_name, p.category, s.qty_sold,
               s.price::float AS price, s.revenue::float AS revenue
        FROM sales s
        JOIN products p ON p.id = s.product_id
    """)


def record_sale(product_id, qty):
    """Reduce stock and insert a sale in one transaction.
    Returns (ok, current_stock_before, price, revenue)."""
    with connect() as conn:
        with conn.transaction():
            row = conn.execute("""
                SELECT i.current_stock, p.price::float
                FROM inventory i JOIN products p ON p.id = i.product_id
                WHERE i.product_id = %s
                FOR UPDATE OF i
            """, (product_id,)).fetchone()
            if row is None:
                return False, 0, 0.0, 0.0
            current_stock, price = row
            if qty > current_stock:
                return False, current_stock, price, 0.0
            revenue = round(qty * price, 2)
            conn.execute(
                "UPDATE inventory SET current_stock = current_stock - %s, updated_at = now() WHERE product_id = %s",
                (qty, product_id),
            )
            conn.execute(
                "INSERT INTO sales (sale_date, product_id, qty_sold, price, revenue) VALUES (%s, %s, %s, %s, %s)",
                (date.today(), product_id, qty, price, revenue),
            )
            return True, current_stock, price, revenue


if __name__ == "__main__":
    create_schema()
    print("Schema is ready.")
