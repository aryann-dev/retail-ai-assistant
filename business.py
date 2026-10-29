from groq import Groq
from dotenv import load_dotenv
import os
import chromadb
import pandas as pd
from sentence_transformers import SentenceTransformer

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

embed_model = SentenceTransformer('BAAI/bge-m3')
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="retail_products")

# Load the inventory once and keep it in memory
inventory_df = pd.read_csv("INVENTORY.csv")
catalog_price_lookup = {}
_CATEGORY_FILES_FOR_PRICE = [
    "ACCESSORIES.csv", "BAGS_BACKPACKS.csv", "BEAUTY.csv", "BLAZERS.csv",
    "HOODIES_SWEATSHIRTS.csv", "JACKETS.csv", "JEANS.csv", "LINEN.csv",
    "OVERSHIRTS.csv", "PERFUMES.csv", "POLO SHIRTS.csv", "SHIRTS.csv",
    "SHOES.csv", "SHORTS.csv", "SUITS.csv", "SWEATERS_CARDIGANS.csv", "TROUSERS.csv"
]
for _f in _CATEGORY_FILES_FOR_PRICE:
    try:
        _df = pd.read_csv(_f)
        for _, _row in _df.iterrows():
            _name = str(_row.get("product_name", "")).strip().upper()
            _price_str = str(_row.get("price", "0"))
            _price_num = "".join(c for c in _price_str if c.isdigit() or c == ".")
            catalog_price_lookup[_name] = float(_price_num) if _price_num else 0.0
    except FileNotFoundError:
        pass
inventory_df["product_name"] = inventory_df["product_name"].str.strip().str.upper()

def get_stock_line(product_name):
    match = inventory_df[inventory_df["product_name"] == product_name.strip().upper()]
    if match.empty:
        return None
    stock = int(match.iloc[0]["current_stock"])
    reorder = int(match.iloc[0]["reorder_level"])
    if stock == 0:
        return "OUT OF STOCK"
    elif stock <= reorder:
        return f"stock: {stock} (LOW STOCK, reorder needed)"
    else:
        return f"stock: {stock}"

def get_relevant_products(user_message, top_k=15):
    query_embedding = embed_model.encode([user_message]).tolist()
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k
    )

    if not results["documents"] or not results["documents"][0]:
        return "No relevant products found."

    lines = []
    docs = results["documents"][0]
    metas = results["metadatas"][0]

    for doc, meta in zip(docs, metas):
        name = meta.get("name", "")
        stock_line = get_stock_line(name)
        if stock_line:
            lines.append(f"- {doc}, {stock_line}")
        else:
            lines.append(f"- {doc}")

    return "\n".join(lines)

BASE_CONTEXT = """
You are Retail AI Assistant, a business assistant for a luxury men's clothing brand.

About the brand (SAMPLE DATA - to be replaced with real data later):
- Type: Luxury men's clothing brand
- Aesthetic: Cinematic, dark, premium feel
- Run by a solo founder

Your role:
- Help solve business problems
- Help plan meetings
- Give practical, direct, actionable answers

Rules:
- Formatting: NEVER use markdown tables (with |), ** bold **, or HTML tags (<br>)
- Write plain, simple text only. Use "-" or numbers for points, one point per line
- Write in short, clear paragraphs
- Always treat the products listed in the "Relevant products" section below as the current available catalog — state their name, price and stock directly, and never refuse
- Give the user the exact "stock: X", "OUT OF STOCK" or "LOW STOCK" value listed with each product — this is real inventory data
- If a product is "LOW STOCK", proactively tell the user it should be reordered
- If "Relevant products" is empty, ask the user what they need — never say "I don't know"
- When the user asks about products, show all of them so they have a choice
"""

def get_ai_reply(user_message):

    # First, check whether this is a "sale report" message
    parsed = try_parse_sale_message(user_message)
    if parsed:
        qty, product_text = parsed
        result = record_sale(product_text, qty)
        return result["message"]

    # Otherwise, return a normal AI reply
    relevant_products = get_relevant_products(user_message)
    full_context = BASE_CONTEXT + f"\n\nRelevant products (based on user's question):\n{relevant_products}"

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {"role": "system", "content": full_context},
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content
def get_dashboard_data():
    sales_df = pd.read_csv("SALES.csv")
    inv_df = pd.read_csv("INVENTORY.csv")

    sales_summary = sales_df.groupby("product_name").agg(
        total_sold=("qty_sold", "sum")
    ).reset_index()
    sales_summary["avg_daily_sale"] = sales_summary["total_sold"] / 90

    merged = inv_df.merge(sales_summary, on="product_name", how="left")
    merged["total_sold"] = merged["total_sold"].fillna(0)
    merged["avg_daily_sale"] = merged["avg_daily_sale"].fillna(0)

    deadstock = []
    overstock = []
    reorder = []

    for _, row in merged.iterrows():
        name = row["product_name"]
        stock = row["current_stock"]
        avg_sale = row["avg_daily_sale"]
        total_sold = row["total_sold"]

        if total_sold == 0 and stock > 0:
            deadstock.append({"name": name, "stock": int(stock)})
        elif avg_sale > 0:
            days_to_sell = stock / avg_sale
            if days_to_sell > 60:
                overstock.append({"name": name, "stock": int(stock), "days_to_sell": round(days_to_sell)})
            elif days_to_sell <= 7:
                reorder.append({"name": name, "stock": int(stock), "days_left": round(days_to_sell)})

    return {
        "deadstock": deadstock[:10],
        "overstock": overstock[:10],
        "reorder": reorder[:10]
    }
