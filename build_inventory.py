import pandas as pd
import random

# Same category files as in business.py
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

REORDER_LEVEL = 10   # a "reorder" alert is raised when stock falls to this level or below
STOCK_MIN = 0
STOCK_MAX = 100

rows = []
seen_names = set()

for filename, category in CATEGORY_FILES.items():
    try:
        df = pd.read_csv(filename)
        for _, row in df.iterrows():
            name = str(row.get("product_name", "N/A")).strip().upper()
            price = str(row.get("price", "N/A"))

            key = f"{name}-{price}"
            if key in seen_names:
                continue
            seen_names.add(key)

            rows.append({
                "product_name": name,
                "category": category,
                "current_stock": random.randint(STOCK_MIN, STOCK_MAX),
                "reorder_level": REORDER_LEVEL,
            })
        print(f"Processed {filename} ({len(df)} products)")
    except FileNotFoundError:
        print(f"Skipped {filename} (not found)")

inventory_df = pd.DataFrame(rows)
inventory_df.to_csv("INVENTORY.csv", index=False)

print(f"\nTotal products in inventory: {len(inventory_df)}")
print("INVENTORY.csv created successfully.")
