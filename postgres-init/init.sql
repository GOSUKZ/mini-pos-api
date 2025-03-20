-- Создаём временную таблицу
CREATE TEMP TABLE temp_products AS TABLE products WITH NO DATA;

-- Загружаем CSV в временную таблицу
COPY temp_products FROM '/docker-entrypoint-initdb.d/data.csv' WITH CSV HEADER;

-- Вставляем данные, игнорируя дубликаты
INSERT INTO products
SELECT * FROM temp_products
ON CONFLICT (barcode) DO NOTHING;