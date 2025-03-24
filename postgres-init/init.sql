CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            sku_code VARCHAR,
            barcode VARCHAR UNIQUE,
            unit VARCHAR,
            sku_name VARCHAR,
            status_1c VARCHAR,
            department VARCHAR,
            group_name VARCHAR,
            subgroup VARCHAR,
            supplier VARCHAR,
            cost_price NUMERIC,
            price NUMERIC
        );

-- Создаём временную таблицу
CREATE TEMP TABLE temp_products AS TABLE products WITH NO DATA;

-- Загружаем CSV в временную таблицу
COPY temp_products FROM '/docker-entrypoint-initdb.d/data.csv' WITH CSV HEADER;

-- Вставляем данные, игнорируя дубликаты
INSERT INTO products
SELECT * FROM temp_products
ON CONFLICT (barcode) DO NOTHING;

CREATE INDEX idx_sales_user_id ON sales (user_id);
CREATE INDEX idx_sales_status ON sales (status);
CREATE INDEX idx_sales_created_at ON sales (created_at);
CREATE INDEX idx_sales_order_id ON sales (order_id);

CREATE INDEX idx_sales_items_product_id ON sales_items (product_id);