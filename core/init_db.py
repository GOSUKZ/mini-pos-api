import logging

import asyncpg

from config import get_settings
from services.auth_service import AuthService
from services.database.base import DatabaseService

# Инициализируем настройки
settings = get_settings()

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[logging.FileHandler(settings.LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger("main")

TABLES = {
    # "warehouses": """
    #     CREATE TABLE IF NOT EXISTS warehouses (
    #         id SERIAL PRIMARY KEY,
    #         user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    #         name VARCHAR,
    #         location VARCHAR,
    #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #         updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    #     )
    # """,
    # "warehouse_products": """
    #     CREATE TABLE IF NOT EXISTS warehouse_products (
    #         id SERIAL PRIMARY KEY,
    #         warehouse_id INTEGER NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
    #         product_id INTEGER NOT NULL REFERENCES local_products(id) ON DELETE CASCADE,
    #         quantity INTEGER NOT NULL DEFAULT 0,
    #         UNIQUE (warehouse_id, product_id)
    #     )
    # """,
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR UNIQUE,
            email VARCHAR,
            hashed_password VARCHAR,
            is_active BOOLEAN DEFAULT TRUE,
            roles VARCHAR,
            auth_provider VARCHAR DEFAULT 'local',
            name VARCHAR,
            picture VARCHAR
        )
    """,
    "local_products": """
        CREATE TABLE IF NOT EXISTS local_products (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            sku_code VARCHAR,
            barcode VARCHAR,
            unit VARCHAR,
            sku_name VARCHAR,
            status_1c VARCHAR,
            department VARCHAR,
            group_name VARCHAR,
            subgroup VARCHAR,
            supplier VARCHAR,
            cost_price NUMERIC,
            price NUMERIC,
            quantity NUMERIC DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "sales": """
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            order_id VARCHAR UNIQUE NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id),
            total_amount NUMERIC NOT NULL,
            currency VARCHAR NOT NULL DEFAULT 'KZT',
            status VARCHAR NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "order_counter": """
        CREATE TABLE IF NOT EXISTS order_counter (
            id SERIAL PRIMARY KEY,
            last_number INTEGER NOT NULL DEFAULT 10000
        )
    """,
    "sales_items": """
        CREATE TABLE IF NOT EXISTS sales_items (
            id SERIAL PRIMARY KEY,
            sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
            product_id INTEGER NOT NULL REFERENCES local_products(id),
            quantity INTEGER NOT NULL,
            price NUMERIC NOT NULL,
            cost_price NUMERIC NOT NULL,
            total NUMERIC NOT NULL
        )
    """,
    "receipts": """
        CREATE TABLE IF NOT EXISTS receipts (
            id SERIAL PRIMARY KEY,
            order_id VARCHAR NOT NULL REFERENCES sales(order_id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES users(id),
            total_amount NUMERIC NOT NULL,
            currency VARCHAR NOT NULL DEFAULT 'KZT',
            payment_method VARCHAR NOT NULL,  -- Например: "cash", "card", "bank_transfer"
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "audit_log": """
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            action VARCHAR,
            entity VARCHAR,
            entity_id VARCHAR,
            user_id VARCHAR,
            timestamp TIMESTAMP,
            details VARCHAR
        )
    """,
}


async def create_database():
    """Создание базы данных и таблиц, если они не существуют"""
    conn = await asyncpg.create_pool(dsn=settings.DATABASE_URL)
    async with conn.acquire() as connection:
        for table, query in TABLES.items():
            await connection.execute(query)
            logger.info("Таблица %s проверена/создана", table)

        admin_count = await connection.fetchval(
            "SELECT COUNT(*) FROM users WHERE roles LIKE '%admin%'"
        )
        if admin_count == 0:
            db_service = DatabaseService(connection)
            auth_service = AuthService(db_service)
            hashed_password = auth_service.get_password_hash("Admin123")
            await connection.execute(
                "INSERT INTO users (username, email, hashed_password, is_active, roles) VALUES ($1, $2, $3, $4, $5)",
                "admin",
                "admin@example.com",
                hashed_password,
                True,
                "admin",
            )
            logger.info("Создан пользователь admin с ролью администратора")

        last_number = await connection.fetchval("SELECT last_number FROM order_counter")
        if last_number is None:
            await connection.execute("INSERT INTO order_counter (last_number) VALUES ($1)", 10000)
    return conn
