import os
import re
import librosa
import numpy as np
import sqlite3
from transformers import pipeline
from mutagen import File as MutagenFile
from dotenv import load_dotenv

load_dotenv()

# --- Логика для проверки дубликатов ---

def get_metadata_info(file_path):
    """
    Пытается извлечь название и исполнителя из метаданных.
    Возвращает множество слов для сравнения.
    """
    try:
        audio = MutagenFile(file_path, easy=True)
        if audio is not None:
            title = audio.get("title", [""])[0]
            artist = audio.get("artist", [""])[0]
            combined = f"{artist} {title}".lower()
            combined = re.sub(r'[^a-z0-9\s]', ' ', combined)
            long_words = [w for w in combined.split() if len(w) > 2]
            if long_words:
                return set(long_words)
    except Exception:
        pass
    # fallback на имя файла
    return clean_filename(file_path)

def clean_filename(filename):
    """
    Очищает имя файла для сравнения:
    - убирает путь и расширение
    - приводит к нижнему регистру
    - заменяет все не-буквенно-цифровые символы на пробелы
    - убирает короткие слова (1-2 буквы)
    """
    name = os.path.basename(filename).lower()
    name = os.path.splitext(name)[0]
    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    long_words = [word for word in name.split() if len(word) > 2]
    return set(long_words)

def is_duplicate(new_file_path, existing_files, word_threshold=4):
    """
    Проверяет, является ли новый файл дубликатом одного из существующих.
    """
    new_words = get_metadata_info(new_file_path)
    for existing_file in existing_files:
        existing_words = get_metadata_info(existing_file)
        common_words_count = len(new_words.intersection(existing_words))
        if common_words_count >= word_threshold:
            print(f"Найден возможный дубликат для '{new_file_path}': '{existing_file}' ({common_words_count} общих слов). Пропуск.")
            return True
    return False

# --- Классификатор жанров ---

classifier = pipeline(
    "audio-classification",
    model="MIT/ast-finetuned-audioset-10-10-0.4593",
    device=os.getenv("CLASSIFIER_DEVICE", "0")   # <-- вот это заставит работать на GPU
)

def extract_audio_features(file_path):
    y, sr = librosa.load(file_path, sr=8000, mono=True, duration=30.0, offset=20.0)
    features = {}
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo = librosa.beat.tempo(onset_envelope=onset_env, sr=sr, hop_length=512)[0]
    features["bpm"] = float(tempo)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    key_index = chroma.mean(axis=1).argmax()
    keys = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
    features["key"] = keys[key_index]
    features["rms_energy"] = float(librosa.feature.rms(y=y).mean())
    features["spectral_centroid"] = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
    features["spectral_bandwidth"] = float(librosa.feature.spectral_bandwidth(y=y, sr=sr).mean())
    features["spectral_rolloff"] = float(librosa.feature.spectral_rolloff(y=y, sr=sr).mean())
    features["zero_crossing_rate"] = float(librosa.feature.zero_crossing_rate(y).mean())
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    features["mfcc1"] = float(mfcc[0].mean())
    features["mfcc2"] = float(mfcc[1].mean())
    features["mfcc3"] = float(mfcc[2].mean())
    return features

def extract_genres(file_path, topn):
    result = classifier(file_path)
    sorted_res = sorted(result, key=lambda x: x['score'], reverse=True)
    filtered = [r for r in sorted_res if r['label'].lower() != "music"][:topn]
    return filtered

# --- Работа с БД ---

def init_db(conn):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file TEXT UNIQUE,
            title TEXT,
            artist TEXT,
            bpm REAL,
            key TEXT,
            rms_energy REAL,
            spectral_centroid REAL,
            spectral_bandwidth REAL,
            spectral_rolloff REAL,
            zero_crossing_rate REAL,
            mfcc1 REAL,
            mfcc2 REAL,
            mfcc3 REAL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER,
            label TEXT,
            score REAL,
            FOREIGN KEY(track_id) REFERENCES features(id)
        )
    """)
    conn.commit()
    conn.close()

def get_title_artist(file_path):
    """
    Возвращает (title, artist) из метаданных, если есть.
    """
    try:
        audio = MutagenFile(file_path, easy=True)
        if audio is not None:
            title = audio.get("title", [""])[0]
            artist = audio.get("artist", [""])[0]
            return title.strip(), artist.strip()
    except Exception:
        pass
    # fallback: используем имя файла
    base = os.path.splitext(os.path.basename(file_path))[0]
    return base, ""

def save_to_db(file_path, feats, genres, conn):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    title, artist = get_title_artist(file_path)

    cur.execute("""
        INSERT OR REPLACE INTO features
        (file, title, artist, bpm, key, rms_energy, spectral_centroid, spectral_bandwidth,
         spectral_rolloff, zero_crossing_rate, mfcc1, mfcc2, mfcc3)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        file_path, title, artist,
        feats["bpm"], feats["key"], feats["rms_energy"],
        feats["spectral_centroid"], feats["spectral_bandwidth"], feats["spectral_rolloff"],
        feats["zero_crossing_rate"], feats["mfcc1"], feats["mfcc2"], feats["mfcc3"]
    ))

    track_id = cur.lastrowid
    cur.execute("DELETE FROM genres WHERE track_id = ?", (track_id,))
    for g in genres:
        cur.execute("INSERT INTO genres (track_id, label, score) VALUES (?,?,?)",
                    (track_id, g['label'], g['score']))
    conn.commit()
    conn.close()


def get_all_files_from_db(conn):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT file FROM features")
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]

def scan_music_folder(folder_path=None, db_path=None):

    if folder_path is None:

        folder_path = os.getenv("MUSIC_FOLDER", "Yandex")

    if db_path is None:

        db_path = os.getenv("DATABASE_URL", "music_features.db")



    conn = sqlite3.connect(db_path)

    conn.row_factory = sqlite3.Row # Set row_factory here for consistency

    try:

                init_db(conn)

                existing_files_in_db = get_all_files_from_db(conn)

                print(f"Найдено {len(existing_files_in_db)} треков в базе данных.")

            

            results = []

            for root, dirs, files in os.walk(folder_path):

                for f in files:

                    if f.lower().endswith((".mp3", ".wav", ".flac")):

                        file_path = os.path.join(root, f)

                        try:

                            if is_duplicate(file_path, existing_files_in_db):

                                continue

                            feats = extract_audio_features(file_path)

                            genres = extract_genres(file_path, topn=50)

                            save_to_db(file_path, feats, genres, conn)
                    existing_files_in_db.append(file_path)
                    results.append((file_path, feats, genres))
                    print(f"Добавлено: {file_path}")
                    for g in genres:
                        print(f" -> genre: {g['label']} ({g['score']:.3f})")
                except Exception as e:
                    print(f"Ошибка при обработке {file_path}: {e}")
    return results
    finally:
        conn.close()

if __name__ == "__main__":
    scan_music_folder()
