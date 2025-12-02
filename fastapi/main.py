import os
import sys
import sqlite3
import time
import uuid
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from collections import defaultdict
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

# --- Path, Config, etc. ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from get_vector import find_similar_tracks
except ImportError as e:
    def find_similar_tracks(*args, **kwargs): raise RuntimeError(f"Модуль get_vector не найден: {e}")

DB_PATH = os.getenv("DATABASE_URL", "music_features.db")

# Dependency
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
GENRE_COLORS = {
    ('rock', 'guitar', 'metal', 'punk'): '#E53935',
    ('electronic music', 'techno', 'house music', 'trance', 'electronica', 'synth-pop', 'synthesizer'): '#1E88E5',
    ('drum machine', 'dubstep', 'sampler'): '#00ACC1',
    ('hip hop music', 'rhythm and blues', 'funk', 'rapping'): '#8E24AA',
    ('singing', 'vocal music', 'soul music'): '#D81B60',
    ('ambient music', 'new-age music', 'drone music', 'easy listening'): '#43A047',
    ('classical music', 'orchestra', 'choir'): '#00897B',
    ('jazz', 'swing', 'blues'): '#FDD835',
    ('musical instrument', 'plucked string instrument', 'piano'): '#795548',
    ('speech', 'spoken word'): '#607D8B',
    ('default',): '#808080'
}
COOLDOWN_PERIOD_SECONDS = int(os.getenv("COOLDOWN_PERIOD_SECONDS", "600"))

# --- DB Functions ---
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS listening_history (user_id TEXT, track_id INTEGER, last_played INTEGER, PRIMARY KEY (user_id, track_id))")
        cursor.execute("CREATE TABLE IF NOT EXISTS playlists (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, name TEXT NOT NULL UNIQUE, UNIQUE(user_id, name))")
        cursor.execute("CREATE TABLE IF NOT EXISTS playlist_tracks (id INTEGER PRIMARY KEY AUTOINCREMENT, playlist_id INTEGER NOT NULL, track_id INTEGER NOT NULL, position INTEGER NOT NULL, UNIQUE(playlist_id, track_id), FOREIGN KEY(playlist_id) REFERENCES playlists(id), FOREIGN KEY(track_id) REFERENCES features(id))")
    
def get_color_for_genre(genre_label):
    if not genre_label: return GENRE_COLORS[('default',)]
    label_lower = genre_label.lower()
    for keywords, color in GENRE_COLORS.items():
        for keyword in keywords:
            if keyword in label_lower: return color
    return GENRE_COLORS[('default',)]

