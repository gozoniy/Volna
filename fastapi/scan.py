import os
import asyncio
import traceback
os.environ["TORCHCODEC_DISABLE"] = "1"

import re
import librosa
import numpy as np
import pymysql
from transformers import pipeline
from mutagen import File as MutagenFile
from dotenv import load_dotenv
from get_vector import precompute_data

load_dotenv()

# -----------------------------
# MySQL CONFIG
# -----------------------------
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "root")
DB_NAME = os.getenv("DB_NAME", "music")

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

class Scanner:
    def __init__(self, music_folder="audio"):
        self.music_folder = os.path.join(os.path.dirname(__file__), music_folder)
        self.covers_folder = os.path.join(os.path.dirname(__file__), "covers")
        self.status = "idle"
        self.total_files = 0
        self.processed_files = 0
        self.current_filename = ""
        self.files_to_scan = []
        self.existing_files_in_db = []
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self.semaphore = asyncio.Semaphore(os.cpu_count() or 4)

        self.classifier = pipeline("audio-classification", model="MIT/ast-finetuned-audioset-10-10-0.4593")

    def get_progress(self):
        return {
            "status": self.status, "total": self.total_files,
            "current": self.processed_files, "filename": self.current_filename,
        }

    async def _run_in_executor(self, func, *args):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    def _discover_files(self):
        self.files_to_scan = []
        for root, _, files in os.walk(self.music_folder):
            for f in files:
                if f.lower().endswith((".mp3", ".wav", ".flac")):
                    self.files_to_scan.append(os.path.join(root, f))
        self.total_files = len(self.files_to_scan)

    def _get_existing_files_from_db(self):
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT file FROM features")
                rows = cursor.fetchall()
                self.existing_files_in_db = [os.path.join(self.music_folder, row["file"]) for row in rows]

    def _reset_state(self):
        self.status = "idle"
        self.processed_files = 0
        self.total_files = 0
        self.current_filename = ""
        self.files_to_scan = []
        self.existing_files_in_db = []
        self._pause_event.set()

    async def _process_file(self, file_path):
        async with self.semaphore:
            await self._pause_event.wait()
            
            if file_path in self.existing_files_in_db:
                # This check is now redundant if we pre-filter but safer to keep
                self.processed_files += 1
                return

            try:
                is_dup = await self._run_in_executor(self._is_duplicate, file_path)
                if is_dup:
                    return

                feats = await self._run_in_executor(self._extract_audio_features, file_path)
                if feats is None:
                    return

                genres = await self._run_in_executor(self._extract_genres, file_path)
                await self._save_to_db(file_path, feats, genres)

                # This is not perfectly thread-safe but okay for this use case
                self.existing_files_in_db.append(file_path)
                print(f"[OK] {file_path}")

            except Exception as e:
                print(f"[ERROR] processing {file_path}: {e}")
                traceback.print_exc()
            finally:
                self.processed_files += 1
                self.current_filename = os.path.basename(file_path)

    async def run(self):
        if self.status == "running": return
        self._reset_state()
        self.status = "running"
        
        try:
            self._discover_files()
            self._get_existing_files_from_db()

            # Pre-filter files to avoid redundant checks in parallel tasks
            files_to_process = [fp for fp in self.files_to_scan if fp not in self.existing_files_in_db]
            self.total_files = len(files_to_process) # Update total to reflect only new files
            self.processed_files = 0


            tasks = [self._process_file(file_path) for file_path in files_to_process]
            await asyncio.gather(*tasks)

            self.status = "finished"
            self.current_filename = ""
            print("Scan finished. Re-computing data for similarity search...")
            await self._run_in_executor(precompute_data)
            print("Re-computing finished.")

        except asyncio.CancelledError:
            self._reset_state()
            print("Scan was cancelled.")
            raise
        except Exception as e:
            self._reset_state()
            print(f"[ERROR] Unhandled exception in scanner: {e}")
            traceback.print_exc()

    def pause(self):
        if self.status == "running":
            self.status = "paused"
            self._pause_event.clear()

    def resume(self):
        if self.status == "paused":
            self.status = "running"
            self._pause_event.set()

    def cancel(self):
        self._reset_state()

    def _get_metadata_info(self, file_path):
        try:
            audio = MutagenFile(file_path, easy=True)
            if audio:
                title = audio.get("title", [""])[0]
                artist = audio.get("artist", [""])[0]
                combined = f"{artist} {title}".lower()
                combined = re.sub(r'[^a-z0-9\s]', ' ', combined)
                return {w for w in combined.split() if len(w) > 2}
        except Exception: pass
        name = os.path.splitext(os.path.basename(file_path).lower())[0]
        name = re.sub(r'[^a-z0-9\s]', ' ', name)
        return {word for word in name.split() if len(word) > 2}

    def _is_duplicate(self, new_file_path, word_threshold=4):
        new_words = self._get_metadata_info(new_file_path)
        for existing_file in self.existing_files_in_db:
            existing_words = self._get_metadata_info(existing_file)
            if len(new_words.intersection(existing_words)) >= word_threshold:
                print(f"[DUPLICATE] {new_file_path} == {existing_file}")
                return True
        return False

    def _extract_genres(self, file_path, topn=50):
        try:
            result = self.classifier(file_path)
            if not result:
                print(f"[WARNING] Classifier returned empty result for {file_path}.")
                return []
            return [r for r in sorted(result, key=lambda x: x['score'], reverse=True) if r['label'].lower() != "music"][:topn]
        except Exception as e:
            print(f"[ERROR] Classifier failed for {file_path}: {e}")
            return []

    def _extract_audio_features(self, file_path):
        try:
            y, sr = librosa.load(file_path, sr=8000, mono=True, duration=30.0, offset=20.0)
            if y.size == 0:
                print(f"[WARNING] Loaded empty audio signal from {file_path}. Skipping.")
                return None
        except Exception as e:
            print(f"[ERROR] librosa.load failed for {file_path}: {e}")
            return None

        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        features = {
            "bpm": float(librosa.beat.tempo(onset_envelope=onset_env, sr=sr)[0]),
            "key": keys[librosa.feature.chroma_stft(y=y, sr=sr).mean(axis=1).argmax()],
            "rms_energy": float(librosa.feature.rms(y=y).mean()),
            "spectral_centroid": float(librosa.feature.spectral_centroid(y=y, sr=sr).mean()),
            "spectral_bandwidth": float(librosa.feature.spectral_bandwidth(y=y, sr=sr).mean()),
            "spectral_rolloff": float(librosa.feature.spectral_rolloff(y=y, sr=sr).mean()),
            "zero_crossing_rate": float(librosa.feature.zero_crossing_rate(y).mean()),
            "mfcc1": float(mfcc[0].mean()), "mfcc2": float(mfcc[1].mean()), "mfcc3": float(mfcc[2].mean()),
        }

        for key, value in features.items():
            if isinstance(value, (int, float)) and not np.isfinite(value):
                print(f"[WARNING] Non-finite value for feature '{key}' in file {file_path}. Skipping file.")
                return None

        return features

    def _get_title_artist(self, file_path):
        try:
            audio = MutagenFile(file_path, easy=True)
            if audio: return audio.get("title", [""])[0].strip(), audio.get("artist", [""])[0].strip()
        except Exception: pass
        return os.path.splitext(os.path.basename(file_path))[0], ""
    
    def _extract_and_save_cover(self, file_path, track_id):
        try:
            os.makedirs(self.covers_folder, exist_ok=True)
            audio = MutagenFile(file_path)
            if not audio: return

            cover_data, ext = None, None
            if apic_tags := [tag for tag in audio.keys() if tag.startswith("APIC")]:
                apic = audio[apic_tags[0]]
                cover_data, ext = apic.data, apic.mime.split("/")[-1]
            elif hasattr(audio, "pictures") and audio.pictures:
                pic = audio.pictures[0]
                cover_data, ext = pic.data, pic.mime.split('/')[-1]
            
            if cover_data:
                ext = "jpg" if ext == "jpeg" else ext
                with open(os.path.join(self.covers_folder, f"{track_id}.{ext}"), "wb") as f:
                    f.write(cover_data)
        except Exception as e:
            print(f"[COVER ERROR] {file_path}: {e}")

    async def _save_to_db(self, file_path, feats, genres):
        await self._run_in_executor(self._blocking_save_to_db, file_path, feats, genres)

    def _blocking_save_to_db(self, file_path, feats, genres):
        with get_connection() as conn:
            with conn.cursor() as cur:
                title, artist = self._get_title_artist(file_path)
                primary_genre = genres[0]["label"] if genres else None
                relative_path = os.path.relpath(file_path, self.music_folder).replace('\\', '/')

                sql = """INSERT INTO features (file, title, artist, primary_genre, bpm, `key`, rms_energy,
                             spectral_centroid, spectral_bandwidth, spectral_rolloff, zero_crossing_rate,
                             mfcc1, mfcc2, mfcc3)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           ON DUPLICATE KEY UPDATE title=VALUES(title), artist=VALUES(artist), 
                             primary_genre=VALUES(primary_genre), bpm=VALUES(bpm), `key`=VALUES(`key`),
                             rms_energy=VALUES(rms_energy), spectral_centroid=VALUES(spectral_centroid),
                             spectral_bandwidth=VALUES(spectral_bandwidth), spectral_rolloff=VALUES(spectral_rolloff),
                             zero_crossing_rate=VALUES(zero_crossing_rate), mfcc1=VALUES(mfcc1),
                             mfcc2=VALUES(mfcc2), mfcc3=VALUES(mfcc3)"""
                params = (relative_path, title, artist, primary_genre, feats["bpm"], feats["key"], feats["rms_energy"],
                          feats["spectral_centroid"], feats["spectral_bandwidth"], feats["spectral_rolloff"],
                          feats["zero_crossing_rate"], feats["mfcc1"], feats["mfcc2"], feats["mfcc3"])
                cur.execute(sql, params)


                cur.execute("SELECT id FROM features WHERE file=%s", (relative_path,))
                if not (row := cur.fetchone()):
                    print(f"[DB ERROR] Track not found after insert: {relative_path}")
                    return

                track_id = row["id"]
                self._extract_and_save_cover(file_path, track_id)

                cur.execute("DELETE FROM genres WHERE track_id=%s", (track_id,))
                if genres:
                    genre_data = [(track_id, g["label"], g["score"]) for g in genres]
                    cur.executemany("INSERT INTO genres (track_id, label, score) VALUES (%s,%s,%s)", genre_data)


    @staticmethod
    def clear_db():
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
                for table in ["playlist_tracks", "playlists", "listening_history", "genres", "features"]:
                    cursor.execute(f"TRUNCATE TABLE {table};")
                cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
            conn.commit()
        
        covers_dir = os.path.join(os.path.dirname(__file__), 'covers')
        if os.path.isdir(covers_dir):
            for f in os.listdir(covers_dir):
                try:
                    os.remove(os.path.join(covers_dir, f))
                except OSError as e:
                    print(f"Error removing file {f}: {e}")