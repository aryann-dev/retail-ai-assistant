"""
One-time setup: create the tables and load data into PostgreSQL.

- products  <- the Kaggle category CSVs (required)
- inventory <- INVENTORY.csv, if present (otherwise run build_inventory.py)
- sales     <- SALES.csv, if present (otherwise run build_sales.py)

Run:  python migrate_csv_to_db.py           (refuses if products already exist)
      python migrate_csv_to_db.py --reset   (deletes all existing data first)
"""
import os
import random
import sys
from collections import defaultdict

import pandas as pd

import db

db.create_schema()

with db.connect() as conn:
    existing = conn.execute("SELECT count(*) FROM products").fetchone()[0]
    if existing and "--reset" not in sys.argv:
        print(f"The database already has {existing} products. Use --reset to replace all data.")
        sys.exit(1)

products = db.read_catalog_csvs()
if not products:
    print("No catalog CSVs found. Copy the Kaggle CSV files into this folder first.")
    sys.exit(1)

with db.connect() as conn:
    with conn.transaction():
        conn.execute("TRUNCATE sales, inventory, products RESTART IDENTITY CASCADE")

        # --- Products ---
        with conn.cursor().copy("COPY products (name, category, price, details, link) FROM STDIN") as copy:
            for p in products:
                copy.write_row((p["name"], p["category"], p["price"], p["details"], p["link"]))
        rows = conn.execute("SELECT id, name, price::float FROM products ORDER BY id").fetchall()
        # The old CSV files identify products by name (and price), so map each name to its
        # distinct (price, first product id) pairs in catalog order
        ids_by_name = defaultdict(list)
        for pid, name, price in rows:
            if all(abs(price - p) >= 0.005 for p, _ in ids_by_name[name]):
                ids_by_name[name].append((price, pid))
        print(f"Products: {len(rows)}")

        # --- Inventory ---
        if os.path.exists("INVENTORY.csv"):
            inv = pd.read_csv("INVENTORY.csv")
            seen_count = defaultdict(int)
            stock = {}
            for _, r in inv.iterrows():
                name = str(r["product_name"]).strip().upper()
                k = seen_count[name]
                seen_count[name] += 1
                # The n-th INVENTORY row for a name belongs to the n-th distinct price of that name
                if k < len(ids_by_name[name]):
                    stock[ids_by_name[name][k][1]] = (int(r["current_stock"]), int(r["reorder_level"]))
            # Products the old CSV did not track get sample stock, as build_inventory.py would
            inv_rows = [(pid, *stock.get(pid, (random.randint(0, 100), 10))) for pid, _, _ in rows]
            with conn.cursor().copy("COPY inventory (product_id, current_stock, reorder_level) FROM STDIN") as copy:
                for row in inv_rows:
                    copy.write_row(row)
            print(f"Inventory: {len(stock)} rows from INVENTORY.csv, {len(inv_rows) - len(stock)} new rows with sample stock")
        else:
            print("Inventory: INVENTORY.csv not found, run build_inventory.py next.")

        # --- Sales ---
        if os.path.exists("SALES.csv"):
            sales = pd.read_csv("SALES.csv")
            sale_rows, skipped = [], 0
            for _, r in sales.iterrows():
                name = str(r["product_name"]).strip().upper()
                candidates = ids_by_name.get(name)
                if not candidates:
                    skipped += 1
                    continue
                # Pick the product with the same price; fall back to the first one with that name
                pid = next((c[1] for c in candidates if abs(c[0] - float(r["price"])) < 0.005), candidates[0][1])
                sale_rows.append((r["date"], pid, int(r["qty_sold"]), float(r["price"]), float(r["revenue"])))
            with conn.cursor().copy("COPY sales (sale_date, product_id, qty_sold, price, revenue) FROM STDIN") as copy:
                for row in sale_rows:
                    copy.write_row(row)
            print(f"Sales: {len(sale_rows)} rows" + (f" ({skipped} unmatched rows skipped)" if skipped else ""))
        else:
            print("Sales: SALES.csv not found, run build_sales.py next.")

print("Done! Now run: python index.py")
