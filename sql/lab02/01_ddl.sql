-- sql/lab02/01_ddl.sql
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS audit;

-- ============================================================================
-- 1. AUDIT
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit.pipeline_runs (
    run_id SERIAL PRIMARY KEY,
    batch_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS audit.run_file_stats (
    stat_id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES audit.pipeline_runs(run_id) ON DELETE CASCADE,
    source_file TEXT NOT NULL,
    input_count INTEGER NOT NULL DEFAULT 0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    accepted_count INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT chk_run_file_balance CHECK (input_count = duplicate_count + rejected_count + accepted_count)
);

CREATE TABLE IF NOT EXISTS audit.rejected_rows (
    reject_id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES audit.pipeline_runs(run_id) ON DELETE CASCADE,
    batch_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    entity_key TEXT,
    raw_payload JSONB NOT NULL,
    reason_code TEXT NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- ============================================================================
-- 2. STAGING (усі реальні поля з CSV як TEXT + технічні поля аудиту)
-- ============================================================================

DROP TABLE IF EXISTS stg.order_items CASCADE;
DROP TABLE IF EXISTS stg.orders CASCADE;
DROP TABLE IF EXISTS stg.products CASCADE;
DROP TABLE IF EXISTS stg.merchants CASCADE;
DROP TABLE IF EXISTS stg.customers CASCADE;

CREATE TABLE stg.customers (
    customer_id TEXT,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    city TEXT,
    service_zone_id TEXT,
    registered_at TEXT,
    customer_status TEXT,
    batch_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE stg.merchants (
    merchant_id TEXT,
    merchant_name TEXT,
    merchant_type TEXT,
    city TEXT,
    service_zone_id TEXT,
    opened_at TEXT,
    merchant_status TEXT,
    batch_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE stg.products (
    product_id TEXT,
    merchant_id TEXT,
    product_name TEXT,
    category TEXT,
    unit_price_uah TEXT,
    is_active TEXT,
    updated_at TEXT,
    batch_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE stg.orders (
    order_id TEXT,
    customer_id TEXT,
    merchant_id TEXT,
    created_at TEXT,
    order_status TEXT,
    currency TEXT,
    subtotal_amount TEXT,
    delivery_fee TEXT,
    discount_amount TEXT,
    total_amount TEXT,
    batch_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE stg.order_items (
    order_item_id TEXT,
    order_id TEXT,
    product_id TEXT,
    quantity TEXT,
    unit_price TEXT,
    line_discount TEXT,
    line_total TEXT,
    currency TEXT,
    batch_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    source_row_number INTEGER NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE OR REPLACE FUNCTION stg.try_cast_timestamptz(val text)
RETURNS timestamptz AS $$
BEGIN
    RETURN val::timestamptz;
EXCEPTION WHEN OTHERS THEN
    RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
-- ============================================================================
-- 3. CORE (цільова реляційна модель з PK, FK та CHECK)
-- ============================================================================

DROP TABLE IF EXISTS core.order_items CASCADE;
DROP TABLE IF EXISTS core.orders CASCADE;
DROP TABLE IF EXISTS core.products CASCADE;
DROP TABLE IF EXISTS core.merchants CASCADE;
DROP TABLE IF EXISTS core.customers CASCADE;

CREATE TABLE core.customers (
    customer_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    city TEXT NOT NULL,
    registered_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE core.merchants (
    merchant_id TEXT PRIMARY KEY,
    merchant_name TEXT NOT NULL,
    city TEXT NOT NULL,
    opened_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE core.products (
    product_id TEXT PRIMARY KEY,
    merchant_id TEXT NOT NULL REFERENCES core.merchants(merchant_id),
    product_name TEXT NOT NULL,
    unit_price_uah NUMERIC(12, 2) NOT NULL CHECK (unit_price_uah > 0),
    is_active BOOLEAN NOT NULL
);

CREATE TABLE core.orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES core.customers(customer_id),
    merchant_id TEXT NOT NULL REFERENCES core.merchants(merchant_id),
    created_at TIMESTAMPTZ NOT NULL,
    order_status TEXT NOT NULL,
    currency VARCHAR(3) NOT NULL,
    subtotal_amount NUMERIC(12, 2) NOT NULL CHECK (subtotal_amount >= 0),
    delivery_fee NUMERIC(12, 2) NOT NULL CHECK (delivery_fee >= 0),
    discount_amount NUMERIC(12, 2) NOT NULL CHECK (discount_amount >= 0),
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0)
);

CREATE TABLE core.order_items (
    order_item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES core.orders(order_id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES core.products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    line_discount NUMERIC(12, 2) NOT NULL CHECK (line_discount >= 0),
    line_total NUMERIC(12, 2) NOT NULL CHECK (line_total >= 0),
    currency VARCHAR(3) NOT NULL
);
