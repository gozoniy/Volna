import sqlite3
import numpy as np
import os
import pandas as pd
import time
from dotenv import load_dotenv

load_dotenv()

# --- вспомогательная функция для извлечения вектора признаков ---
def get_feature_vector(row):
    return np.array([
        row["bpm"],
        row["rms_energy"],
        row["spectral_centroid"],
        row["spectral_bandwidth"],
        row["spectral_rolloff"],
        row["zero_crossing_rate"],
        row["mfcc1"],
        row["mfcc2"],
        row["mfcc3"]
    ], dtype=float)

# --- читаем таблицу features ---
def load_features(db_path=None):
    if db_path is None:
        db_path = os.getenv("DATABASE_URL", "music_features.db")
    t0 = time.perf_counter()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM features")
    rows = cur.fetchall()
    conn.close()
    print(f"[TIMER] load_features: {time.perf_counter() - t0:.3f} сек")
    return rows

# --- читаем таблицу genres ---
def load_genres(db_path=None):
    if db_path is None:
        db_path = os.getenv("DATABASE_URL", "music_features.db")
    t0 = time.perf_counter()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM genres")
    rows = cur.fetchall()
    conn.close()
    print(f"[TIMER] load_genres: {time.perf_counter() - t0:.3f} сек")
    return rows

# --- строим жанровые векторы через Pandas ---
def build_genre_matrix(features, genres):
    t0 = time.perf_counter()
    df = pd.DataFrame(genres)
    df = df.rename(columns={0: "id", 1: "track_id", 2: "label", 3: "score"})
    pivot = df.pivot_table(index="track_id", columns="label", values="score", fill_value=0)
    all_labels = list(pivot.columns)

    genre_vectors = {}
    for f in features:
        if f["id"] in pivot.index:
            vec = pivot.loc[f["id"]].to_numpy(dtype=float)
        else:
            vec = np.zeros(len(all_labels))
        genre_vectors[f["file"]] = vec

    print(f"[TIMER] build_genre_matrix: {time.perf_counter() - t0:.3f} сек")
    return genre_vectors, all_labels

# --- поиск похожих треков через NumPy ---
def find_similar_tracks(target_id, db_path=None, top_n=10, metric="cosine"):
    if db_path is None:
        db_path = os.getenv("DATABASE_URL", "music_features.db")
    t0 = time.perf_counter()
    features = load_features(db_path)
    genres = load_genres(db_path)
    print(f"[TIMER] загрузка данных: {time.perf_counter() - t0:.3f} сек")

    t1 = time.perf_counter()
    genre_vectors, all_labels = build_genre_matrix(features, genres)
    print(f"[TIMER] подготовка жанров: {time.perf_counter() - t1:.3f} сек")

    t2 = time.perf_counter()
    vectors = {r["id"]: get_feature_vector(r) for r in features}
    files = {r["id"]: r["file"] for r in features}
    vectors_norm_list = [vectors[r['id']] for r in features]
    vectors_norm = np.array(vectors_norm_list)
    mean = vectors_norm.mean(axis=0)
    std = vectors_norm.std(axis=0) + 1e-8
    vectors_norm = (vectors_norm - mean) / std
    print(f"[TIMER] нормализация признаков: {time.perf_counter() - t2:.3f} сек")

    t3 = time.perf_counter()
    weights = np.array([2.0, 1.0, 0.5, 0.5, 0.5, 0.5, 1.0, 1.0, 1.0])
    genre_weight = 40.0
    combined_vectors = []
    ids = []
    for i, r in enumerate(features):
        feat_vec = vectors_norm[i] * weights
        genre_vec = genre_vectors[r["file"]]
        combined = np.concatenate([feat_vec, genre_vec * genre_weight])
        combined_vectors.append(combined.astype("float32"))
        ids.append(r["id"])
    combined_vectors = np.array(combined_vectors, dtype="float32")
    print(f"[TIMER] сборка комбинированных векторов: {time.perf_counter() - t3:.3f} сек")

    if target_id not in ids:
        raise ValueError(f"Трек с ID {target_id} не найден в базе")

    target_idx = ids.index(target_id)
    target_vec = combined_vectors[target_idx]

    t4 = time.perf_counter()
    if metric == "euclidean":
        dists = np.linalg.norm(combined_vectors - target_vec, axis=1)
    elif metric == "cosine":
        dot_products = combined_vectors @ target_vec
        norms = np.linalg.norm(combined_vectors, axis=1) * np.linalg.norm(target_vec)
        dists = 1 - dot_products / norms
    else:
        raise ValueError("Неизвестная метрика")
    print(f"[TIMER] расчет расстояний: {time.perf_counter() - t4:.3f} сек")

    dists[target_idx] = np.inf
    top_idx = np.argsort(dists)[:top_n]
    similarities = [(ids[i], files[ids[i]], dists[i]) for i in top_idx]

    return similarities

# --- запуск ---
if __name__ == "__main__":
    target_id = 14
    similar = find_similar_tracks(target_id, metric="cosine")
    print("Похожие треки:")
    for f, d in similar:
        abs_path = os.path.abspath(f).replace("\\", "/")
        print(f"{abs_path} -> distance {d:.4f}")
