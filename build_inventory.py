import random

import db

REORDER_LEVEL = 10   # a "reorder" alert is raised when stock falls to this level or below
STOCK_MIN = 0
STOCK_MAX = 100

products = db.get_products()
if products.empty:
    print("No products in the database. Run migrate_csv_to_db.py first.")
    raise SystemExit(1)

rows = [(int(pid), random.randint(STOCK_MIN, STOCK_MAX), REORDER_LEVEL) for pid in products["id"]]

with db.connect() as conn:
    with conn.transaction():
        conn.execute("DELETE FROM inventory")
        with conn.cursor().copy("COPY inventory (product_id, current_stock, reorder_level) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)

print(f"\nTotal products in inventory: {len(rows)}")
print("Inventory table created successfully.")
