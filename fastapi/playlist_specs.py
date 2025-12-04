# fastapi/playlist_specs.py
import pymysql
import os
import numpy as np
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "root")
DB_NAME = os.getenv("DB_NAME", "music")

def get_connection():
    return pymysql.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS,
        database=DB_NAME, charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor, autocommit=True
    )

MOOD_CATEGORIES = {
    "energy": "Энергичный",
    "calm": "Спокойный",
    "dark": "Мрачный",
    "positive": "Светлый",
    "electronic": "Электронный",
    "organic": "Живой",
    "dense": "Плотный",
    "sparse": "Воздушный",
    "complex": "Сложный",
    "uniform": "Цельный",
}



# Keywords from genres that map to categories
GENRE_KEYWORDS = {
    "energy": ["rock", "metal", "punk", "techno", "house", "drum and bass", "energetic", "driving", "intense"],
    "calm": ["ambient", "chill", "lounge", "atmospheric", "meditative", "calm", "relaxing"],
    "dark": ["dark", "ambient", "industrial", "gothic", "gloomy", "eerie", "anxious"],
    "positive": ["happy", "pop", "funk", "disco", "upbeat", "joyful", "sunny"],
    "electronic": ["electronic", "synth", "techno", "house", "idm", "glitch", "industrial"],
    "organic": ["acoustic", "folk", "jazz", "blues", "live", "unplugged", "vocal"],
    "dense": ["dense", "heavy", "bass", "dubstep", "drone", "wall of sound"],
    "sparse": ["sparse", "minimal", "airy", "spacious", "ethereal", "reverb"],
    "complex": ["complex", "progressive", "experimental", "jazz", "idm", "avant-garde"],
    "uniform": ["minimal", "uniform", "steady", "cohesive", "minimal techno"],
}


def get_playlist_data(playlist_id: int):
    """Fetches features and genres for all tracks in a playlist."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            # Fetches audio features for tracks in the playlist
            sql_features = """
                SELECT f.*
                FROM features f
                JOIN playlist_tracks pt ON f.id = pt.track_id
                WHERE pt.playlist_id = %s
            """
            cursor.execute(sql_features, (playlist_id,))
            features = cursor.fetchall()

            if not features:
                return None, None

            track_ids = [f['id'] for f in features]
            placeholders = ','.join(['%s'] * len(track_ids))
            
            # Fetches genre labels for the same tracks
            sql_genres = f"""
                SELECT g.track_id, g.label, g.score
                FROM genres g
                WHERE g.track_id IN ({placeholders})
            """
            cursor.execute(sql_genres, tuple(track_ids))
            genres = cursor.fetchall()
            
            return features, genres

def analyze_playlist(playlist_id: int) -> str | None:
    """Analyzes a playlist and returns the top mood category."""
    features, genres = get_playlist_data(playlist_id)

    if not features:
        return None

    # --- Aggregate Features ---
    # Convert features to a list of dicts if it's not already
    feature_values = {key: [f[key] for f in features if f.get(key) is not None] for key in features[0]}
    
    avg_features = {key: np.mean(values) for key, values in feature_values.items() if np.issubdtype(np.array(values).dtype, np.number)}
    std_features = {key: np.std(values) for key, values in feature_values.items() if np.issubdtype(np.array(values).dtype, np.number)}

    # --- Initialize Scores ---
    scores = {category: 0 for category in MOOD_CATEGORIES}

    # --- Apply Rules based on Features ---
    if avg_features.get("bpm", 0) > 128 and avg_features.get("rms_energy", 0) > 0.5:
        scores["energy"] += 1
    if avg_features.get("bpm", 0) < 100 and avg_features.get("rms_energy", 0) < 0.4:
        scores["calm"] += 1
    if avg_features.get("spectral_centroid", 0) < 1500:
        scores["dark"] += 0.5
        scores["dense"] += 0.5
    if avg_features.get("spectral_centroid", 0) > 2000:
        scores["positive"] += 0.5
        scores["sparse"] += 0.5
    if avg_features.get("spectral_bandwidth", 0) > 1500:
        scores["complex"] += 0.5
    if avg_features.get("spectral_bandwidth", 0) < 1000:
        scores["uniform"] += 0.5
    if avg_features.get("rms_energy", 0) > 0.6:
        scores["dense"] += 0.5
    if avg_features.get("rms_energy", 0) < 0.3:
        scores["sparse"] += 0.5

    # --- Apply Rules based on Genres ---
    if genres:
        playlist_genre_text = ' '.join([g['label'].lower() for g in genres])
        for category, keywords in GENRE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in playlist_genre_text:
                    scores[category] += 0.2 # Add a small score for each keyword match

    # --- Determine the winning category ---
    if not any(s > 0 for s in scores.values()):
        # If no scores, maybe it's just uniform?
        if std_features.get("bpm", 100) < 15 and std_features.get("rms_energy", 1) < 0.1:
            return MOOD_CATEGORIES["uniform"]
        return None # No definitive mood found

    # Find the category with the highest score
    top_category = max(scores, key=scores.get)
    
    return MOOD_CATEGORIES[top_category]

if __name__ == '__main__':
    # Example usage: Replace with a real playlist ID from your DB
    # You might need to adjust your PYTHONPATH to run this directly
    # export PYTHONPATH=.
    test_playlist_id = 1 
    mood = analyze_playlist(test_playlist_id)
    print(f"Playlist {test_playlist_id} mood: {mood}")
