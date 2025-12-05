import numpy as np
import os
import pandas as pd
import time
from dotenv import load_dotenv
import pymysql
import traceback

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "root")
DB_NAME = os.getenv("DB_NAME", "music")

# Global cache for all pre-computed data
CACHED_DATA = {}

def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

def get_feature_vector(row):
    return np.array([
        row["bpm"], row["rms_energy"], row["spectral_centroid"],
        row["spectral_bandwidth"], row["spectral_rolloff"], row["zero_crossing_rate"],
        row["mfcc1"], row["mfcc2"], row["mfcc3"]
    ], dtype=float)

def load_features():
    t0 = time.perf_counter()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM features")
            rows = cur.fetchall()
    print(f"[TIMER] load_features: {time.perf_counter() - t0:.3f} сек")
    return rows

def load_genres():
    t0 = time.perf_counter()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM genres")
            rows = cur.fetchall()
    print(f"[TIMER] load_genres: {time.perf_counter() - t0:.3f} сек")
    return rows

def build_genre_matrix(features, genres):
    t0 = time.perf_counter()
    if not genres:
        print("[WARN] No genres found in database. Genre matrix will be empty.")
        return {}, []
    df = pd.DataFrame(genres)
    pivot = df.pivot_table(index="track_id", columns="label", values="score", fill_value=0)
    all_labels = list(pivot.columns)
    genre_vectors = {
        f["file"]: pivot.loc[f["id"]].to_numpy(dtype=float) if f["id"] in pivot.index else np.zeros(len(all_labels))
        for f in features
    }
    print(f"[TIMER] build_genre_matrix: {time.perf_counter() - t0:.3f} сек")
    return genre_vectors, all_labels

def precompute_data():
    """
    Loads all data from DB and pre-computes the vectors for similarity search.
    This should be called once on application startup.
    """
    print("Начинаем предварительный расчет данных...")
    t_start = time.perf_counter()

    features = load_features()
    genres = load_genres()
    print(f"[TIMER] загрузка данных: {time.perf_counter() - t_start:.3f} сек")

    genre_vectors, _ = build_genre_matrix(features, genres)

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
    
    # Handle case where there are no genres
    if not genre_vectors:
        print("[WARN] No genre vectors were built. Proceeding without genre information.")
        fallback_genre_vec = np.array([])
    else:
        fallback_genre_vec = np.zeros_like(next(iter(genre_vectors.values())))

    for i, r in enumerate(features):
        try:
            feat_vec = vectors_norm[i] * weights
            genre_vec = genre_vectors.get(r["file"], fallback_genre_vec)
            
            # Ensure genre_vec is not empty if fallback was used and genre_vectors was empty
            if genre_vec.size == 0 and fallback_genre_vec.size > 0:
                 genre_vec = fallback_genre_vec
            
            combined = np.concatenate([feat_vec, genre_vec * genre_weight])
            combined_vectors.append(combined.astype("float32"))
            ids.append(r["id"])
        except Exception as e:
            print(f"[WARN] Failed to process track ID {r.get('id', 'N/A')} during pre-computation: {e}")
            traceback.print_exc()
            # Optionally, remove it from 'files' as well if it won't be in the cache
            if r.get('id') in files:
                del files[r.get('id')]
    
    # Store results in the global cache
    CACHED_DATA["ids"] = np.array(ids)
    CACHED_DATA["files"] = files
    CACHED_DATA["combined_vectors"] = np.array(combined_vectors, dtype="float32")
    
    print(f"[TIMER] сборка комбинированных векторов: {time.perf_counter() - t3:.3f} сек")
    print(f"Предварительный расчет данных завершен за {time.perf_counter() - t_start:.3f} сек")

def find_similar_tracks(target_id, user_id: str = None, top_n=10, metric="cosine"):
    t0 = time.perf_counter()

    if not CACHED_DATA:
        print("[WARN] Данные не были предварительно рассчитаны. Загрузка по требованию. Это будет медленно.")
        precompute_data()

    ids = CACHED_DATA["ids"]
    files = CACHED_DATA["files"]
    combined_vectors = CACHED_DATA["combined_vectors"]

    try:
        target_idx_arr = np.where(ids == target_id)[0]
        if len(target_idx_arr) == 0:
            raise ValueError(f"Трек с ID {target_id} не найден в кеше")
        target_idx = target_idx_arr[0]
        target_vec = combined_vectors[target_idx]
    except (KeyError, IndexError):
        raise ValueError(f"Трек с ID {target_id} не найден в кеше")

    t4 = time.perf_counter()
    if metric == "euclidean":
        dists = np.linalg.norm(combined_vectors - target_vec, axis=1)
    elif metric == "cosine":
        dot_products = combined_vectors @ target_vec
        norms = np.linalg.norm(combined_vectors, axis=1) * np.linalg.norm(target_vec)
        norms[norms == 0] = 1e-8 # avoid division by zero
        dists = 1 - dot_products / norms
    else:
        raise ValueError("Неизвестная метрика")
    print(f"[TIMER] расчет расстояний: {time.perf_counter() - t4:.3f} сек")

    dists[target_idx] = np.inf

    # Get recently played tracks
    recently_played = set()
    if user_id:
        with get_connection() as conn:
            with conn.cursor() as cur:
                ten_minutes_ago = int(time.time()) - 600
                cur.execute(
                    "SELECT track_id FROM listening_history WHERE user_id = %s AND last_played > %s",
                    (user_id, ten_minutes_ago)
                )
                rows = cur.fetchall()
                recently_played = {row['track_id'] for row in rows}

    # Fetch more tracks to have a buffer for filtering
    initial_top_n = top_n + len(recently_played) + 50 
    top_idx = np.argsort(dists)

    similarities = []
    for i in top_idx:
        track_id = ids[i]
        if track_id != target_id and track_id not in recently_played:
            similarities.append((track_id, files[track_id], dists[i]))
            if len(similarities) >= top_n:
                break
    
    # Filter out non-finite values to prevent JSON serialization errors
    final_similarities = []
    for sid, fname, dist in similarities:
        if np.isfinite(dist):
            final_similarities.append((sid, fname, dist))
        else:
            print(f"[WARN] Skipping track ID {sid} from similar results due to non-finite distance.")
            
    print(f"[TIMER] find_similar_tracks (только поиск): {time.perf_counter() - t0:.3f} сек")
    
    return final_similarities

if __name__ == "__main__":
    precompute_data()
    target_id = 14
    similar = find_similar_tracks(target_id, metric="cosine")
    print("Похожие треки:")
    for tid, f, d in similar:
        print(f"{tid}: {f} -> distance {d:.4f}")