import random
from datetime import datetime, timedelta

import db

products = db.get_products()
if products.empty:
    print("No products in the database. Run migrate_csv_to_db.py first.")
    raise SystemExit(1)

DAYS = 90
today = datetime.today()

# Some products sell fast and some are slow or dead, so the test data looks realistic
rows = []

for _, product in products.iterrows():
    product_id = int(product["id"])
    price = float(product["price"])

    # Give each product a random "selling speed"
    speed_type = random.choices(
        ["dead", "slow", "normal", "fast"],
        weights=[15, 25, 40, 20]  # share (%) of products of each type
    )[0]

    for day_offset in range(DAYS):
        date = today - timedelta(days=day_offset)

        if speed_type == "dead":
            qty_sold = 0  # no sales at all
        elif speed_type == "slow":
            qty_sold = random.choices([0, 1], weights=[85, 15])[0]
        elif speed_type == "normal":
            qty_sold = random.choices([0, 1, 2], weights=[60, 30, 10])[0]
        else:  # fast
            qty_sold = random.choices([0, 1, 2, 3, 4], weights=[30, 30, 20, 15, 5])[0]

        if qty_sold > 0:
            rows.append((date.date(), product_id, qty_sold, price, round(qty_sold * price, 2)))

with db.connect() as conn:
    with conn.transaction():
        conn.execute("DELETE FROM sales")
        with conn.cursor().copy("COPY sales (sale_date, product_id, qty_sold, price, revenue) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)

print(f"Total sales records generated: {len(rows)}")
print("Sales table created successfully.")
