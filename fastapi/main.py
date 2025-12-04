import os
import sys
import time
import uuid
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
import pymysql
import json

from get_vector import *
from playlist_specs import analyze_playlist
# Add project root to sys.path to allow importing get_vector
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from fastapi.get_vector import precompute_data

load_dotenv()

# -------------------------------------------------------------
# DB CONFIG
# -------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "root")
DB_NAME = os.getenv("DB_NAME", "music")

API_BASE_URL = "http://127.0.0.1:8000"

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


# -------------------------------------------------------------
# DB CONNECTION
# -------------------------------------------------------------
def get_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )


# -------------------------------------------------------------
# CREATE TABLES (MYSQL)
# -------------------------------------------------------------
def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listening_history (
                user_id VARCHAR(255),
                track_id INT,
                last_played BIGINT,
                PRIMARY KEY (user_id, track_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INT PRIMARY KEY AUTO_INCREMENT,
                user_id VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                UNIQUE(user_id, name)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist_tracks (
                id INT PRIMARY KEY AUTO_INCREMENT,
                playlist_id INT NOT NULL,
                track_id INT NOT NULL,
                position INT NOT NULL,
                UNIQUE(playlist_id, track_id),
                FOREIGN KEY (playlist_id) REFERENCES playlists(id),
                FOREIGN KEY (track_id) REFERENCES features(id)
            )
        """)


# -------------------------------------------------------------
# GENRES COLOR
# -------------------------------------------------------------
def get_color_for_genre(label):
    if not label:
        return GENRE_COLORS[('default',)]

    label = label.lower()
    for keys, color in GENRE_COLORS.items():
        if any(k in label for k in keys):
            return color

    return GENRE_COLORS[('default',)]


# -------------------------------------------------------------
# ALL TRACK DETAILS
# -------------------------------------------------------------
def get_all_track_ids(user_id: Optional[str] = None) -> List[int]:
    with get_connection() as conn:
        cursor = conn.cursor()
        # Этот запрос может быть оптимизирован, если нам нужны только ID
        cursor.execute("SELECT id FROM features ORDER BY id")
        rows = cursor.fetchall()
    return [row['id'] for row in rows]

def get_track_details_by_ids(track_ids: List[int], user_id: Optional[str] = None):
    if not track_ids:
        return {}

    details = {}
    with get_connection() as conn:
        cursor = conn.cursor()

        placeholders = ', '.join(['%s'] * len(track_ids))

        query = f"""
            SELECT f.id, f.file, f.title, f.artist, f.primary_genre,
                   h.last_played
            FROM features f
            LEFT JOIN listening_history h ON h.track_id = f.id AND h.user_id = %s
            WHERE f.id IN ({placeholders})
        """

        params = (user_id,) + tuple(track_ids)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        covers_dir = os.path.join(os.path.dirname(__file__), "covers")

        for row in rows:
            genre = row["primary_genre"] or "Unknown"
            track_id = row["id"]
            
            cover_url = None
            if os.path.exists(os.path.join(covers_dir, f"{track_id}.jpg")):
                cover_url = f"{API_BASE_URL}/covers/{track_id}.jpg"
            elif os.path.exists(os.path.join(covers_dir, f"{track_id}.png")):
                cover_url = f"{API_BASE_URL}/covers/{track_id}.png"

            details[track_id] = {
                "id": track_id,
                "filename": row["file"],
                "title": row["title"] or "Unknown",
                "artist": row["artist"] or "Unknown",
                "genre": genre,
                "color": get_color_for_genre(genre),
                "last_played": row["last_played"],
                "cover_url": cover_url
            }
            
    return details


# -------------------------------------------------------------
# FASTAPI INIT
# -------------------------------------------------------------
app = FastAPI(debug=True)

import logging

logging.basicConfig(
    level=logging.INFO,
    format="🔥 %(levelname)s | %(message)s"
)

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.DEBUG)

def log_unhandled_exception(exc_type, exc, tb):
    import traceback
    print("💥 UNHANDLED ERROR:")
    traceback.print_exception(exc_type, exc, tb)

sys.excepthook = log_unhandled_exception


@app.on_event("startup")
async def startup_event():
    init_db()
    precompute_data()


@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "http://localhost:5173"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response


origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount("/audio", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "audio")), name="audio")
app.mount("/covers", StaticFiles(directory=os.path.join(os.path.dirname(__file__),"covers")), name="covers")


# -------------------------------------------------------------
# MODELS
# -------------------------------------------------------------
class Track(BaseModel):
    id: int
    filename: str
    title: str
    artist: str
    genre: str
    color: str
    last_played: Optional[int]
    cover_url: Optional[str] = None

class Playlist(BaseModel):
    id: int
    user_id: str
    name: str
    track_count: int

class PreviewTrack(BaseModel):
    id: int
    title: str
    artist: str
    cover_url: Optional[str] = None

class PlaylistWithPreview(Playlist):
    preview_tracks: List[PreviewTrack]
    last_track_cover_url: Optional[str] = None
    mood: Optional[str] = None



class PlaylistCreate(BaseModel):
    user_id: str
    name: str


class PlaylistAddTrack(BaseModel):
    playlist_id: int
    track_id: int


class HistoryUpdateItem(BaseModel):
    user_id: str
    track_id: int


class PlaylistTrack(Track):
    position: int


class PlaylistWithTracks(BaseModel):
    name: str
    tracks: List[PlaylistTrack]

class TracksByIdsRequest(BaseModel):
    track_ids: List[int]
    user_id: Optional[str] = None


@app.post("/api/tracks_by_ids", response_model=List[Track])
def api_get_tracks_by_ids(request: TracksByIdsRequest):
    if not request.track_ids:
        return []
    
    data = get_track_details_by_ids(request.track_ids, request.user_id)
    if not data:
        raise HTTPException(404, "Треки не найдены")

    # Сортировка результата в том же порядке, что и track_ids
    sorted_tracks = sorted(data.values(), key=lambda track: request.track_ids.index(track['id']))
    
    return list(map(Track.parse_obj, sorted_tracks))


# -------------------------------------------------------------
# API: GET ALL TRACKS
# -------------------------------------------------------------
@app.get("/api/tracks", response_model=List[int])
def api_get_tracks(user_id: Optional[str] = None):
    """
    Возвращает список ID всех треков в базе данных.
    Опциональный параметр user_id в данный момент не используется, 
    но сохранен для совместимости с будущими версиями.
    """
    track_ids = get_all_track_ids(user_id)
    if not track_ids:
        # Вместо ошибки 404 возвращаем пустой список, 
        # т.к. отсутствие треков - это не ошибка, а состояние.
        return []
    return track_ids


# -------------------------------------------------------------
# UPDATE HISTORY
# -------------------------------------------------------------
@app.post("/api/history/update")
def update_history(item: HistoryUpdateItem):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO listening_history (user_id, track_id, last_played)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE last_played = VALUES(last_played)
            """,
            (item.user_id, item.track_id, int(time.time()))
        )
    return {"status": "ok"}


# -------------------------------------------------------------
# GET LAST PLAYED
# -------------------------------------------------------------
@app.get("/api/history/last", response_model=Optional[Track])
def get_last_played(user_id: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.id, f.file, f.title, f.artist, f.primary_genre, h.last_played
            FROM listening_history h
            JOIN features f ON f.id = h.track_id
            WHERE h.user_id = %s
            ORDER BY h.last_played DESC
            LIMIT 1
        """, (user_id,))

        row = cursor.fetchone()
        if not row:
            return None

        genre = row["primary_genre"] or "Unknown"
        track_id = row["id"]
        
        cover_url = None
        covers_dir = os.path.join(os.path.dirname(__file__), "covers")
        if os.path.exists(os.path.join(covers_dir, f"{track_id}.jpg")):
            cover_url = f"{API_BASE_URL}/covers/{track_id}.jpg"
        elif os.path.exists(os.path.join(covers_dir, f"{track_id}.png")):
            cover_url = f"{API_BASE_URL}/covers/{track_id}.png"

        return Track(
            id=track_id,
            filename=row["file"],
            title=row["title"] or "Unknown",
            artist=row["artist"] or "Unknown",
            genre=genre,
            color=get_color_for_genre(genre),
            last_played=row["last_played"],
            cover_url=cover_url
        )


# -------------------------------------------------------------
# CREATE PLAYLIST
# -------------------------------------------------------------
@app.post("/api/playlists/create", response_model=Playlist)
def create_playlist(data: PlaylistCreate):
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO playlists (user_id, name) VALUES (%s, %s)",
                (data.user_id, data.name)
            )
        except:
            raise HTTPException(409, "Такой плейлист уже существует")

        return Playlist(
            id=cursor.lastrowid,
            user_id=data.user_id,
            name=data.name,
            track_count=0
        )


# -------------------------------------------------------------
# ADD TRACK TO PLAYLIST
# -------------------------------------------------------------
@app.post("/api/playlists/add_track", response_model=PlaylistTrack)
async def add_track_to_playlist(data: PlaylistAddTrack):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM playlist_tracks WHERE playlist_id = %s AND track_id = %s",
            (data.playlist_id, data.track_id)
        )
        if cursor.fetchone():
            raise HTTPException(409, "Трек уже в плейлисте")

        cursor.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM playlist_tracks WHERE playlist_id = %s",
            (data.playlist_id,)
        )
        pos = cursor.fetchone()['next_pos']

        try:
            cursor.execute(
                "INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (%s, %s, %s)",
                (data.playlist_id, data.track_id, pos)
            )
            conn.commit()
            
            # В `get_track_details_by_ids` необходимо передавать user_id, 
            # но в текущем запросе его нет. Поскольку для получения
            # деталей трека он не является критичным (влияет только на
            # `last_played`), мы можем передать None.
            details = get_track_details_by_ids([data.track_id], user_id=None).get(data.track_id)
            if not details:
                # Этот случай маловероятен, если трек существует.
                # Но если трек был удален, база данных вернет ошибку
                # внешнего ключа при INSERT, и мы не дойдем сюда.
                raise HTTPException(404, "Трек не найден")

            return PlaylistTrack(position=pos, **details)
        except pymysql.Error as db_error:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Ошибка базы данных: {db_error}")
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Неожиданная ошибка сервера: {e}")


# -------------------------------------------------------------
# GET PLAYLISTS
# -------------------------------------------------------------
from fastapi import APIRouter
from typing import List
import traceback, sys


@app.get("/api/playlists", response_model=List[PlaylistWithPreview])
def get_playlists(user_id: Optional[str] = None):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    WITH ranked_tracks AS (
                        SELECT
                            pt.playlist_id,
                            f.id,
                            COALESCE(f.title, 'Unknown Title') as title,
                            COALESCE(f.artist, 'Unknown Artist') as artist,
                            ROW_NUMBER() OVER(PARTITION BY pt.playlist_id ORDER BY pt.position) as rn
                        FROM playlist_tracks pt
                        JOIN features f ON pt.track_id = f.id
                    )
                    SELECT
                        p.id,
                        p.user_id,
                        p.name,
                        (SELECT COUNT(*) FROM playlist_tracks WHERE playlist_id = p.id) as track_count,
                        COALESCE(
                            (SELECT
                                JSON_ARRAYAGG(JSON_OBJECT('id', rt.id, 'title', rt.title, 'artist', rt.artist))
                             FROM ranked_tracks rt
                             WHERE rt.playlist_id = p.id AND rt.rn <= 4
                            ), '[]') AS preview_tracks,
                        (SELECT pt.track_id FROM playlist_tracks pt WHERE pt.playlist_id = p.id ORDER BY pt.id DESC LIMIT 1) as last_track_id
                    FROM playlists p
                    WHERE (%s IS NULL OR p.user_id = %s)
                    GROUP BY p.id, p.user_id, p.name
                    ORDER BY p.id;
                """
                params = (user_id, user_id)
                cursor.execute(query, params)
                playlists_data = cursor.fetchall()
                
                covers_dir = os.path.join(os.path.dirname(__file__), "covers")

                result = []
                for row in playlists_data:
                    if row["id"] is None:
                        continue
                    
                    preview_tracks = json.loads(row.get('preview_tracks', '[]'))
                    
                    # Add cover_url to each preview track
                    for track in preview_tracks:
                        track_id = track['id']
                        cover_url = None
                        if os.path.exists(os.path.join(covers_dir, f"{track_id}.jpg")):
                            cover_url = f"{API_BASE_URL}/covers/{track_id}.jpg"
                        elif os.path.exists(os.path.join(covers_dir, f"{track_id}.png")):
                            cover_url = f"{API_BASE_URL}/covers/{track_id}.png"
                        track['cover_url'] = cover_url

                    # Get cover for the last track in the playlist
                    last_track_id = row.get('last_track_id')
                    last_track_cover_url = None
                    if last_track_id:
                        if os.path.exists(os.path.join(covers_dir, f"{last_track_id}.jpg")):
                            last_track_cover_url = f"{API_BASE_URL}/covers/{last_track_id}.jpg"
                        elif os.path.exists(os.path.join(covers_dir, f"{last_track_id}.png")):
                            last_track_cover_url = f"{API_BASE_URL}/covers/{last_track_id}.png"

                    result.append(
                        PlaylistWithPreview(
                            id=row["id"],
                            user_id=row["user_id"],
                            name=row["name"],
                            track_count=row["track_count"] or 0,
                            preview_tracks=preview_tracks,
                            last_track_cover_url=last_track_cover_url,
                            mood=analyze_playlist(row["id"]) # Analyze and add mood
                        )
                    )

                return result

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    
    
    

class SimilarTrackFull(BaseModel):
    distance: float
    id: int
    filename: str
    title: str
    artist: str
    genre: str
    color: str
    last_played: Optional[int] = None
    cover_url: Optional[str] = None


# try:
#     from fastapi.get_vector import find_similar_tracks
# except ImportError as e:
#     # Capture the error message for use in the replacement function
#     error_message = f"Failed to import find_similar_tracks from get_vector: {e}"
#     def find_similar_tracks(*args, **kwargs):
#         raise RuntimeError(error_message)


@app.get("/api/similar/{track_id}")
def api_get_similar_tracks(track_id: int, user_id: Optional[str] = None, top_n: int = 15, metric: str = "cosine"):
    try:
        # 1. Найти похожие треки
        similar_list_raw = find_similar_tracks(track_id, top_n=top_n, metric=metric)

        if not similar_list_raw:
            return []

        # 2. Получить детали только для найденных треков
        similar_ids = [sim_id for sim_id, _, _ in similar_list_raw]
        track_details_map = get_track_details_by_ids(similar_ids, user_id)

        # 3. Собрать ответ
        response_data = []
        for sim_id, fname, dist in similar_list_raw:
            track_details = track_details_map.get(sim_id)
            if track_details:
                full_info = {
                    "distance": float(dist),
                    **track_details
                }
                response_data.append(SimilarTrackFull(**full_info))

        return response_data

    except Exception as exc:
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске похожих треков: {str(exc)}")


# -------------------------------------------------------------
# GET TRACKS FROM PLAYLIST
# -------------------------------------------------------------
@app.get("/api/playlists/{playlist_id}/tracks", response_model=PlaylistWithTracks)
def get_playlist_tracks(playlist_id: int, user_id: Optional[str] = None):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT user_id, name FROM playlists WHERE id = %s", (playlist_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(404, "Плейлист не найден")

        playlist_name = row["name"]
        # Temporarily disable user check for testing purposes
        # if user_id and row["user_id"] != user_id:
        #     raise HTTPException(403, "Доступ запрещён")

        cursor.execute("""
            SELECT pt.position, f.id
            FROM playlist_tracks pt
            JOIN features f ON pt.track_id = f.id
            WHERE pt.playlist_id = %s
            ORDER BY pt.position
        """, (playlist_id,))

        rows = cursor.fetchall()
        track_ids = [r["id"] for r in rows]
        all_details = get_track_details_by_ids(track_ids, user_id)

        out_tracks = []
        for r in rows:
            if r["id"] in all_details:
                out_tracks.append(
                    PlaylistTrack(position=r["position"], **all_details[r["id"]])
                )
        
        return PlaylistWithTracks(name=playlist_name, tracks=out_tracks)


# -------------------------------------------------------------
# SCAN ENDPOINTS
# -------------------------------------------------------------
import asyncio
from fastapi import BackgroundTasks
from scan import Scanner

# Create a single scanner instance to manage state
scanner = Scanner(music_folder="audio")
scanner_task = None

@app.post("/api/scan/start")
async def start_scan():
    global scanner, scanner_task

    if scanner.status == "running":
        raise HTTPException(status_code=409, detail="Scan is already in progress.")
    
    # If a previous scan finished, create a new scanner instance to start fresh
    if scanner.status == "finished":
        scanner = Scanner(music_folder="audio")

    scanner_task = asyncio.create_task(scanner.run())
    return {"message": "Scan started."}

@app.post("/api/scan/pause")
async def pause_scan():
    if scanner.status != "running":
        raise HTTPException(status_code=400, detail="No scan is currently running to pause.")
    scanner.pause()
    return {"message": "Scan paused."}

@app.post("/api/scan/resume")
async def resume_scan():
    if scanner.status != "paused":
        raise HTTPException(status_code=400, detail="Scan is not paused.")
    scanner.resume()
    return {"message": "Scan resumed."}

@app.post("/api/scan/cancel")
async def cancel_scan():
    global scanner_task
    if not scanner_task or scanner_task.done():
        raise HTTPException(status_code=400, detail="No active scan to cancel.")
    
    scanner_task.cancel()
    scanner.cancel()
    scanner_task = None # Clear the task reference
    
    return {"message": "Scan has been cancelled."}
    
@app.post("/api/scan/clear")
async def clear_library():
    if scanner.status == "running" or scanner.status == "paused":
        raise HTTPException(status_code=409, detail="Cannot clear library while a scan is in progress or paused.")
    
    try:
        Scanner.clear_db()
        # After clearing, it might be good to re-precompute data if needed
        precompute_data()
        return {"message": "Music library has been cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear library: {str(e)}")


@app.get("/api/scan/progress")
async def get_scan_progress():
    return scanner.get_progress()
# -------------------------------------------------------------
# TRACK COVER
# -------------------------------------------------------------
@app.get("/api/tracks/{track_id}/cover")
def get_cover(track_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file FROM features WHERE id = %s", (track_id,))
        row = cursor.fetchone()

        if not row:
            raise HTTPException(404)

        audio_path = os.path.join(os.path.dirname(__file__), "..", row["file"])
        cover_path = os.path.splitext(audio_path)[0] + ".jpg"

        if not os.path.exists(cover_path):
            cover_path = os.path.join(os.path.dirname(__file__), "..", "default-cover.png")

        return FileResponse(cover_path)
