DROP SCHEMA IF EXISTS retail CASCADE;
CREATE SCHEMA retail;

CREATE TABLE retail.transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    invoice_no TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    description TEXT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    invoice_date TIMESTAMP NOT NULL,
    unit_price NUMERIC(12, 3) NOT NULL CHECK (unit_price > 0),
    customer_id TEXT NOT NULL,
    country TEXT NOT NULL,
    source_period TEXT NOT NULL,
    revenue NUMERIC(14, 3) NOT NULL CHECK (revenue > 0)
);
