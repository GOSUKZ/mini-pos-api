import logging
from datetime import datetime

import asyncpg

from config import get_settings

# Инициализируем настройки
settings = get_settings()

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[logging.FileHandler(settings.LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger("main")


# Создаем и инициализируем базу данных
async def create_database():
    """Создание базы данных и таблиц, если они не существуют"""
    conn = await asyncpg.create_pool(dsn=settings.DATABASE_URL)

    # Создаем таблицу товаров
    await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        sku_code VARCHAR UNIQUE,
        barcode VARCHAR,
        unit VARCHAR,
        sku_name VARCHAR,
        status_1c VARCHAR,
        department VARCHAR,
        group_name VARCHAR,
        subgroup VARCHAR,
        supplier VARCHAR,
        cost_price NUMERIC,
        price NUMERIC
    )
    """
    )

    # Создаем таблицу пользователей с дополнительными полями для OAuth
    await conn.execute(
        """
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
    """
    )

    await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS local_products (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # Создаем таблицу для OAuth аккаунтов
    await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS oauth_accounts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        provider VARCHAR,
        provider_user_id VARCHAR,
        access_token VARCHAR,
        refresh_token VARCHAR,
        expires_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        UNIQUE (provider, provider_user_id)
    )
    """
    )

    # Создаем таблицу для платежей
    await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS payments (
        id SERIAL PRIMARY KEY,
        order_id VARCHAR,
        payment_provider VARCHAR,
        payment_id VARCHAR UNIQUE,
        amount NUMERIC,
        currency VARCHAR DEFAULT 'USD',
        status VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        details VARCHAR
    )
    """
    )

    # Создаем таблицу аудита
    await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        action VARCHAR,
        entity VARCHAR,
        entity_id VARCHAR,
        user_id VARCHAR,
        timestamp TIMESTAMP,
        details VARCHAR
    )
    """
    )
    # Создаем таблицу для подписок
    await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS subscriptions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        plan_type VARCHAR NOT NULL,
        status VARCHAR NOT NULL,
        start_date TIMESTAMP NOT NULL,
        end_date TIMESTAMP NOT NULL,
        last_payment_id VARCHAR,
        next_payment_date TIMESTAMP,
        auto_renew BOOLEAN DEFAULT TRUE,
        amount NUMERIC NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # Создаем таблицу для планов подписок
    await conn.execute(
        """
    CREATE TABLE IF NOT EXISTS subscription_plans (
        id SERIAL PRIMARY KEY,
        name VARCHAR NOT NULL,
        plan_type VARCHAR NOT NULL,
        price NUMERIC NOT NULL,
        description VARCHAR,
        features VARCHAR,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    count = await conn.fetchval("SELECT COUNT(*) FROM subscription_plans")
    if count == 0:
        now = datetime.utcnow()
        await conn.executemany(
            """
            INSERT INTO subscription_plans (name, plan_type, price, description, features, is_active, created_at, updated_at) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            [
                (
                    "Basic Monthly",
                    "monthly",
                    9.99,
                    "Базовая месячная подписка",
                    "Базовый функционал, Поддержка по email",
                    True,
                    now,
                    now,
                ),
                (
                    "Basic Annual",
                    "annual",
                    99.99,
                    "Базовая годовая подписка",
                    "Базовый функционал, Поддержка по email, Скидка 17%",
                    True,
                    now,
                    now,
                ),
                (
                    "Premium Monthly",
                    "monthly",
                    19.99,
                    "Премиум месячная подписка",
                    "Все функции, Приоритетная поддержка, Доп. возможности",
                    True,
                    now,
                    now,
                ),
                (
                    "Premium Annual",
                    "annual",
                    199.99,
                    "Премиум годовая подписка",
                    "Все функции, Приоритетная поддержка, Доп. возможности, Скидка 17%",
                    True,
                    now,
                    now,
                ),
            ],
        )
        logger.info("Созданы стандартные планы подписки")

    # Проверяем наличие администратора в системе
    admin_count = await conn.fetchval("SELECT COUNT(*) FROM users WHERE roles LIKE '%admin%'")
    if admin_count == 0:
        from core.database import DatabaseService
        from services.auth_service import AuthService

        db_service = DatabaseService(conn)
        auth_service = AuthService(db_service)

        hashed_password = auth_service.get_password_hash("Admin123")
        await conn.execute(
            "INSERT INTO users (username, email, hashed_password, is_active, roles) VALUES ($1, $2, $3, $4, $5)",
            "admin",
            "admin@example.com",
            hashed_password,
            True,
            "admin",
        )
        logger.info("Создан пользователь admin с ролью администратора")

    return conn
