import chromadb
from sentence_transformers import SentenceTransformer

import db

products = db.get_products()
if products.empty:
    print("No products in the database. Run migrate_csv_to_db.py first.")
    raise SystemExit(1)

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

for _, row in products.iterrows():
    name = row["name"]
    category = row["category"]
    price = f"₹ {row['price']:,.2f}"
    details = row["details"]

    text = f"{name}, category: {category}, price: {price}"
    if isinstance(details, str) and details:
        text += f", details: {details[:150]}"

    documents.append(text)
    metadatas.append({"product_id": int(row["id"]), "name": name, "price": price, "category": category})
    ids.append(f"product_{int(row['id'])}")

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