def get_sales_analytics():
    sales_df = pd.read_csv("SALES.csv")

    total_revenue = round(sales_df["revenue"].sum(), 2)
    total_units = int(sales_df["qty_sold"].sum())

    # Top 5 selling products (by revenue)
    top_products = (
        sales_df.groupby("product_name")
        .agg(units_sold=("qty_sold", "sum"), revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False)
        .head(5)
        .reset_index()
    )
    top_products_list = [
        {"name": row["product_name"], "units": int(row["units_sold"]), "revenue": round(row["revenue"], 2)}
        for _, row in top_products.iterrows()
    ]

    # Category-wise revenue
    category_revenue = (
        sales_df.groupby("category")
        .agg(revenue=("revenue", "sum"))
        .sort_values("revenue", ascending=False)
        .reset_index()
    )
    category_list = [
        {"name": row["category"], "revenue": round(row["revenue"], 2)}
        for _, row in category_revenue.iterrows()
    ]

    # Daily trend (last 30 days)
    daily = (
        sales_df.groupby("date")
        .agg(revenue=("revenue", "sum"))
        .reset_index()
        .sort_values("date")
        .tail(30)
    )
    daily_trend = [
        {"date": row["date"], "revenue": round(row["revenue"], 2)}
        for _, row in daily.iterrows()
    ]

    return {
        "total_revenue": total_revenue,
        "total_units": total_units,
        "top_products": top_products_list,
        "category_revenue": category_list,
        "daily_trend": daily_trend
    }
import re
from datetime import datetime

def find_product_match(product_query):
    """Find the catalog product that best matches the name the user typed."""
    query_upper = product_query.strip().upper()
    names = inventory_df["product_name"].tolist()

    # Try an exact match first
    for name in names:
        if name == query_upper:
            return name

    # Partial match (e.g. "shirt" matches "TEXTURED SHIRT")
    matches = [name for name in names if query_upper in name or name in query_upper]
    if matches:
        return matches[0]

    return None


def record_sale(product_name, qty):
    """Record a sale: reduce the stock and append an entry to SALES.csv."""
    global inventory_df

    matched_name = find_product_match(product_name)
    if not matched_name:
        return {"success": False, "message": f"No product named '{product_name}' was found in the catalog."}

    row_idx = inventory_df[inventory_df["product_name"] == matched_name].index[0]
    current_stock = int(inventory_df.at[row_idx, "current_stock"])

    if qty > current_stock:
        return {"success": False, "message": f"Only {current_stock} units of '{matched_name}' are in stock, so {qty} cannot be sold."}

    # Reduce the stock
    inventory_df.at[row_idx, "current_stock"] = current_stock - qty
    inventory_df.to_csv("INVENTORY.csv", index=False)

    # Append a new record to SALES.csv
    category = inventory_df.at[row_idx, "category"]
    price = catalog_price_lookup.get(matched_name, 0.0)
    revenue = round(qty * price, 2)

    new_sale = pd.DataFrame([{
        "date": datetime.today().strftime("%Y-%m-%d"),
        "product_name": matched_name,
        "category": category,
        "qty_sold": qty,
        "price": price,
        "revenue": revenue
    }])

    sales_df = pd.read_csv("SALES.csv")
    sales_df = pd.concat([sales_df, new_sale], ignore_index=True)
    sales_df.to_csv("SALES.csv", index=False)

    new_stock = current_stock - qty
    return {
        "success": True,
        "message": f"Sold {qty} units of {matched_name}. New stock: {new_stock}. Revenue: Rs. {revenue}"
    }


def try_parse_sale_message(user_message):
    """Check whether the message is a sale report such as "2 shirts sold".
    Hindi phrasings ("bik gaya", "becha", ...) are also accepted as user input."""
    pattern = r"(\d+)\s+(.+?)\s+(bik gaye|bik gayi|bik gaya|sold|becha|bech diya)"
    match = re.search(pattern, user_message.lower())
    if match:
        qty = int(match.group(1))
        product_text = match.group(2)
        return qty, product_text
    return None
