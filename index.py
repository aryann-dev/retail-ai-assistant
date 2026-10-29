import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer

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

print("Loading embedding model...")
model = SentenceTransformer('BAAI/bge-m3')

chroma_client = chromadb.PersistentClient(path="./chroma_db")

try:
    chroma_client.delete_collection(name="retail_products")
    print("Old collection deleted.")
except Exception:
    print("No old collection found, creating fresh.")

collection = chroma_client.get_or_create_collection(name="retail_products")

documents = []
metadatas = []
ids = []
counter = 0

for filename, category in CATEGORY_FILES.items():
    try:
        df = pd.read_csv(filename)
        seen = set()
        for _, row in df.iterrows():
            name = str(row.get("product_name", "N/A"))
            price = str(row.get("price", "N/A"))
            details = str(row.get("details", ""))
            
            key = f"{name}-{price}"
            if key in seen:
                continue
            seen.add(key)

            text = f"{name}, category: {category}, price: {price}"
            if details and details != "nan":
                text += f", details: {details[:150]}"

            documents.append(text)
            metadatas.append({"name": name, "price": price, "category": category})
            ids.append(f"id_{counter}")
            counter += 1
        print(f"Loaded {filename}")
    except FileNotFoundError:
        print(f"Skipped {filename} (not found)")

print(f"Total products: {len(documents)}")
print("Building embeddings and storing in ChromaDB... (this may take a minute)")

embeddings = model.encode(documents).tolist()

collection.add(
    documents=documents,
    embeddings=embeddings,
    metadatas=metadatas,
    ids=ids
)

print("Done! Index built successfully.")