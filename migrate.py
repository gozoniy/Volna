import sqlite3
import pymysql

# --- 1. Подключение к SQLite ---
sqlite_conn = sqlite3.connect("music_features.db")
sqlite_conn.row_factory = sqlite3.Row
cursor_sqlite = sqlite_conn.cursor()

# --- 2. Подключение к MySQL ---
mysql_conn = pymysql.connect(
    host="localhost",
    user="root",
    password="root",
    database="music",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor
)
cursor_mysql = mysql_conn.cursor()

# --- 3. Получаем список таблиц в SQLite ---
tables = cursor_sqlite.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name!='sqlite_sequence';"
).fetchall()

for t in tables:
    table_name = t["name"]

    # --- 4. Получаем схему таблицы ---
    schema = cursor_sqlite.execute(f"PRAGMA table_info({table_name});").fetchall()

    # Формируем CREATE TABLE для MySQL
    columns_def = []
    for col in schema:
        col_name = col["name"]
        col_type = col["type"].upper()
        # простая маппинг типов
        if "INT" in col_type:
            mysql_type = "INT"
        elif "CHAR" in col_type or "TEXT" in col_type:
            mysql_type = "VARCHAR(255)"
        elif "REAL" in col_type or "DOUBLE" in col_type or "FLOAT" in col_type:
            mysql_type = "DOUBLE"
        else:
            mysql_type = "VARCHAR(255)"
        columns_def.append(f"`{col_name}` {mysql_type}")

    create_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(columns_def)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;"
    cursor_mysql.execute(create_sql)

    # --- 5. Копируем данные ---
    rows = cursor_sqlite.execute(f"SELECT * FROM {table_name}").fetchall()
    if rows:
        col_names = [col["name"] for col in schema]
        placeholders = ", ".join(["%s"] * len(col_names))
        insert_sql = f"INSERT INTO `{table_name}` ({', '.join(f'`{c}`' for c in col_names)}) VALUES ({placeholders})"

        for row in rows:
            cursor_mysql.execute(insert_sql, [row[c] for c in col_names])

mysql_conn.commit()

print("Миграция завершена!")

# --- 6. Закрытие соединений ---
mysql_conn.close()
sqlite_conn.close()
