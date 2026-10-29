import pandas as pd
import random
from datetime import datetime, timedelta

inventory_df = pd.read_csv("INVENTORY.csv")
catalog_price = {}

# Read prices from all category CSVs and map them by product_name
CATEGORY_FILES = [
    "ACCESSORIES.csv", "BAGS_BACKPACKS.csv", "BEAUTY.csv", "BLAZERS.csv",
    "HOODIES_SWEATSHIRTS.csv", "JACKETS.csv", "JEANS.csv", "LINEN.csv",
    "OVERSHIRTS.csv", "PERFUMES.csv", "POLO SHIRTS.csv", "SHIRTS.csv",
    "SHOES.csv", "SHORTS.csv", "SUITS.csv", "SWEATERS_CARDIGANS.csv", "TROUSERS.csv"
]

for filename in CATEGORY_FILES:
    try:
        df = pd.read_csv(filename)
        for _, row in df.iterrows():
            name = str(row.get("product_name", "")).strip().upper()
            price_str = str(row.get("price", "0"))
            price_num = "".join(c for c in price_str if c.isdigit() or c == ".")
            try:
                catalog_price[name] = float(price_num) if price_num else 0.0
            except ValueError:
                catalog_price[name] = 0.0
    except FileNotFoundError:
        pass

DAYS = 90
today = datetime.today()

# Some products sell fast and some are slow or dead, so the test data looks realistic
rows = []

for _, product in inventory_df.iterrows():
    product_name = product["product_name"]
    category = product["category"]

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
            price = catalog_price.get(product_name, 0.0)
            rows.append({
                "date": date.strftime("%Y-%m-%d"),
                "product_name": product_name,
                "category": category,
                "qty_sold": qty_sold,
                "price": price,
                "revenue": round(qty_sold * price, 2)
            })

sales_df = pd.DataFrame(rows)
sales_df.to_csv("SALES.csv", index=False)

print(f"Total sales records generated: {len(sales_df)}")
print("SALES.csv created successfully.")
