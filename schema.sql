-- Retail AI Assistant: PostgreSQL schema (Neon)

CREATE TABLE IF NOT EXISTS products (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    price       NUMERIC(10, 2) NOT NULL DEFAULT 0,
    details     TEXT,
    UNIQUE (name, price)
);

CREATE TABLE IF NOT EXISTS inventory (
    product_id     INTEGER PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
    current_stock  INTEGER NOT NULL CHECK (current_stock >= 0),
    reorder_level  INTEGER NOT NULL DEFAULT 10,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sales (
    id          BIGSERIAL PRIMARY KEY,
    sale_date   DATE NOT NULL,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    qty_sold    INTEGER NOT NULL CHECK (qty_sold > 0),
    price       NUMERIC(10, 2) NOT NULL,
    revenue     NUMERIC(12, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sales_date ON sales (sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_product ON sales (product_id);
