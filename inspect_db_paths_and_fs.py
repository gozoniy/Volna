import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'music_features.db')
MUSIC_DIR = os.path.join(BASE_DIR, 'music')
YANDEX_DIR = os.path.join(BASE_DIR, 'Yandex')

def inspect_db_paths():
    print("--- Пути из базы данных 'music_features.db' (таблица 'features') ---")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT id, file FROM features LIMIT 20")
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    print(f"ID: {row['id']}, DB_File: '{row['file']}'")
            else:
                print("Таблица 'features' пуста или не содержит данных.")
    except Exception as e:
        print(f"Ошибка при чтении базы данных: {e}")

def inspect_filesystem_paths():
    print("\n--- Пути из файловой системы и их относительное представление ---")
    found_count = 0
    # Проверяем директорию 'music'
    for root, _, files in os.walk(MUSIC_DIR):
        for file in files:
            if file.lower().endswith('.mp3'):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, BASE_DIR).replace('\\', '/')
                print(f"FS_Path: '{full_path}', Relative_Path: '{relative_path}'")
                found_count += 1
                if found_count >= 10: break
        if found_count >= 10: break
    
    # Если еще не набрали 10, проверяем директорию 'Yandex'
    if found_count < 10:
        for root, _, files in os.walk(YANDEX_DIR):
            for file in files:
                if file.lower().endswith('.mp3'):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, BASE_DIR).replace('\\', '/')
                    print(f"FS_Path: '{full_path}', Relative_Path: '{relative_path}'")
                    found_count += 1
                    if found_count >= 10: break
            if found_count >= 10: break
    
    if found_count == 0:
        print("MP3-файлы не найдены в директориях 'music' или 'Yandex'.")

if __name__ == "__main__":
    inspect_db_paths()
    inspect_filesystem_paths()