def get_all_track_details(user_id: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> Dict[int, Dict]:
    details = {}
    if conn is None: # Fallback for direct calls, though typically conn will be provided
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        close_conn = True
    else:
        close_conn = False

    try:
        cursor = conn.cursor()
        query = """
            SELECT f.id, f.file, f.title, f.artist,
                   (SELECT g.label FROM genres g WHERE g.track_id = f.id ORDER BY g.score DESC LIMIT 1) as primary_genre,
                   h.last_played
            FROM features f
            LEFT JOIN listening_history h ON f.id = h.track_id AND h.user_id = ?
        """
        for row in cursor.execute(query, (user_id,) if user_id else (None,)):
            genre = row['primary_genre'] if row['primary_genre'] else 'Unknown'
            details[row['id']] = {
                'id': row['id'],
                'filename': row['file'],
                'title': row['title'] or 'Unknown Title',
                'artist': row['artist'] or 'Unknown Artist',
                'genre': genre,
                'color': get_color_for_genre(genre),
                'last_played': row['last_played']
            }
    except Exception as e:
        print(f"DB Error fetching details: {e}")
    finally:
        if close_conn:
            conn.close()
    return details

# --- FastAPI App ---
app = FastAPI()
@app.on_event("startup")
async def startup_event(): init_db()

origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5174,http://127.0.0.1:5174")
origins = [o.strip() for o in origins_str.split(',')]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/audio", StaticFiles(directory=os.path.join(os.path.dirname(__file__), '..')), name="audio")

# --- Pydantic Models ---
class Track(BaseModel):
    id: int
    filename: str
    title: str
    artist: str
    genre: str
    color: str
    last_played: Optional[int] = None

class Playlist(BaseModel): id: int; user_id: str; name: str; track_count: int = 0
class PlaylistCreate(BaseModel): user_id: str; name: str
class PlaylistAddTrack(BaseModel): user_id: str; playlist_id: int; track_id: int
class PlaylistTrack(Track): position: int

class SimilarTrack(BaseModel): distance: float
class HistoryUpdate(BaseModel): track_id: int; user_id: str

# --- Endpoints ---
@app.get("/api/tracks", response_model=List[Track])
def get_all_tracks(user_id: Optional[str] = None, db: sqlite3.Connection = Depends(get_db)):
    track_details = get_all_track_details(user_id=user_id, conn=db)
    if not track_details: raise HTTPException(status_code=404, detail="Треки не найдены.")
    return [Track(**details) for details in track_details.values()]

class SimilarTrackFull(BaseModel):
    distance: float
    id: int
    filename: str
    title: str
    artist: str
    genre: str
    color: str
    last_played: Optional[int] = None


@app.get("/api/similar/{track_id}")
def get_similar_tracks(track_id: int, top_n: int = 15, metric: str = "cosine", db: sqlite3.Connection = Depends(get_db)):
    try:
        print(f"[DEBUG] Запрос похожих треков: track_id={track_id}, top_n={top_n}, metric={metric}")
        t0 = time.perf_counter()

        # шаг 1: вызов поиска, теперь возвращает (id, fname, dist)
        similar_list_raw = find_similar_tracks(track_id, conn=db, top_n=top_n, metric=metric)
        print(f"[TIMER] find_similar_tracks: {time.perf_counter() - t0:.3f} сек")
        print(f"[DEBUG] similar_list_raw={similar_list_raw}")

        # шаг 2: получаем детали всех треков, чтобы не делать запросы в цикле
        all_details = get_all_track_details()

        # шаг 3: формирование ответа
        response_data = []
        for sim_id, fname, dist in similar_list_raw:
            track_details = all_details.get(sim_id)
            if track_details:
                # Объединяем детали трека с расстоянием
                full_info = {
                    "distance": float(dist),
                    **track_details
                }
                response_data.append(SimilarTrackFull(**full_info))
            else:
                    print(f"[WARN] Не найдены детали для трека с ID {sim_id} и файлом {fname}")

        print(f"[DEBUG] response_data готово: {response_data}")
        return response_data
    except Exception as e:
        print(f"[ERROR] Ошибка в get_similar_tracks: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {e}")


@app.post("/api/history/update")
def update_history(item: HistoryUpdate, db: sqlite3.Connection = Depends(get_db)):
    try:
        with _db_conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO listening_history (user_id, track_id, last_played) VALUES (?, ?, ?) ON CONFLICT(user_id, track_id) DO UPDATE SET last_played=excluded.last_played;", (item.user_id, item.track_id, int(time.time())))
    except Exception as e: raise HTTPException(status_code=500, detail=f"Ошибка записи в историю: {e}")
    return {"status": "ok", "user_id": item.user_id}

@app.get("/api/history/last", response_model=Optional[Track])
def get_last_played(user_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not user_id: return None
    try:
        cursor = db.cursor()
        query = """SELECT f.id, f.file, h.last_played, (SELECT g.label FROM genres g WHERE g.track_id = f.id ORDER BY g.score DESC LIMIT 1) as primary_genre FROM listening_history h JOIN features f ON f.id = h.track_id WHERE h.user_id = ? ORDER BY h.last_played DESC LIMIT 1;"""
        row = cursor.execute(query, (user_id,)).fetchone()
        if not row: return None
        genre = row['primary_genre'] if row['primary_genre'] else 'Unknown'
        track_details = { 'id': row['id'], 'filename': row['file'], 'genre': genre, 'color': get_color_for_genre(genre), 'last_played': row['last_played'] }
        return Track(**track_details)
    except Exception as e: print(f"DB Error fetching last played: {e}")
    return None

# --- NEW PLAYLIST ENDPOINTS ---
@app.post("/api/playlists/create", response_model=Playlist)
def create_playlist(playlist_data: PlaylistCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        cursor = db.cursor()
        cursor.execute("INSERT INTO playlists (user_id, name) VALUES (?, ?)", (playlist_data.user_id, playlist_data.name))
        db.commit()
        return Playlist(id=cursor.lastrowid, user_id=playlist_data.user_id, name=playlist_data.name, track_count=0)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Плейлист с таким названием уже существует.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ошибка при создании плейлиста: {e}")

@app.post("/api/playlists/add_track", response_model=PlaylistTrack)
def add_track_to_playlist(data: PlaylistAddTrack, db: sqlite3.Connection = Depends(get_db)):
    try:
        # Проверяем, есть ли трек уже в плейлисте
        cursor = db.cursor()
        cursor.execute("SELECT id FROM playlist_tracks WHERE playlist_id = ? AND track_id = ?", (data.playlist_id, data.track_id))
        if cursor.fetchone():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Трек уже в этом плейлисте.")
        
        # Определяем позицию
        cursor.execute("SELECT MAX(position) FROM playlist_tracks WHERE playlist_id = ?", (data.playlist_id,))
        max_pos = cursor.fetchone()[0]
        new_pos = (max_pos + 1) if max_pos is not None else 0

        cursor.execute("INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)", (data.playlist_id, data.track_id, new_pos))
        db.commit()
        
        # Получаем детали трека
        all_details = get_all_track_details(user_id=data.user_id, conn=db)
        track_detail = all_details.get(data.track_id)
        if not track_detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Трек не найден.")
        
        return PlaylistTrack(position=new_pos, **track_detail)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ошибка при добавлении трека в плейлист: {e}")

@app.get("/api/playlists", response_model=List[Playlist])
def get_user_playlists(user_id: str, db: sqlite3.Connection = Depends(get_db)):
    try:
        cursor = db.cursor()
        query = """
            SELECT p.id, p.name, p.user_id, COUNT(pt.track_id) as track_count
            FROM playlists p
            LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
            WHERE p.user_id = ?
            GROUP BY p.id, p.name, p.user_id
            ORDER BY p.name;
        """
        playlists = cursor.execute(query, (user_id,)).fetchall()
        return [Playlist(**p) for p in playlists]

@app.get("/api/playlists/{playlist_id}/tracks", response_model=List[PlaylistTrack])
def get_playlist_tracks(playlist_id: int, user_id: Optional[str] = None, db: sqlite3.Connection = Depends(get_db)):
    try:
        cursor = db.cursor()
        # Проверяем принадлежность плейлиста пользователю
        if user_id:
            cursor.execute("SELECT user_id FROM playlists WHERE id = ?", (playlist_id,))
            owner_id = cursor.fetchone()
            if not owner_id or owner_id['user_id'] != user_id:
                 raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен или плейлист не найден.")

        query = """
            SELECT pt.position, f.id, f.file,
                   (SELECT g.label FROM genres g WHERE g.track_id = f.id ORDER BY g.score DESC LIMIT 1) as primary_genre
            FROM playlist_tracks pt
            JOIN features f ON pt.track_id = f.id
            WHERE pt.playlist_id = ?
            ORDER BY pt.position;
        """
        tracks_raw = cursor.execute(query, (playlist_id,)).fetchall()
        
        all_details = get_all_track_details(user_id=user_id, conn=db) # Для получения полных деталей, включая last_played/color
        
        playlist_tracks = []
        for track_raw in tracks_raw:
            full_track_detail = all_details.get(track_raw['id'])
            if full_track_detail:
                playlist_tracks.append(PlaylistTrack(position=track_raw['position'], **full_track_detail))
            else:
                # Если трек не найден в features (удален?), можно вернуть заглушку или пропустить
                pass
        return playlist_tracks
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ошибка при получении треков плейлиста: {e}")
    
    

@app.get("/api/tracks/{track_id}/cover")
    
    

def get_track_cover(track_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Возвращает обложку трека для отладки.
    Пока используем файл с расширением .jpg рядом с аудио.
    """
    try:
        cursor = db.cursor()
        row = cursor.execute("SELECT file FROM features WHERE id = ?", (track_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Трек не найден")

        # Путь к аудио файлу
        audio_file_path = os.path.join(os.path.dirname(__file__), '..', row['file'])
        # Путь к картинке: меняем расширение на .jpg или ищем рядом с файлом
        cover_file_path = os.path.splitext(audio_file_path)[0] + ".jpg"

        if not os.path.exists(cover_file_path):
            # fallback: вернём заглушку
            cover_file_path = os.path.join(os.path.dirname(__file__), '..', 'default-cover.png')

        return FileResponse(cover_file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении обложки: {e}")
    
import shutil

@app.get("/api/tracks/{track_id}/save_cover_debug")
def save_track_cover_debug(track_id: int, db: sqlite3.Connection = Depends(get_db)):
    """
    Копирует обложку трека в папку debug_covers для проверки.
    """
    try:
        debug_dir = os.path.join(os.path.dirname(__file__), '..', 'debug_covers')
        os.makedirs(debug_dir, exist_ok=True)

        cursor = db.cursor()
        row = cursor.execute("SELECT file FROM features WHERE id = ?", (track_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Трек не найден")

        audio_file_path = os.path.join(os.path.dirname(__file__), '..', row['file'])
        cover_file_path = os.path.splitext(audio_file_path)[0] + ".jpg"

        if not os.path.exists(cover_file_path):
            # fallback: используем заглушку
            cover_file_path = os.path.join(os.path.dirname(__file__), '..', 'default-cover.png')

        dest_path = os.path.join(debug_dir, f"track_{track_id}.jpg")
        shutil.copyfile(cover_file_path, dest_path)

        return {"status": "ok", "saved_to": dest_path}

@app.get("/api/tracks/debug_list")
def debug_list_tracks(db: sqlite3.Connection = Depends(get_db)):
    """
    Возвращает все треки из базы с их id и путями к файлам для проверки.
    """
    try:
        cursor = db.cursor()
        rows = cursor.execute("SELECT id, file FROM features").fetchall()
        if not rows:
            return {"status": "empty", "tracks": []}
        tracks = [{"id": row["id"], "file": row["file"]} for row in rows]
        return {"status": "ok", "tracks": tracks}
