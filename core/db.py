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

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sha1 ON uploads(sha1_hash)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_path ON uploads(local_path)
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
        """Calculate SHA-1 hash of a file efficiently in chunks."""
        hasher = hashlib.sha1()
        with open(file_path, "rb") as f:
            while chunk := f.read(1024 * 1024):  # 1MB chunk
                hasher.update(chunk)
        return hasher.hexdigest()

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

    def record_upload(
        self,
        local_path: str,
        filename: str,
        sha1_hash: str,
        file_size: int,
        media_key: Optional[str] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        account_email: Optional[str] = None
    ) -> None:
        """Insert or update upload record."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM uploads WHERE sha1_hash = ?", (sha1_hash,))
                conn.execute(
                    """
                    INSERT INTO uploads (local_path, filename, sha1_hash, file_size, media_key, status, error_message, account_email, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(local_path),
                        filename,
                        sha1_hash,
                        file_size,
                        media_key,
                        status,
                        error_message,
                        account_email,
                        datetime.now().isoformat()
                    )
                )
                conn.commit()

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

    def get_statistics(self) -> Dict[str, Any]:
        """Get summary statistics: total files, total bytes uploaded, GB saved."""
        with self._get_connection() as conn:
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

    def clear_history(self) -> None:
        """Clear all upload records and reset statistics to zero."""
        with self._lock:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM uploads")
                try:
                    conn.execute("DELETE FROM sqlite_sequence WHERE name = 'uploads'")
                except Exception:
                    pass
                conn.commit()
