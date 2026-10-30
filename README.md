# Retail AI Assistant

An AI business assistant for a clothing store. It answers product questions using retrieval-augmented
generation (RAG) over the store's catalog, records sales from plain-language messages, and shows inventory
and sales dashboards. Products, stock and sales are stored in PostgreSQL (Neon).

## Features

### RAG product search
- Ask questions in natural language, e.g. *"Show me a black blazer for a wedding"*.
- The question is embedded with **BGE-M3** and the 15 most similar products are retrieved from **ChromaDB**.
- Each retrieved product is enriched with live stock status (`OUT OF STOCK`, `LOW STOCK`, or the exact count).
- The products are passed as context to **GPT-OSS 20B** (via Groq), which writes a short, practical answer
  and flags items that should be reordered.

### Sales recording
- Type a sale in plain language, e.g. *"2 basic blazer sold"* (Hindi phrasings such as *"2 jeans bik gaye"* also work).
- The product is matched against the catalog; the stock update and the new sale row are written to
  PostgreSQL in a single transaction. No LLM call is needed for this path.

### Dashboard
- **Inventory insights:** deadstock (no sales in 90 days), overstock (more than 60 days of stock left) and
  products to reorder soon (7 days or less remaining).
- **Sales & revenue:** total revenue and units, top 5 products, revenue by category and a 30-day revenue trend chart.

### Stock overview page (`/stock`)
- Every product with its category, price, current quantity and status: **In stock**, **Low stock**
  (at or below the reorder level) or **Out of stock**.
- Totals for all, low and out-of-stock products (click a total to filter), plus search and a category filter.
- Sorted with the lowest stock first.

## How it works

```mermaid
flowchart LR
    U[Web page] -->|question| F[Flask server]
    F -->|embed with BGE-M3| C[(ChromaDB<br/>product vectors)]
    C -->|top 15 product IDs| F
    F <-->|products, inventory, sales| P[(PostgreSQL<br/>Neon)]
    F -->|products + stock as context| G[GPT-OSS 20B<br/>via Groq]
    G -->|answer| U
    F -->|dashboards + stock page| U
```

## Tech Stack

| Area | Technology |
|---|---|
| Web server | Python, Flask |
| Embeddings | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) via `sentence-transformers` |
| Database | PostgreSQL on [Neon](https://neon.com) via `psycopg` 3 |
| Vector database | ChromaDB (persistent, local) |
| LLM | `openai/gpt-oss-20b` via the Groq API |
| Data processing | pandas |
| Front end | HTML, CSS, JavaScript, Chart.js |

## Project Structure

```
.
├── mee.py               # Flask server: /, /stock, /chat, /sales-data, /dashboard-data, /stock-data
├── business.py          # RAG search, AI replies, sale recording, dashboard and stock analytics
├── db.py                # PostgreSQL connection and queries
├── schema.sql           # Tables: products, inventory, sales
├── migrate_csv_to_db.py # One-time setup: creates tables and loads the catalog (and existing CSV data)
├── index.py             # Builds the ChromaDB product index from the products table
├── build_inventory.py   # Generates sample stock levels in the inventory table
├── build_sales.py       # Generates 90 days of sample sales in the sales table
├── templates/
│   ├── index.html       # Chat UI and dashboards
│   └── stock.html       # Stock overview page
├── requirements.txt
└── .gitignore
```

## Data Source

Product data comes from the
[Zara Dataset - Men and Women Clothing](https://www.kaggle.com/datasets/abhinavtyagi2708/zara-dataset-men-and-women-clothing)
on Kaggle (by abhinavtyagi2708). The dataset is not included in this repository; download it from Kaggle.
It was collected from Zara's public website and is intended for research and informational use, so please
respect Zara's terms of use and intellectual property.

Stock levels and sales history are **synthetic**: they are generated randomly by `build_inventory.py` and
`build_sales.py` for demonstration purposes.

## Setup

**Requirements:** Python 3.11+, a free [Groq API key](https://console.groq.com/keys) and a free
[Neon](https://neon.com) PostgreSQL database.

1. **Clone and install**
   ```bash
   git clone https://github.com/aryann-dev/retail-ai-assistant.git
   cd retail-ai-assistant
   python -m venv venv
   venv\Scripts\activate        # Windows  (macOS/Linux: source venv/bin/activate)
   pip install -r requirements.txt
   ```

2. **Add your secrets** — create a Neon project, copy its connection string, and create a file named `.env`
   in the project folder:
   ```
   GROQ_API_KEY=your-groq-api-key
   DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
   ```
   `.env` is git-ignored and must never be committed.

3. **Add the dataset** — download the Kaggle dataset and copy the CSV files from its `Men/Men/` folder into
   the project folder. The project uses these 17 files: `ACCESSORIES`, `BAGS_BACKPACKS`, `BEAUTY`, `BLAZERS`,
   `HOODIES_SWEATSHIRTS`, `JACKETS`, `JEANS`, `LINEN`, `OVERSHIRTS`, `PERFUMES`, `POLO SHIRTS`, `SHIRTS`,
   `SHOES`, `SHORTS`, `SUITS`, `SWEATERS_CARDIGANS`, `TROUSERS` (all `.csv`).

4. **Create the tables, generate sample data and build the index**
   ```bash
   python migrate_csv_to_db.py # creates the tables and loads the products
   python build_inventory.py   # fills the inventory table with sample stock levels
   python build_sales.py       # fills the sales table with 90 days of sample sales
   python index.py             # builds the ChromaDB index (downloads BGE-M3 on first run, a few GB)
   ```
   If `INVENTORY.csv` and `SALES.csv` from an older CSV-based version are present, `migrate_csv_to_db.py`
   imports them too, and the two build scripts can be skipped.

5. **Run**
   ```bash
   python mee.py
   ```
   Open http://127.0.0.1:5000 for the assistant and http://127.0.0.1:5000/stock for the stock overview.

## Notes

- Recording a sale through the chat **modifies** the `inventory` and `sales` tables. Re-run the build scripts to reset them.
- After adding or changing products in the database, re-run `python index.py` so the search index matches.
- The boutique selector on the page is a UI placeholder; all requests currently use the same catalog.
- The Flask server runs in debug mode and is intended for local use only.
