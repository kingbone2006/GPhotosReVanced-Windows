"""Database module for Google Photos ReVanced Windows edition.
Tracks upload history, file hashes, deduplication, and storage statistics.
"""

import os
import sqlite3
import hashlib
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class UploadDatabase:
    def __init__(self, db_path: Optional[Path] = None):
        self._lock = threading.Lock()
        if db_path is None:
            app_data = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "GPhotosReVanced"
            app_data.mkdir(parents=True, exist_ok=True)
            self.db_path = app_data / "history.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._fast_cache: Optional[Dict[Tuple[str, int, str], Dict[str, Any]]] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS uploads (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        local_path TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        sha1_hash TEXT NOT NULL,
                        file_size INTEGER NOT NULL,
                        media_key TEXT,
                        status TEXT NOT NULL,
                        error_message TEXT,
                        account_email TEXT,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                # Check if albums table exists and its schema
                pragma = conn.execute("PRAGMA table_info(albums)").fetchall()
                col_names = [col[1] for col in pragma] if pragma else []
                if pragma and "account_email" not in col_names:
                    conn.execute("ALTER TABLE albums RENAME TO albums_old;")
                    conn.execute("""
                        CREATE TABLE albums (
                            account_email TEXT NOT NULL DEFAULT '',
                            album_name TEXT NOT NULL,
                            album_media_key TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (account_email, album_name)
                        )
                    """)
                    conn.execute("""
                        INSERT OR IGNORE INTO albums (account_email, album_name, album_media_key, created_at)
                        SELECT 'haidkgcf@gmail.com', album_name, album_media_key, created_at FROM albums_old;
                    """)
                    conn.execute("DROP TABLE albums_old;")
                elif not pragma:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS albums (
                            account_email TEXT NOT NULL DEFAULT '',
                            album_name TEXT NOT NULL,
                            album_media_key TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            PRIMARY KEY (account_email, album_name)
                        )
                    """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS album_items (
                        account_email TEXT NOT NULL DEFAULT '',
                        album_name TEXT NOT NULL,
                        media_key TEXT NOT NULL,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (account_email, album_name, media_key)
                    )
                """)

                uploads_pragma = conn.execute("PRAGMA table_info(uploads)").fetchall()
                uploads_cols = [col[1] for col in uploads_pragma] if uploads_pragma else []
                if uploads_pragma and "mtime" not in uploads_cols:
                    conn.execute("ALTER TABLE uploads ADD COLUMN mtime REAL DEFAULT 0;")

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sha1 ON uploads(sha1_hash)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_path ON uploads(local_path)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_uploads_fast ON uploads(local_path, file_size, status, account_email)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_albums_account ON albums(account_email, album_name)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_album_items ON album_items(account_email, album_name)
                """)
                conn.commit()

    def get_album_key(self, album_name: str, account_email: str = "") -> Optional[str]:
        """Get stored Google Photos album key for an album name and account."""
        with self._lock:
            with self._get_connection() as conn:
                if account_email:
                    cur = conn.execute(
                        "SELECT album_media_key FROM albums WHERE album_name = ? AND account_email = ? LIMIT 1",
                        (album_name, account_email)
                    )
                    row = cur.fetchone()
                    return row["album_media_key"] if row else None
                else:
                    cur = conn.execute("SELECT album_media_key FROM albums WHERE album_name = ? LIMIT 1", (album_name,))
                    row = cur.fetchone()
                    return row["album_media_key"] if row else None

    def save_album_key(self, album_name: str, album_media_key: str, account_email: str = "") -> None:
        """Store Google Photos album key for an album name and account."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO albums (account_email, album_name, album_media_key) VALUES (?, ?, ?)",
                    (account_email, album_name, album_media_key)
                )
                conn.commit()

    def delete_album_key(self, album_name: str, account_email: str = "") -> None:
        """Remove Google Photos album key for an album name (used when album is deleted or invalid)."""
        with self._lock:
            with self._get_connection() as conn:
                if account_email:
                    conn.execute(
                        "DELETE FROM albums WHERE album_name = ? AND account_email = ?",
                        (album_name, account_email)
                    )
                else:
                    conn.execute("DELETE FROM albums WHERE album_name = ?", (album_name,))
                conn.commit()

    def is_in_album(self, album_name: str, media_key: str, account_email: str = "") -> bool:
        """Check if a media key is already recorded in the album."""
        with self._lock:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT 1 FROM album_items WHERE album_name = ? AND media_key = ? AND account_email = ? LIMIT 1",
                    (album_name, media_key, account_email)
                )
                return cur.fetchone() is not None

    def record_album_items(self, album_name: str, media_keys: List[str], account_email: str = "") -> None:
        """Record media keys as successfully added to an album."""
        if not media_keys:
            return
        with self._lock:
            with self._get_connection() as conn:
                conn.executemany(
                    "INSERT OR IGNORE INTO album_items (account_email, album_name, media_key) VALUES (?, ?, ?)",
                    [(account_email, album_name, mk) for mk in media_keys]
                )
                conn.commit()

    def clear_album_items(self, album_name: str, account_email: str = "") -> None:
        """Clear recorded items for an album (used when re-creating album)."""
        with self._lock:
            with self._get_connection() as conn:
                if account_email:
                    conn.execute(
                        "DELETE FROM album_items WHERE album_name = ? AND account_email = ?",
                        (album_name, account_email)
                    )
                else:
                    conn.execute("DELETE FROM album_items WHERE album_name = ?", (album_name,))
                conn.commit()

    @staticmethod
    def calculate_sha1(file_path: Path) -> str:
        """Calculate SHA-1 hash of a file efficiently using 4MB buffered chunks."""
        hasher = hashlib.sha1()
        try:
            with open(file_path, "rb", buffering=4 * 1024 * 1024) as f:
                while chunk := f.read(4 * 1024 * 1024):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            # Fallback
            with open(file_path, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    hasher.update(chunk)
            return hasher.hexdigest()

    def load_fast_cache(self, account_email: str = "") -> None:
        """Pre-load all successful uploads into an in-memory dictionary for microsecond lookups."""
        with self._lock:
            self._fast_cache = {}
            with self._get_connection() as conn:
                query = "SELECT local_path, file_size, sha1_hash, media_key, mtime FROM uploads WHERE status = 'success'"
                params = ()
                if account_email:
                    query += " AND account_email = ?"
                    params = (account_email,)
                cur = conn.execute(query, params)
                for row in cur.fetchall():
                    key = (row["local_path"], row["file_size"], account_email)
                    self._fast_cache[key] = {
                        "sha1_hash": row["sha1_hash"],
                        "media_key": row["media_key"],
                        "mtime": row["mtime"] or 0.0
                    }

    def fast_check_file(
        self,
        local_path: str,
        file_size: int,
        mtime: Optional[float] = None,
        account_email: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Ultra-fast check if file (by path + size + optional mtime) was already uploaded successfully.
        Runs in ~0.001ms using memory cache or fast SQLite index.
        """
        path_str = str(local_path)
        with self._lock:
            # 1. Check in-memory cache
            if self._fast_cache is not None:
                cache_key = (path_str, file_size, account_email)
                cached = self._fast_cache.get(cache_key)
                if cached is not None:
                    if mtime is not None and cached.get("mtime", 0) > 0:
                        if abs(cached["mtime"] - mtime) < 1.5:
                            return cached
                    else:
                        return cached

            # 2. Query indexed database
            with self._get_connection() as conn:
                if account_email:
                    cur = conn.execute(
                        """
                        SELECT sha1_hash, media_key, mtime 
                        FROM uploads 
                        WHERE local_path = ? AND file_size = ? AND status = 'success' AND account_email = ?
                        ORDER BY id DESC LIMIT 1
                        """,
                        (path_str, file_size, account_email)
                    )
                else:
                    cur = conn.execute(
                        """
                        SELECT sha1_hash, media_key, mtime 
                        FROM uploads 
                        WHERE local_path = ? AND file_size = ? AND status = 'success'
                        ORDER BY id DESC LIMIT 1
                        """,
                        (path_str, file_size)
                    )
                row = cur.fetchone()
                if row and row["media_key"]:
                    res = {
                        "sha1_hash": row["sha1_hash"],
                        "media_key": row["media_key"],
                        "mtime": row["mtime"] or 0.0
                    }
                    if self._fast_cache is not None:
                        self._fast_cache[(path_str, file_size, account_email)] = res
                    return res
                return None

    def is_file_uploaded(self, sha1_hash: str) -> bool:
        """Check if file hash was previously recorded as successfully uploaded."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM uploads WHERE sha1_hash = ? AND status = 'success' LIMIT 1",
                (sha1_hash,)
            )
            return cursor.fetchone() is not None

    def remove_upload_by_hash(self, sha1_hash: str) -> None:
        """Remove upload record if file was deleted on Google Photos."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM uploads WHERE sha1_hash = ?", (sha1_hash,))
                conn.commit()
            if self._fast_cache is not None:
                keys_to_remove = [k for k, v in self._fast_cache.items() if v.get("sha1_hash") == sha1_hash]
                for k in keys_to_remove:
                    self._fast_cache.pop(k, None)

    def record_upload(
        self,
        local_path: str,
        filename: str,
        sha1_hash: str,
        file_size: int,
        media_key: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        account_email: Optional[str] = None,
        mtime: Optional[float] = None
    ) -> None:
        """Insert or update upload record."""
        path_str = str(local_path)
        if mtime is None:
            try:
                mtime = Path(path_str).stat().st_mtime
            except Exception:
                mtime = 0.0

        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM uploads WHERE sha1_hash = ?", (sha1_hash,))
                conn.execute(
                    """
                    INSERT INTO uploads (local_path, filename, sha1_hash, file_size, media_key, status, error_message, account_email, mtime, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        path_str,
                        filename,
                        sha1_hash,
                        file_size,
                        media_key,
                        status,
                        error_message,
                        account_email,
                        mtime,
                        datetime.now().isoformat()
                    )
                )
                conn.commit()

            # Update in-memory fast cache
            if self._fast_cache is not None and status == "success" and media_key:
                self._fast_cache[(path_str, file_size, account_email or "")] = {
                    "sha1_hash": sha1_hash,
                    "media_key": media_key,
                    "mtime": mtime or 0.0
                }

    def get_recent_uploads(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent upload entries."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, local_path, filename, sha1_hash, file_size, media_key, status, error_message, account_email, uploaded_at
                FROM uploads
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self, account_email: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics: total files, total bytes uploaded, GB saved.
        If account_email is provided, returns statistics specifically for that account.
        """
        with self._get_connection() as conn:
            if account_email:
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(id) AS total_count,
                        COALESCE(SUM(file_size), 0) AS total_bytes
                    FROM uploads
                    WHERE status = 'success' AND account_email = ?
                    """,
                    (account_email,)
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT 
                        COUNT(id) AS total_count,
                        COALESCE(SUM(file_size), 0) AS total_bytes
                    FROM uploads
                    WHERE status = 'success'
                    """
                )
            row = cursor.fetchone()
            total_count = row["total_count"] if row else 0
            total_bytes = row["total_bytes"] if row else 0
            total_gb = round(total_bytes / (1024 ** 3), 2)
            total_mb = round(total_bytes / (1024 ** 2), 2)

            return {
                "total_files": total_count,
                "total_bytes": total_bytes,
                "total_mb": total_mb,
                "total_gb": total_gb,
            }

    def clear_history(self, account_email: Optional[str] = None) -> None:
        """Clear upload records and reset statistics to zero.
        If account_email is provided, only clears records for that account.
        """
        with self._lock:
            with self._get_connection() as conn:
                if account_email:
                    conn.execute("DELETE FROM uploads WHERE account_email = ?", (account_email,))
                else:
                    conn.execute("DELETE FROM uploads")
                    try:
                        conn.execute("DELETE FROM sqlite_sequence WHERE name = 'uploads'")
                    except Exception:
                        pass
                conn.commit()
            self._fast_cache = None

    def get_account_unbackup_info(self, account_email: str) -> Dict[str, Any]:
        """Get all sha1 hashes, count, total size, and album count for unbackup."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT sha1_hash, file_size
                FROM uploads
                WHERE status = 'success' AND (account_email = ? OR account_email = '' OR account_email IS NULL)
                """,
                (account_email,)
            )
            rows = cursor.fetchall()
            hashes = list(dict.fromkeys([r["sha1_hash"] for r in rows if r["sha1_hash"]]))
            total_size = sum(r["file_size"] for r in rows)

            album_cursor = conn.execute(
                "SELECT COUNT(DISTINCT album_name) as album_count FROM albums WHERE account_email = ? OR account_email = '' OR account_email IS NULL",
                (account_email,)
            )
            album_row = album_cursor.fetchone()
            album_count = album_row["album_count"] if album_row else 0

            return {
                "hashes": hashes,
                "total_files": len(hashes),
                "total_bytes": total_size,
                "total_gb": round(total_size / (1024 ** 3), 2),
                "album_count": album_count,
            }

    def clear_account_data(self, account_email: str) -> None:
        """Clear all uploads, albums, and album_items associated with account_email."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM uploads WHERE account_email = ? OR account_email = '' OR account_email IS NULL", (account_email,))
                conn.execute("DELETE FROM albums WHERE account_email = ? OR account_email = '' OR account_email IS NULL", (account_email,))
                conn.execute("DELETE FROM album_items WHERE account_email = ? OR account_email = '' OR account_email IS NULL", (account_email,))
                try:
                    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('uploads', 'albums', 'album_items')")
                except Exception:
                    pass
                conn.commit()
            self._fast_cache = None

    def get_all_albums(self, account_email: str = "") -> List[Dict[str, Any]]:
        """
        Get all albums with their photo count and cover thumbnail info.
        Combines registered albums and folder-based albums from uploads.
        """
        albums_dict = {}
        with self._get_connection() as conn:
            # 1. Registered albums in albums table
            q_alb = "SELECT album_name, album_media_key, created_at FROM albums WHERE (account_email = ? OR account_email = '' OR account_email IS NULL)"
            for row in conn.execute(q_alb, (account_email,)).fetchall():
                name = row["album_name"]
                albums_dict[name] = {
                    "album_name": name,
                    "album_media_key": row["album_media_key"],
                    "created_at": row["created_at"],
                    "photo_count": 0,
                    "cover_path": "",
                    "cover_media_key": "",
                }

            # 2. Add counts from album_items
            q_items = "SELECT album_name, COUNT(DISTINCT media_key) as cnt, MIN(media_key) as cover_key FROM album_items WHERE (account_email = ? OR account_email = '' OR account_email IS NULL) GROUP BY album_name"
            for row in conn.execute(q_items, (account_email,)).fetchall():
                name = row["album_name"]
                if name in albums_dict:
                    albums_dict[name]["photo_count"] = row["cnt"]
                    albums_dict[name]["cover_media_key"] = row["cover_key"]
                else:
                    albums_dict[name] = {
                        "album_name": name,
                        "album_media_key": "",
                        "created_at": "",
                        "photo_count": row["cnt"],
                        "cover_path": "",
                        "cover_media_key": row["cover_key"],
                    }

            # 3. Discover folder-based albums from uploads table
            q_uploads = "SELECT local_path, filename, media_key FROM uploads WHERE status = 'success' AND (account_email = ? OR account_email = '' OR account_email IS NULL)"
            for row in conn.execute(q_uploads, (account_email,)).fetchall():
                p_str = row["local_path"]
                if not p_str:
                    continue
                p = Path(p_str)
                parent_name = p.parent.name
                if not parent_name or parent_name in (".", "/", "\\"):
                    continue
                if parent_name not in albums_dict:
                    albums_dict[parent_name] = {
                        "album_name": parent_name,
                        "album_media_key": "",
                        "created_at": "",
                        "photo_count": 1,
                        "cover_path": p_str if p.exists() else "",
                        "cover_media_key": row["media_key"] or "",
                    }
                else:
                    if albums_dict[parent_name]["photo_count"] == 0:
                        albums_dict[parent_name]["photo_count"] += 1
                        if not albums_dict[parent_name]["cover_path"] and p.exists():
                            albums_dict[parent_name]["cover_path"] = p_str
                        if not albums_dict[parent_name]["cover_media_key"]:
                            albums_dict[parent_name]["cover_media_key"] = row["media_key"] or ""
                    elif not albums_dict[parent_name].get("album_media_key"):
                        albums_dict[parent_name]["photo_count"] += 1

        return sorted(list(albums_dict.values()), key=lambda x: x["album_name"].lower())

    def get_album_photos(self, album_name: str, account_email: str = "") -> List[Dict[str, Any]]:
        """
        Get all photos belonging to an album.
        Checks album_items first, with fallback to path-based matching in uploads.
        """
        photos = []
        with self._get_connection() as conn:
            # 1. Look in album_items joined with uploads
            q1 = """
            SELECT u.filename, u.local_path, u.media_key, u.file_size, u.uploaded_at
            FROM album_items ai
            JOIN uploads u ON ai.media_key = u.media_key
            WHERE ai.album_name = ? AND (ai.account_email = ? OR ai.account_email = '' OR ai.account_email IS NULL)
            """
            for row in conn.execute(q1, (album_name, account_email)).fetchall():
                photos.append({
                    "filename": row["filename"],
                    "local_path": row["local_path"],
                    "media_key": row["media_key"],
                    "file_size": row["file_size"],
                    "uploaded_at": row["uploaded_at"]
                })

            # 2. If empty, fallback to parent directory matching in uploads
            if not photos:
                q2 = """
                SELECT filename, local_path, media_key, file_size, uploaded_at
                FROM uploads
                WHERE status = 'success' 
                  AND (account_email = ? OR account_email = '' OR account_email IS NULL)
                """
                for row in conn.execute(q2, (account_email,)).fetchall():
                    p_str = row["local_path"]
                    if p_str and Path(p_str).parent.name == album_name:
                        photos.append({
                            "filename": row["filename"],
                            "local_path": row["local_path"],
                            "media_key": row["media_key"],
                            "file_size": row["file_size"],
                            "uploaded_at": row["uploaded_at"]
                        })

        return photos

