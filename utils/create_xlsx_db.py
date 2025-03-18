"""
Модуль для создания базы данных и таблицы для товаров, если они не существуют.

Используется для инициализации БД перед запуском сервиса.

Example:
    $ python -m utils.create_xlsx_db
"""

import asyncio

import asyncpg
import pandas as pd


async def create_database(db_url):
    """Создание базы данных и таблицы для товаров, если они не существуют."""
    conn = await asyncpg.connect(db_url)

    # Создаем таблицу, если её нет
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            sku_code TEXT UNIQUE,
            barcode TEXT,
            unit TEXT,
            sku_name TEXT,
            status_1c TEXT,
            department TEXT,
            group_name TEXT,
            subgroup TEXT,
            supplier TEXT,
            cost_price REAL DEFAULT 0,
            price REAL DEFAULT 0
        )
        """
    )

    await conn.close()


async def parse_excel_to_postgres(excel_file, db_url):
    """Парсинг Excel-файла и добавление данных в PostgreSQL асинхронно."""
    await create_database(db_url)  # Создаем БД и таблицу (если нет)

    # Создаем пул соединений
    pool = await asyncpg.create_pool(db_url)

    # Чтение всех листов Excel-файла
    xls = pd.ExcelFile(excel_file)
    sheet_names = xls.sheet_names

    # Счетчики для отчета
    total_records = 0
    added_records = 0
    skipped_records = 0

    print(f"Начинаем обработку файла: {excel_file}")
    print(f"Найдено листов: {len(sheet_names)}")

    async with pool.acquire() as conn:
        for sheet_name in sheet_names:
            print(f"\nОбработка листа: {sheet_name}")

            try:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheet_records = len(df)
                total_records += sheet_records
                print(f"Прочитано записей: {sheet_records}")

                # Проверяем наличие колонок
                required_columns = [
                    "Код SKU",
                    "Штрих Код",
                    "Единица измерения",
                    "Наименование SKU",
                    "Статус 1С",
                    "Отдел",
                    "Группа",
                    "Подгруппа",
                    "Поставщик",
                ]
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    print(f"⚠️ Лист '{sheet_name}' пропущен (нет колонок: {missing_columns})")
                    continue

                # Пропускаем строки с пустым SKU
                df = df.dropna(subset=["Код SKU"])

                for _, row in df.iterrows():
                    try:
                        sku_code = str(row["Код SKU"]).strip()

                        # Проверяем существование товара
                        exists = await conn.fetchval(
                            "SELECT 1 FROM products WHERE sku_code = $1", sku_code
                        )
                        if exists:
                            skipped_records += 1
                            continue

                        # Вставляем данные
                        await conn.execute(
                            """
                            INSERT INTO products (
                                sku_code, barcode, unit, sku_name, status_1c,
                                department, group_name, subgroup, supplier,
                                cost_price, price
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 0, 0)
                            """,
                            sku_code,
                            str(row["Штрих Код"]).strip(),
                            str(row["Единица измерения"]).strip(),
                            str(row["Наименование SKU"]).strip(),
                            str(row["Статус 1С"]).strip(),
                            str(row["Отдел"]).strip(),
                            str(row["Группа"]).strip(),
                            str(row["Подгруппа"]).strip(),
                            str(row["Поставщик"]).strip(),
                        )
                        added_records += 1

                    except asyncpg.UniqueViolationError:
                        skipped_records += 1
                    except Exception as e:
                        print(f"❌ Ошибка при обработке строки: {e}")

                await conn.execute("COMMIT")  # Сохраняем изменения

            except Exception as e:
                print(f"❌ Ошибка на листе '{sheet_name}': {e}")

    await pool.close()

    # Выводим статистику
    print("\n" + "=" * 50)
    print("✅ ИТОГИ ИМПОРТА:")
    print(f"📦 Всего обработано записей: {total_records}")
    print(f"✅ Добавлено новых товаров: {added_records}")
    print(f"⚠️ Пропущено (уже существующих): {skipped_records}")
    print("=" * 50)


async def main():
    """
    Главная функция, которая запрашивает файл Excel и URL PostgreSQL,
    а затем вызывает функцию parse_excel_to_postgres для импорта данных.
    """
    excel_file = "data.xlsx"

    await parse_excel_to_postgres(
        excel_file, "postgresql://makkenzo:qwerty@localhost:5432/claude_data_shop"
    )

    print("\n✅ Импорт завершен!")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
