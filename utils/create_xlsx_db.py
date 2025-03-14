import pandas as pd
import aiosqlite
import os
import asyncio


async def create_database(db_name):
    """Создание базы данных и таблицы для товаров, если они не существуют"""
    conn = await aiosqlite.connect(db_name)

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

    await conn.commit()
    return conn


async def parse_excel_to_sqlite(excel_file, db_name):
    """Парсинг Excel-файла и добавление данных в SQLite асинхронно"""
    conn = await create_database(db_name)

    # Чтение всех листов Excel-файла
    xls = pd.ExcelFile(excel_file)
    sheet_names = xls.sheet_names

    # Счетчики для отчета
    total_records = 0
    added_records = 0
    skipped_records = 0

    print(f"Начинаем обработку файла: {excel_file}")
    print(f"Найдено листов: {len(sheet_names)}")

    # Обработка каждого листа
    for sheet_name in sheet_names:
        print(f"\nОбработка листа: {sheet_name}")

        # Чтение данных с текущего листа
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            sheet_records = len(df)
            total_records += sheet_records
            print(f"Прочитано записей: {sheet_records}")

            # Проверка наличия всех необходимых колонок
            required_columns = [
                'Код SKU', 'Штрих Код', 'Единица измерения', 'Наименование SKU',
                'Статус 1С', 'Отдел', 'Группа', 'Подгруппа', 'Поставщик'
            ]

            # Проверяем наличие всех колонок
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"ВНИМАНИЕ: На листе '{sheet_name}' отсутствуют колонки: {missing_columns}")
                print("Этот лист будет пропущен")
                continue

            # Пропускаем строки с пустыми значениями SKU
            df = df.dropna(subset=['Код SKU'])

            # Добавляем записи в базу данных
            for _, row in df.iterrows():
                try:
                    # Проверяем, существует ли уже этот товар в базе
                    async with conn.execute("SELECT sku_code FROM products WHERE sku_code = ?",
                                            (row['Код SKU'],)) as cursor:
                        result = await cursor.fetchone()

                    if result:
                        # Товар уже существует, пропускаем
                        skipped_records += 1
                        continue

                    # Добавляем новый товар
                    await conn.execute('''
                    INSERT INTO products (
                        sku_code, barcode, unit, sku_name, status_1c, 
                        department, group_name, subgroup, supplier,
                        cost_price, price
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['Код SKU'],
                        row['Штрих Код'],
                        row['Единица измерения'],
                        row['Наименование SKU'],
                        row['Статус 1С'],
                        row['Отдел'],
                        row['Группа'],
                        row['Подгруппа'],
                        row['Поставщик'],
                        0,  # Пустое значение для себестоимости
                        0  # Пустое значение для цены
                    ))
                    added_records += 1

                except aiosqlite.IntegrityError:
                    # Обработка ошибки уникальности
                    skipped_records += 1
                    continue
                except Exception as e:
                    print(f"Ошибка при обработке строки: {e}")
                    continue

            # Сохраняем изменения
            await conn.commit()

        except Exception as e:
            print(f"Ошибка при обработке листа '{sheet_name}': {e}")

    # Выводим общую статистику
    print("\n" + "=" * 50)
    print("ИТОГИ ИМПОРТА:")
    print(f"Всего обработано записей: {total_records}")
    print(f"Добавлено новых товаров: {added_records}")
    print(f"Пропущено (уже существующих): {skipped_records}")
    print("=" * 50)

    # Закрываем соединение
    await conn.close()


async def main():
    # Путь к Excel файлу (можно изменить)
    excel_file = input("Введите путь к Excel файлу: ")

    # Проверка существования файла
    if not os.path.exists(excel_file):
        print(f"Ошибка: Файл '{excel_file}' не найден.")
        return

    # Имя базы данных SQLite (можно изменить)
    db_name = input("Введите имя файла базы данных SQLite (по умолчанию 'products.db'): ") or "products.db"

    # Запускаем парсинг
    await parse_excel_to_sqlite(excel_file, db_name)

    print(f"\nОбработка завершена. База данных сохранена в файл '{db_name}'")


if __name__ == "__main__":
    # Запускаем асинхронную программу
    asyncio.run(main())