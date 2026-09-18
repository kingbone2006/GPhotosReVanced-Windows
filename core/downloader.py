"""High-speed Multi-Threaded Album & Media Downloader for Google Photos ReVanced.
Downloads albums into dedicated folders named after the album name on the local PC,
supporting multi-threaded streaming, Google User Content endpoints, automatic filename
detection from Content-Disposition, and local copy optimizations.
"""

import os
import re
import shutil
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import logging

logger = logging.getLogger(__name__)

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".3gp", ".m4v", ".mts"}


def sanitize_folder_name(name: str) -> str:
    """Sanitize string to be a safe directory name on Windows and other OSes."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    return clean if clean else "Untitled_Album"


def sanitize_filename(name: str) -> str:
    """Sanitize string to be a safe filename."""
    clean = re.sub(r'[\\/*?:"<>|]', "_", name).strip()
    return clean if clean else "photo.jpg"


class AlbumDownloader:
    """
    Handles downloading selected albums to a destination directory.
    Each album is downloaded into a dedicated subfolder: `<dest_dir>/<album_name>/`.
    Uses multi-threaded streaming directly from Google User Content CDN.
    """
    def __init__(self, api=None, max_threads: int = 4):
        self.api = api
        self.max_threads = max(1, min(max_threads, 8))
        self._is_cancelled = False
        self._lock = threading.Lock()

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
        last_time = time.time()
        last_bytes = 0

        def emit_progress(current_album: str, current_file: str):
            if not progress_callback:
                return
            now = time.time()
            pct = completed_files / total_files if total_files > 0 else 1.0
            elapsed = now - start_time
            speed_str = ""
            if elapsed > 0.5 and downloaded_bytes > 0:
                mb_per_sec = (downloaded_bytes / (1024 * 1024)) / elapsed
                speed_str = f"{mb_per_sec:.1f} MB/s"

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

        bearer_token = getattr(self.api, "bearer_token", "") if self.api else ""
        user_agent = getattr(self.api, "user_agent", "Mozilla/5.0") if self.api else "Mozilla/5.0"

        headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip",
        }
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"

        for a_idx, album in enumerate(albums, 1):
            if self._is_cancelled:
                break

            album_name = album.get("album_name", f"Album_{a_idx}")
            safe_name = sanitize_folder_name(album_name)
            album_dir = destination_root / safe_name
            album_dir.mkdir(parents=True, exist_ok=True)

            items = album.get("items", [])
            if not items:
                continue

            def process_single_item(item_idx: int, item: dict) -> bool:
                nonlocal completed_files, success_count, error_count, downloaded_bytes
                if self._is_cancelled:
                    return False

                raw_filename = item.get("filename") or f"photo_{item_idx:04d}.jpg"
                filename = sanitize_filename(raw_filename)
                local_source = item.get("local_path")
                raw_mk = item.get("media_key")
                if isinstance(raw_mk, bytes):
                    media_key = raw_mk.decode("utf-8", errors="replace").strip()
                else:
                    media_key = str(raw_mk or "").strip()

                dest_path = album_dir / filename

                # 1. Local copy optimization: file already on disk and readable
                if local_source and Path(local_source).exists() and Path(local_source).is_file():
                    try:
                        # Avoid overwriting destination with identical source
                        if Path(local_source).resolve() != dest_path.resolve():
                            shutil.copy2(local_source, dest_path)
                        with self._lock:
                            success_count += 1
                            completed_files += 1
                            emit_progress(album_name, filename)
                        return True
                    except Exception as e:
                        logger.debug("Local copy failed for %s: %s", filename, e)

                # 2. Direct Google User Content CDN Streaming
                if media_key and self.api:
                    is_vid = Path(filename).suffix.lower() in VIDEO_EXTS
                    success, b_count, real_name = self._stream_download_item(
                        media_key=media_key,
                        dest_dir=album_dir,
                        suggested_filename=filename,
                        is_video=is_vid,
                        headers=headers
                    )
                    if success:
                        with self._lock:
                            success_count += 1
                            completed_files += 1
                            downloaded_bytes += b_count
                            emit_progress(album_name, real_name or filename)
                        return True

                with self._lock:
                    error_count += 1
                    completed_files += 1
                    emit_progress(album_name, filename)
                return False

            # Multi-threaded download workers
            with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
                futures = [
                    executor.submit(process_single_item, idx, itm)
                    for idx, itm in enumerate(items, 1)
                ]
                for fut in as_completed(futures):
                    if self._is_cancelled:
                        break
                    try:
                        fut.result()
                    except Exception as e:
                        logger.debug("Item worker exception: %s", e)

        return {
            "success": not self._is_cancelled,
            "albums_count": total_albums,
            "files_count": success_count,
            "error_count": error_count,
            "destination": str(destination_root)
        }

    def _stream_download_item(
        self,
        media_key: str,
        dest_dir: Path,
        suggested_filename: str,
        is_video: bool,
        headers: dict
    ) -> tuple[bool, int, str]:
        """Stream download media item from Google User Content endpoints."""
        url_candidates = []
        if is_video:
            url_candidates.extend([
                f"https://lh3.googleusercontent.com/p/{media_key}=dv",
                f"https://ap2.googleusercontent.com/gpa/{media_key}=dv",
                f"https://lh3.googleusercontent.com/p/{media_key}=d",
                f"https://ap2.googleusercontent.com/gpa/{media_key}=d",
            ])
        else:
            url_candidates.extend([
                f"https://lh3.googleusercontent.com/p/{media_key}=d",
                f"https://ap2.googleusercontent.com/gpa/{media_key}=d",
                f"https://lh3.googleusercontent.com/p/{media_key}=dv",
            ])

        for url in url_candidates:
            if self._is_cancelled:
                return False, 0, suggested_filename

            try:
                resp = requests.get(url, headers=headers, stream=True, timeout=35)
                if resp.status_code == 200:
                    effective_name = suggested_filename
                    content_disp = resp.headers.get("Content-Disposition", "")
                    if "filename=" in content_disp:
                        m = re.search(r'filename=["\']?([^"\';]+)["\']?', content_disp)
                        if m and m.group(1):
                            effective_name = sanitize_filename(m.group(1).strip())
                    else:
                        ctype = resp.headers.get("Content-Type", "")
                        if "video" in ctype and Path(effective_name).suffix.lower() not in VIDEO_EXTS:
                            effective_name = str(Path(effective_name).with_suffix(".mp4"))

                    dest_path = dest_dir / effective_name
                    # If target already exists, append counter
                    if dest_path.exists():
                        stem = dest_path.stem
                        suffix = dest_path.suffix
                        counter = 1
                        while dest_path.exists():
                            dest_path = dest_dir / f"{stem}_{counter}{suffix}"
                            counter += 1

                    part_path = dest_path.with_suffix(dest_path.suffix + ".part")
                    bytes_received = 0

                    with open(part_path, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=512 * 1024):
                            if self._is_cancelled:
                                break
                            if chunk:
                                f.write(chunk)
                                bytes_received += len(chunk)

                    if self._is_cancelled:
                        if part_path.exists():
                            try:
                                part_path.unlink()
                            except Exception:
                                pass
                        return False, 0, effective_name

                    if bytes_received > 0:
                        if part_path.exists():
                            part_path.replace(dest_path)
                        return True, bytes_received, dest_path.name
                    else:
                        if part_path.exists():
                            part_path.unlink()
            except Exception as e:
                logger.debug("Failed downloading candidate %s: %s", url, e)
                continue

        return False, 0, suggested_filename
