import pandas as pd
import numpy as np

# Пути к файлам
TRACKS_CSV = "data/tracks.csv"
GENRES_CSV = "data/genres.csv"

# Загружаем таблицы
tracks = pd.read_csv(TRACKS_CSV, index_col=0)
genres_map = pd.read_csv(GENRES_CSV)

# В tracks.csv колонка track.8 содержит жанр_id в виде строки "[21]"
def parse_genre(val):
    if isinstance(val, str) and val.startswith("[") and val.endswith("]"):
        try:
            return int(val.strip("[]"))
        except:
            return None
    return None

# Добавляем колонку genre_id
tracks["genre_id"] = tracks["track.8"].apply(parse_genre)

# Соединяем с genres.csv (там есть genre_id и title)
tracks = tracks.merge(genres_map, on="genre_id", how="left")

# Берём названия жанров
genre_titles = tracks["title"].dropna().unique()

# Сохраняем список жанров в classes.npy
np.save("classes.npy", genre_titles)

print("Сохранено classes.npy с жанрами:")
print(genre_titles)
