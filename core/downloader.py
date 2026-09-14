"""Album and Photo Downloader for Google Photos ReVanced.
Downloads albums into folders named after the album name on the local PC,
supporting multi-threaded downloads, bandwidth streaming, and local copy optimizations.
"""

import os
import re
import shutil
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import requests


def sanitize_folder_name(name: str) -> str:
    """Sanitize string to be a safe directory name on Windows and other OSes."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    return clean if clean else "Untitled_Album"


class AlbumDownloader:
    """
    Handles downloading selected albums to a destination directory.
    Each album is downloaded into a dedicated subfolder: `<dest_dir>/<album_name>/`.
    """
    def __init__(self, api=None, max_threads: int = 4):
        self.api = api
        self.max_threads = max_threads
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def download_albums(
        self,
        albums: List[Dict[str, Any]],
        destination_root: Path,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Download list of albums into destination_root.
        albums format: [
            {
                "album_name": "Cosplay 2026",
                "items": [
                    {"filename": "001.jpg", "media_key": "...", "local_path": "..."}
                ]
            }
        ]
        """
        self._is_cancelled = False
        destination_root = Path(destination_root)
        destination_root.mkdir(parents=True, exist_ok=True)

        total_albums = len(albums)
        total_files = sum(len(a.get("items", [])) for a in albums)
        completed_files = 0
        success_count = 0
        error_count = 0

        start_time = time.time()
        downloaded_bytes = 0

        def emit_progress(current_album: str, current_file: str, speed_str: str = ""):
            if progress_callback:
                pct = completed_files / total_files if total_files > 0 else 1.0
                progress_callback({
                    "type": "progress",
                    "current_album": current_album,
                    "current_file": current_file,
                    "completed_files": completed_files,
                    "total_files": total_files,
                    "percent": pct,
                    "speed": speed_str,
                    "total_albums": total_albums
                })

        for a_idx, album in enumerate(albums, 1):
            if self._is_cancelled:
                break

            album_name = album.get("album_name", f"Album_{a_idx}")
            safe_name = sanitize_folder_name(album_name)
            album_dir = destination_root / safe_name
            album_dir.mkdir(parents=True, exist_ok=True)

            items = album.get("items", [])
            for item in items:
                if self._is_cancelled:
                    break

                filename = item.get("filename") or "photo.jpg"
                dest_path = album_dir / filename
                local_source = item.get("local_path")
                media_key = item.get("media_key")

                # Handle duplicate filenames in same album
                if dest_path.exists():
                    counter = 1
                    stem = Path(filename).stem
                    suffix = Path(filename).suffix
                    while dest_path.exists():
                        dest_path = album_dir / f"{stem}_{counter}{suffix}"
                        counter += 1

                emit_progress(album_name, filename)

                # 1. Local copy optimization: if file already exists on machine and is readable
                copied_locally = False
                if local_source and Path(local_source).exists() and Path(local_source).is_file():
                    try:
                        shutil.copy2(local_source, dest_path)
                        copied_locally = True
                        success_count += 1
                        completed_files += 1
                        continue
                    except Exception:
                        copied_locally = False

                # 2. Download from Google Photos Cloud if local copy not available
                download_success = False
                if not copied_locally and media_key and self.api:
                    try:
                        download_url = self._get_download_url(media_key)
                        if download_url:
                            resp = requests.get(download_url, stream=True, timeout=30)
                            resp.raise_for_status()
                            with open(dest_path, "wb") as f:
                                for chunk in resp.iter_content(chunk_size=64 * 1024):
                                    if self._is_cancelled:
                                        break
                                    if chunk:
                                        f.write(chunk)
                                        downloaded_bytes += len(chunk)
                            if not self._is_cancelled:
                                download_success = True
                                success_count += 1
                    except Exception:
                        download_success = False

                if not copied_locally and not download_success:
                    error_count += 1

                completed_files += 1
                elapsed = time.time() - start_time
                speed_str = ""
                if elapsed > 0 and downloaded_bytes > 0:
                    mb_per_sec = (downloaded_bytes / (1024 * 1024)) / elapsed
                    speed_str = f"{mb_per_sec:.1f} MB/s"
                emit_progress(album_name, filename, speed_str)

        return {
            "success": not self._is_cancelled,
            "albums_count": total_albums,
            "files_count": success_count,
            "error_count": error_count,
            "destination": str(destination_root)
        }

    def _get_download_url(self, media_key: str) -> Optional[str]:
        """Fetch high-resolution download URL from Google Photos."""
        try:
            res = self.api.get_download_urls(media_key)
            # Try original URL first
            url = res.get("1", {}).get("5", {}).get("2", {}).get("6", None)
            if not url:
                # Fallback to edited or default
                url = res.get("1", {}).get("5", {}).get("2", {}).get("5", None)
            return url
        except Exception:
            return None
