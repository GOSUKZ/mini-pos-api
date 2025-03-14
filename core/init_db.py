import logging
import aiosqlite
from datetime import datetime
from typing import Dict, List, Optional, Any
from config import get_settings

# Инициализируем настройки
settings = get_settings()

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

# Создаем и инициализируем базу данных
async def create_database(db_name):
    """Создание базы данных и таблиц, если они не существуют"""
    conn = await aiosqlite.connect(db_name)
    conn.row_factory = aiosqlite.Row

    # Создаем таблицу товаров
    await conn.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sku_code TEXT UNIQUE,
        barcode TEXT,
        unit TEXT,
        sku_name TEXT,
        status_1c TEXT,
        department TEXT,
        group_name TEXT,
        subgroup TEXT,
        supplier TEXT,
        cost_price REAL,
        price REAL
    )
    ''')

    # Создаем таблицу пользователей с дополнительными полями для OAuth
    await conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        hashed_password TEXT,
        is_active BOOLEAN,
        roles TEXT,
        auth_provider TEXT DEFAULT 'local',
        name TEXT,
        picture TEXT
    )
    ''')

    # Создаем таблицу для OAuth аккаунтов
    await conn.execute('''
    CREATE TABLE IF NOT EXISTS oauth_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        provider TEXT,
        provider_user_id TEXT,
        access_token TEXT,
        refresh_token TEXT,
        expires_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
        UNIQUE (provider, provider_user_id)
    )
    ''')

    # Создаем таблицу для платежей
    await conn.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        payment_provider TEXT,
        payment_id TEXT UNIQUE,
        amount REAL,
        currency TEXT DEFAULT 'USD',
        status TEXT,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        details TEXT
    )
    ''')

    # Создаем таблицу аудита
    await conn.execute('''
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT,
        entity TEXT,
        entity_id TEXT,
        user_id TEXT,
        timestamp TIMESTAMP,
        details TEXT
    )
    ''')
    # Создаем таблицу для подписок
    await conn.execute('''
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        plan_type TEXT NOT NULL,  -- 'monthly' или 'annual'
        status TEXT NOT NULL,     -- 'active', 'expired', 'cancelled', 'pending'
        start_date TIMESTAMP NOT NULL,
        end_date TIMESTAMP NOT NULL,
        last_payment_id TEXT,
        next_payment_date TIMESTAMP,
        auto_renew BOOLEAN DEFAULT TRUE,
        amount REAL NOT NULL,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')

    # Создаем таблицу для планов подписок
    await conn.execute('''
    CREATE TABLE IF NOT EXISTS subscription_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        plan_type TEXT NOT NULL,  -- 'monthly' или 'annual'
        price REAL NOT NULL,
        description TEXT,
        features TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL
    )
    ''')
    await conn.commit()
    # Проверяем наличие планов подписки
    async with conn.execute("SELECT COUNT(*) as count FROM subscription_plans") as cursor:
        result = await cursor.fetchone()
        if result["count"] == 0:
            # Создаем стандартные планы подписки
            now = datetime.utcnow()

            # Месячный план
            await conn.execute(
                "INSERT INTO subscription_plans (name, plan_type, price, description, features, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("Basic Monthly", "monthly", 9.99, "Базовая месячная подписка", "Базовый функционал,Поддержка по email",
                 True, now, now)
            )

            # Годовой план
            await conn.execute(
                "INSERT INTO subscription_plans (name, plan_type, price, description, features, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("Basic Annual", "annual", 99.99, "Базовая годовая подписка",
                 "Базовый функционал,Поддержка по email,Скидка 17%", True, now, now)
            )

            # Премиум месячный план
            await conn.execute(
                "INSERT INTO subscription_plans (name, plan_type, price, description, features, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("Premium Monthly", "monthly", 19.99, "Премиум месячная подписка",
                 "Все функции,Приоритетная поддержка,Дополнительные возможности", True, now, now)
            )

            # Премиум годовой план
            await conn.execute(
                "INSERT INTO subscription_plans (name, plan_type, price, description, features, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("Premium Annual", "annual", 199.99, "Премиум годовая подписка",
                 "Все функции,Приоритетная поддержка,Дополнительные возможности,Скидка 17%", True, now, now)
            )

            await conn.commit()
            logger.info("Созданы стандартные планы подписки")

    # Проверяем наличие администратора в системе
    async with conn.execute("SELECT COUNT(*) as count FROM users WHERE roles LIKE '%admin%'") as cursor:
        result = await cursor.fetchone()
        if result["count"] == 0:
            # Создаем админа по умолчанию, если его нет
            from services.auth_service import AuthService
            from core.database import DatabaseService

            db_service = DatabaseService(conn)
            auth_service = AuthService(db_service)

            hashed_password = auth_service.get_password_hash("Admin123")

            await conn.execute(
                "INSERT INTO users (username, email, hashed_password, is_active, roles) VALUES (?, ?, ?, ?, ?)",
                ("admin", "admin@example.com", hashed_password, True, "admin")
            )
            await conn.commit()

            logger.info("Создан пользователь admin с ролью администратора")

    return conn




