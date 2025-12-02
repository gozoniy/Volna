import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'music_features.db')

def check_features_table():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, file FROM features LIMIT 10")
            rows = cursor.fetchall()
            if rows:
                print("Пример записей из таблицы 'features':")
                for row in rows:
                    print(f"ID: {row['id']}, File: {row['file']}")
            else:
                print("Таблица 'features' пуста или не содержит данных.")
            
            cursor.execute("PRAGMA table_info(features)")
            schema = cursor.fetchall()
            print("\nСхема таблицы 'features':")
            for col in schema:
                print(f"Name: {col['name']}, Type: {col['type']}, NotNull: {col['notnull']}, PrimaryKey: {col['pk']}")

    except Exception as e:
        print(f"Ошибка при работе с базой данных: {e}")

if __name__ == "__main__":
    check_features_table()

