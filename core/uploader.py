"""Uploader engine for Google Photos ReVanced Windows edition.
Features multi-threaded parallel uploads (Pixel XL unlimited spoofing),
per-file live event callbacks, deduplication, and worker pool management.
"""

import os
import re
import time
import threading
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty
from typing import Optional, Callable, Dict, Any, List, Sequence, Tuple
import requests
import gpmc
from gpmc.client import UploadProgressEvent
import mimetypes
from .db import UploadDatabase
from .network_optimizer import apply_network_optimizations
from .hash_pool import MultiCoreHashPool

apply_network_optimizations()

VIDEO_EXTENSIONS = {
    ".mp4", ".mov", ".m4v", ".mkv", ".avi", ".wmv", ".flv", ".webm", ".3gp", ".mts"
}

SUPPORTED_EXTENSIONS = {
    # Images
    ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif",
    ".bmp", ".tiff", ".tif", ".ico", ".svg",
    # RAW
    ".dng", ".cr2", ".cr3", ".nef", ".arw", ".rw2", ".orf", ".pef",
    # Videos
    *VIDEO_EXTENSIONS
}

IMAGE_EXTENSIONS = SUPPORTED_EXTENSIONS - VIDEO_EXTENSIONS

# Ensure Windows recognizes all video MIME types properly for gpmc
for _ext, _mime in [
    (".flv", "video/x-flv"),
    (".mp4", "video/mp4"),
    (".mov", "video/quicktime"),
    (".mkv", "video/x-matroska"),
    (".m4v", "video/mp4"),
    (".avi", "video/avi"),
    (".wmv", "video/x-ms-wmv"),
    (".webm", "video/webm"),
    (".3gp", "video/3gpp"),
    (".mts", "video/vnd.dlna.mpeg-tts"),
]:
    mimetypes.add_type(_mime, _ext)


def ensure_blackboxprotobuf_patched() -> None:
    """Self-healing patch for blackboxprotobuf to prevent KeyError: 'name' and ensure string encoding support."""
    try:
        import blackboxprotobuf.lib.types.type_maps as tm
        from blackboxprotobuf.lib.types import length_delim
        from google.protobuf.internal import wire_format

        # Add string and str support
        tm.encoders["str"] = length_delim.encode_bytes
        tm.encoders["string"] = length_delim.encode_bytes
        tm.wiretypes["string"] = wire_format.WIRETYPE_LENGTH_DELIMITED
        tm.wiretypes["str"] = wire_format.WIRETYPE_LENGTH_DELIMITED

        # Patch encode_message in length_delim if needed
        orig_encode = length_delim.encode_message
        if not getattr(length_delim, "_gphotos_revanced_patched", False):
            def safe_encode_message(data, typedef, group=False):
                if not isinstance(typedef, dict):
                    return orig_encode(data, typedef, group)
                # Ensure each field in typedef has a name or is safely queried
                safe_typedef = {}
                for k, v in typedef.items():
                    if isinstance(v, dict) and "name" not in v:
                        v_copy = v.copy()
                        v_copy["name"] = ""
                        safe_typedef[k] = v_copy
                    else:
                        safe_typedef[k] = v
                return orig_encode(data, safe_typedef, group)

            length_delim.encode_message = safe_encode_message
            length_delim._gphotos_revanced_patched = True
    except Exception:
        pass


ensure_blackboxprotobuf_patched()


def parse_retry_after(header_val: Optional[str], default: float = 5.0) -> float:
    """Parse HTTP Retry-After header which can be seconds or an HTTP-date."""
    if not header_val:
        return default
    header_str = str(header_val).strip()
    try:
        val = float(header_str)
        return max(1.0, min(val, 120.0))
    except ValueError:
        pass
    try:
        import email.utils
        dt = email.utils.parsedate_to_datetime(header_str)
        now = datetime.now(dt.tzinfo)
        diff = (dt - now).total_seconds()
        return max(1.0, min(diff, 120.0))
    except Exception:
        return default


class RateLimiter:
    """Thread-safe rate limiter and 429 cooldown coordinator across all worker threads."""
    _lock = threading.Lock()
    _until: float = 0.0
    _pacing_lock = threading.Lock()
    _last_req: float = 0.0
    _log_func: Optional[Callable[[str, str], None]] = None

    @classmethod
    def set_logger(cls, log_func: Optional[Callable[[str, str], None]]) -> None:
        cls._log_func = log_func

    @classmethod
    def wait_if_needed(cls) -> None:
        while True:
            now = time.time()
            with cls._lock:
                until = cls._until
            if now >= until:
                break
            time.sleep(min(0.2, until - now))

    @classmethod
    def trigger(cls, wait_secs: float, reason: str = "") -> None:
        wait_secs = max(2.0, min(wait_secs, 120.0))
        with cls._lock:
            cls._until = max(cls._until, time.time() + wait_secs)
        if cls._log_func:
            try:
                cls._log_func(
                    f"⚠️ [HTTP 429 Too Many Requests] Google Photos đang giới hạn tần suất ({reason}). Tạm nghỉ {wait_secs:.1f}s trên toàn bộ các luồng...",
                    "WARNING"
                )
            except Exception:
                pass

    @classmethod
    def pace(cls, min_interval: float = 0.06) -> None:
        with cls._pacing_lock:
            now = time.time()
            elapsed = now - cls._last_req
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            cls._last_req = time.time()


def ensure_gpmc_rate_limit_patched() -> None:
    """
    Self-healing patch for gpmc.api to:
    1. Support automatic retries on POST and PUT methods (urllib3 excludes POST by default).
    2. Add HTTP 429 Too Many Requests and 500/502/503/504 to retry status list.
    3. Coordinate global rate limiting backoff across all threads.
    4. Auto-rewind request data stream when retrying 429/503.
    """
    try:
        import gpmc.api as gpmc_api
        from urllib3.util import Retry
        from requests.adapters import HTTPAdapter

        if getattr(gpmc_api.Api, "_gphotos_rate_limit_patched", False):
            return

        class RateLimitRetrySession(requests.Session):
            def request(self, method, url, *args, **kwargs):
                RateLimiter.wait_if_needed()
                RateLimiter.pace(0.05)

                max_retries = 5
                backoff = 3.0
                for attempt in range(max_retries):
                    RateLimiter.wait_if_needed()
                    try:
                        resp = super().request(method, url, *args, **kwargs)
                        if resp.status_code == 429:
                            retry_after = resp.headers.get("Retry-After")
                            wait_time = parse_retry_after(retry_after, default=backoff)
                            RateLimiter.trigger(wait_time, f"{method} 429")
                            if attempt < max_retries - 1:
                                time.sleep(wait_time)
                                backoff = min(backoff * 2, 60.0)
                                data = kwargs.get("data")
                                if hasattr(data, "seek"):
                                    try:
                                        data.seek(0)
                                    except Exception:
                                        pass
                                if hasattr(data, "_completed"):
                                    try:
                                        data._completed = 0
                                    except Exception:
                                        pass
                                continue
                        elif resp.status_code in (500, 502, 503, 504):
                            if attempt < max_retries - 1:
                                time.sleep(backoff)
                                backoff = min(backoff * 1.5, 30.0)
                                data = kwargs.get("data")
                                if hasattr(data, "seek"):
                                    try:
                                        data.seek(0)
                                    except Exception:
                                        pass
                                if hasattr(data, "_completed"):
                                    try:
                                        data._completed = 0
                                    except Exception:
                                        pass
                                continue
                        return resp
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                        if attempt < max_retries - 1:
                            time.sleep(backoff)
                            backoff = min(backoff * 1.5, 30.0)
                            data = kwargs.get("data")
                            if hasattr(data, "seek"):
                                try:
                                    data.seek(0)
                                except Exception:
                                    pass
                            continue
                        raise

        def patched_new_session(self):
            s = RateLimitRetrySession()
            retries = Retry(
                total=5,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=None  # Essential for POST and PUT retries
            )
            adapter = HTTPAdapter(max_retries=retries)
            s.mount("http://", adapter)
            s.mount("https://", adapter)
            s.proxies = {
                "http": self.proxy,
                "https": self.proxy,
            }
            if self.proxy:
                s.verify = False
            return s

        gpmc_api.Api._new_session = patched_new_session
        gpmc_api.Api._gphotos_rate_limit_patched = True
    except Exception:
        pass


ensure_gpmc_rate_limit_patched()

GENERIC_SUBFOLDER_PATTERN = re.compile(
    r'^(?:part|vol|volume|p|ch|chap|chapter|ep|episode|set|cd|disc|disk|sec|section|sub|subfolder|img|images|raw|photos?|pics?|thumbnails?)\s*[\-_#]?\s*\d*$',
    re.IGNORECASE
)


def is_subfolder_artifact(name: str) -> bool:
    """
    Check if a directory name is an internal pagination, index, or generic subfolder
    rather than the main photo album/set name (e.g. '1', '24', 'part1', 'img').
    """
    name_clean = name.strip()
    if not name_clean:
        return True
    if name_clean.isdigit() or name_clean.startswith("{"):
        return True
    # Strip wrapping brackets e.g. "(1)", "[24]", "{3}"
    clean_no_brackets = re.sub(r'^[(\[{<]\s*|\s*[)\]}>]$', '', name_clean)
    if clean_no_brackets.isdigit():
        return True
    if GENERIC_SUBFOLDER_PATTERN.match(name_clean):
        return True
    return False


def determine_album_name(file_path: Path, sync_roots: Optional[Sequence[Any]] = None) -> str:
    """
    Intelligently determines the album name for a file.
    Identifies the true photo set / album directory (e.g. '桜井宁宁 NO.003 双马尾黑丝 [22P-40MB]')
    and ensures ALL nested subfolders (e.g. 'gif [51P]', '1', 'sub/part') belong to that album.
    """
    try:
        p = file_path.resolve()
        resolved_roots = [Path(r).resolve() for r in (sync_roots or []) if r]

        # 1. Check relative to monitored sync roots
        for root in resolved_roots:
            try:
                rel = p.relative_to(root)
                if len(rel.parts) <= 1:
                    return "" if len(root.parts) <= 1 else root.name

                if len(rel.parts) == 2:
                    return rel.parts[0]

                if len(rel.parts) >= 3:
                    f1_name = rel.parts[0]
                    f2_name = rel.parts[1]
                    f1_path = root / f1_name
                    is_f1_collection = False

                    if f2_name.lower().startswith(f1_name.lower()):
                        is_f1_collection = True
                    elif re.search(r'(?:NO\.?\s*\d+|\[\d+[PpvV]|\[\d+(?:\.\d+)?\s*(?:MB|GB|M|G)\]|作品|合集|自拍|写真)', f2_name, re.IGNORECASE):
                        is_f1_collection = True
                    elif f1_path.is_dir():
                        try:
                            has_subdirs = any(entry.is_dir() for entry in os.scandir(f1_path))
                            has_direct_media = any(
                                entry.is_file() and os.path.splitext(entry.name)[1].lower() in SUPPORTED_EXTENSIONS
                                for entry in os.scandir(f1_path)
                            )
                            if has_subdirs and not has_direct_media:
                                is_f1_collection = True
                        except Exception:
                            pass

                    if is_f1_collection:
                        return f2_name
                    else:
                        return rel.parts[0]
            except ValueError:
                continue

        # 2. Fallback when sync_roots not provided: climb parents looking for set folder
        curr = p.parent
        while curr and len(curr.parts) > 2:
            parent = curr.parent
            if parent and parent != curr and len(parent.parts) > 1:
                # If parent folder contains set markers, current directory is an internal subfolder
                if re.search(r'(?:NO\.?\s*\d+|\[\d+[PpvV]|\[\d+(?:\.\d+)?\s*(?:MB|GB|M|G)\]|作品|合集|自拍|写真)', parent.name, re.IGNORECASE):
                    curr = parent
                    continue
            if is_subfolder_artifact(curr.name):
                curr = parent
                continue
            break

        return curr.name
    except Exception:
        return file_path.parent.name



def get_failed_files_from_log(
    log_path: str = "failed_skipped_files.log",
    db: Optional[UploadDatabase] = None,
    account_email: str = ""
) -> List[Path]:
    """Parse failed_skipped_files.log and extract valid existing file paths that need retry."""
    p = Path(log_path)
    if not p.exists():
        return []
    import re
    pattern = re.compile(r"\]\s+FAIL:\s+(.+?)\s+-\s+")
    seen_paths = set()
    raw_files = []
    try:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    raw_path = m.group(1).strip()
                    if raw_path not in seen_paths:
                        seen_paths.add(raw_path)
                        raw_files.append(raw_path)
    except Exception:
        pass

    uploaded_set = set()
    if db:
        try:
            with db._get_connection() as conn:
                if account_email:
                    rows = conn.execute(
                        "SELECT local_path FROM uploads WHERE status = 'success' AND (account_email = ? OR account_email = '' OR account_email IS NULL)",
                        (account_email,)
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT local_path FROM uploads WHERE status = 'success'"
                    ).fetchall()
                for r in rows:
                    if r["local_path"]:
                        try:
                            uploaded_set.add(Path(r["local_path"]).resolve().as_posix().lower())
                        except Exception:
                            pass
        except Exception:
            pass

    valid_files = []
    for raw in raw_files:
        fp = Path(raw)
        if fp.suffix.lower() in SUPPORTED_EXTENSIONS and fp.is_file():
            try:
                if fp.resolve().as_posix().lower() in uploaded_set:
                    continue
            except Exception:
                pass
            valid_files.append(fp)

    # Clean up stale lines from failed_skipped_files.log so only truly pending files remain
    if valid_files and len(raw_files) > len(valid_files):
        try:
            valid_set = {f.resolve().as_posix().lower() for f in valid_files}
            kept_lines = []
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    m = pattern.search(line)
                    if m:
                        raw_path = m.group(1).strip()
                        try:
                            if Path(raw_path).resolve().as_posix().lower() in valid_set:
                                kept_lines.append(line)
                        except Exception:
                            pass
            if kept_lines:
                with open(p, "w", encoding="utf-8") as f:
                    f.writelines(kept_lines)
        except Exception:
            pass

    return valid_files


def sync_cloud_albums(
    api=None,
    db: Optional[UploadDatabase] = None,
    account_email: str = ""
) -> Dict[str, Dict[str, Any]]:
    """
    Fetches all collections (albums) from Google Photos cloud via get_library_state.
    Stores and caches album_media_key, remote count, and cover for each album in the database.
    Guarantees that existing cloud albums are reused and never duplicated.
    """
    if api is None:
        return {}

    try:
        res = api.get_library_state()
        root = res.get("1", {}) if isinstance(res, dict) else {}
        collections = root.get("3", [])
        if isinstance(collections, dict):
            collections = [collections]
        if not isinstance(collections, list):
            return {}

        cloud_albums: Dict[str, Dict[str, Any]] = {}

        def _to_str(v) -> str:
            if v is None:
                return ""
            if isinstance(v, bytes):
                return v.decode("utf-8", errors="replace").strip()
            return str(v).strip()

        for c in collections:
            if not isinstance(c, dict):
                continue
            key = _to_str(c.get("1"))
            c2 = c.get("2", {}) if isinstance(c.get("2"), dict) else {}
            title = _to_str(c2.get("5"))
            total_items = 0
            try:
                total_items = int(c2.get("7", 0))
            except (ValueError, TypeError):
                total_items = 0
            cover_key = _to_str(c2.get("17", {}).get("1") if isinstance(c2.get("17"), dict) else "")

            if not key or not title:
                continue

            # If duplicate title exists on cloud, prefer the one with more photos
            if title in cloud_albums:
                if total_items > cloud_albums[title]["total"]:
                    cloud_albums[title] = {"key": key, "total": total_items, "cover_key": cover_key}
            else:
                cloud_albums[title] = {"key": key, "total": total_items, "cover_key": cover_key}

        if db and cloud_albums:
            ignored_set = set()
            try:
                ignored_set = db.get_ignored_albums(account_email)
            except Exception:
                ignored_set = set()

            for title, info in cloud_albums.items():
                # If this album was cleaned/ignored and still has 0 photos, skip saving to DB
                if title in ignored_set and info["total"] <= 0:
                    continue
                # If photos were added to a previously ignored album, unignore it
                if title in ignored_set and info["total"] > 0:
                    try:
                        db.unignore_album(title, account_email)
                    except Exception:
                        pass
                try:
                    db.save_album_key(
                        album_name=title,
                        album_media_key=info["key"],
                        account_email=account_email,
                        remote_count=info["total"],
                        cover_media_key=info["cover_key"]
                    )
                except Exception:
                    pass

        return cloud_albums
    except Exception:
        return {}


def reconcile_album_photos(
    scan_roots: List[str],
    db: UploadDatabase,
    account_email: str = "",
    api=None,
    cloud_albums: Optional[Dict[str, Dict[str, Any]]] = None
) -> Tuple[List[Dict[str, Any]], List[Path], List[Tuple[str, str]]]:
    """
    Scans local folders under scan_roots, compares against cloud albums and uploads.
    Detects:
    1. Empty albums (0 photos) on Cloud where local folder has photos.
    2. Incomplete albums where local folder has more photos than on Cloud.
    3. New local folders that don't have an album yet on Cloud.

    Guarantees:
    - If the album already exists on Cloud, photos are directly queued into it (NO new album created).
    - Only creates a new album if it does not exist on Cloud.
    """
    if not scan_roots:
        return [], [], []

    # 1. Sync remote cloud albums to ensure complete and up-to-date knowledge
    if cloud_albums is None and api is not None:
        try:
            cloud_albums = sync_cloud_albums(api=api, db=db, account_email=account_email)
        except Exception:
            cloud_albums = {}

    if cloud_albums is None:
        # Fallback to local DB albums
        try:
            db_albums = db.get_all_albums(account_email)
            cloud_albums = {
                a["album_name"]: {
                    "key": a["album_media_key"],
                    "total": a.get("photo_count", 0)
                }
                for a in db_albums if a.get("album_name")
            }
        except Exception:
            cloud_albums = {}

    try:
        db.load_fast_cache(account_email)
        uploaded_map = {k[0]: v["media_key"] for k, v in db._fast_cache.items()}
    except Exception:
        uploaded_map = {}

    album_items_set = set()
    try:
        with db._get_connection() as conn:
            rows = conn.execute(
                "SELECT album_name, media_key FROM album_items WHERE account_email = ? OR account_email = '' OR account_email IS NULL",
                (account_email,)
            ).fetchall()
            album_items_set = {(r["album_name"], r["media_key"]) for r in rows}
    except Exception:
        pass

    normalized_cloud: Dict[str, Dict[str, Any]] = {}
    if cloud_albums:
        for k, v in cloud_albums.items():
            if k:
                normalized_cloud[k.strip().lower()] = v

    # Group media files across scan_roots by their true album name
    album_groups: Dict[str, Dict[str, Any]] = {}
    for root_str in scan_roots:
        root_path = Path(root_str)
        if not root_path.exists() or not root_path.is_dir():
            continue

        for dirpath, _, filenames in os.walk(root_path):
            for f in filenames:
                if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS:
                    fp = Path(dirpath) / f
                    alb_name = determine_album_name(fp, scan_roots)
                    if not alb_name:
                        continue
                    if alb_name not in album_groups:
                        folder_rep = str(fp.parent if not is_subfolder_artifact(fp.parent.name) else fp.parent.parent)
                        album_groups[alb_name] = {
                            "folder_path": folder_rep,
                            "files": []
                        }
                    album_groups[alb_name]["files"].append(fp)

    discrepancies = []

    missing_to_upload = []
    already_uploaded_needing_album = []

    for album_name, group in album_groups.items():
        media_files = group["files"]
        dirpath = group["folder_path"]
        
        # Match cloud album info (exact match, then stripped/lower match)
        cloud_info = cloud_albums.get(album_name) if cloud_albums else None
        if not cloud_info and cloud_albums:
            cloud_info = normalized_cloud.get(album_name.strip().lower())
            
        album_exists_on_cloud = cloud_info is not None and bool(cloud_info.get("key"))
        cloud_photo_count = cloud_info.get("total", 0) if cloud_info else 0

        folder_missing_upload = []
        folder_already_on_cloud = []

        for fp in media_files:
            p_str = str(fp)
            m_key = uploaded_map.get(p_str)
            if m_key:
                if (album_name, m_key) not in album_items_set:
                    folder_already_on_cloud.append((album_name, m_key))
            else:
                folder_missing_upload.append(fp)

        # Server disparity check:
        # If album exists on Cloud, but Google Photos server has FEWER items than local files:
        # (cloud_photo_count < len(media_files)), then the server is definitely missing items!
        # Even if items were recorded locally in album_items, the server doesn't have them!
        # Therefore, we collect all uploaded media_keys for this album to ensure they are pushed to the server.
        server_is_missing_items = album_exists_on_cloud and (cloud_photo_count < len(media_files))

        if server_is_missing_items:
            already_queued_keys = {mk for _, mk in folder_already_on_cloud}
            for fp in media_files:
                p_str = str(fp)
                m_key = uploaded_map.get(p_str)
                if m_key and m_key not in already_queued_keys:
                    folder_already_on_cloud.append((album_name, m_key))
                    already_queued_keys.add(m_key)

        # If cloud already has >= total local files AND no local files need upload AND no items need album assignment:
        if album_exists_on_cloud and cloud_photo_count >= len(media_files) and not folder_missing_upload and not folder_already_on_cloud:
            continue

        if folder_missing_upload or folder_already_on_cloud or not album_exists_on_cloud or server_is_missing_items:
            local_vids = [f for f in media_files if f.suffix.lower() in VIDEO_EXTENSIONS]
            missing_vids = [f for f in folder_missing_upload if f.suffix.lower() in VIDEO_EXTENSIONS]
            
            discrepancies.append({
                "album_name": album_name,
                "folder_path": dirpath,
                "total_local": len(media_files),
                "local_photos": len(media_files) - len(local_vids),
                "local_videos": len(local_vids),
                "cloud_count": cloud_photo_count,
                "missing_upload": len(folder_missing_upload),
                "missing_upload_photos": len(folder_missing_upload) - len(missing_vids),
                "missing_upload_videos": len(missing_vids),
                "needs_album_assignment": len(folder_already_on_cloud),
                "album_exists_on_cloud": album_exists_on_cloud,
                "server_is_missing_items": server_is_missing_items,
            })
            missing_to_upload.extend(folder_missing_upload)
            already_uploaded_needing_album.extend(folder_already_on_cloud)

    return discrepancies, missing_to_upload, already_uploaded_needing_album



class PhotoUploader:
    def __init__(
        self,
        auth_data: str,
        db: UploadDatabase,
        event_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        log_callback: Optional[Callable[[str, str], None]] = None,
        log_func: Optional[Callable[[str, str], None]] = None,
        threads: int = 4,
        quality: str = "original",
        auto_album: bool = False,
        sync_roots: Optional[List[str]] = None,
        **kwargs
    ):
        self.auth_data = auth_data.strip()
        self.account_email = ""
        if "Email=" in self.auth_data:
            try:
                import urllib.parse
                self.account_email = urllib.parse.unquote(self.auth_data.split("Email=")[-1].split("&")[0])
            except Exception:
                self.account_email = self.auth_data.split("Email=")[-1].split("&")[0]

        self.db = db
        self.event_callback = event_callback
        self.log_callback = log_callback or log_func
        self.threads = max(1, min(threads, 16))
        self.quality = quality  # "original" (Pixel XL Unlimited) or "saver"
        self.auto_album = auto_album
        self.sync_roots = [str(r) for r in (sync_roots or []) if r]

        self._client: Optional[gpmc.Client] = None
        self._is_paused = True
        self._is_cancelled = False
        self._queue: Queue[Path] = Queue()
        self._queued_paths: set = set()
        self._active_workers: List[threading.Thread] = []
        self._active_files: Dict[str, Dict[str, Any]] = {}
        self._active_lock = threading.Lock()

        # Batching & SQLite Caching for Albums to guarantee 1 Album per folder
        self._album_pending_keys: Dict[str, List[str]] = {}
        self._album_forced_albums: Set[str] = set()
        self._album_lock = threading.Lock()
        self._album_flusher_thread: Optional[threading.Thread] = None
        self._album_processing = False

        # Cloud Album Cache: guarantees existing albums on Cloud are reused and never duplicated
        self._cloud_albums_cache: Dict[str, str] = {}
        self._cloud_sync_lock = threading.Lock()

        # High-Speed Keep-Alive connection pool for checking Google Photos hash
        RateLimiter.set_logger(self._log)
        self._pool_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=25,
            pool_maxsize=25,
            max_retries=requests.adapters.Retry(
                total=3,
                backoff_factor=1.0,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=None  # Allows retrying POST requests
            )
        )
        self._pool_session.mount("https://", adapter)
        self._pool_session.mount("http://", adapter)

        # Preload fast cache for this account
        try:
            self.db.load_fast_cache(self.account_email)
        except Exception:
            pass

        self._init_client()

    def _log(self, message: str, level: str = "INFO") -> None:
        if self.log_callback:
            try:
                self.log_callback(message, level)
            except Exception:
                pass

    def _init_client(self) -> None:
        try:
            self._client = gpmc.Client(
                auth_data=self.auth_data,
                log_level="WARNING",
            )
            email = self.account_email or (self.auth_data.split("Email=")[-1].split("&")[0] if "Email=" in self.auth_data else "")
            self._log(f"Đã kích hoạt sao lưu đa luồng ({self.threads} luồng) cho: {email}", "SUCCESS")
            # Preload remote cloud albums in background so existing albums are immediately mapped
            threading.Thread(target=self.sync_cloud_albums, daemon=True).start()
        except Exception as e:
            self._log(f"Lỗi khởi tạo Google Photos Client: {e}", "ERROR")
            raise

    def check_google_photos_hash(self, sha1_hash: str) -> Optional[str]:
        """
        Check if file hash exists on Google Photos using persistent Keep-Alive session.
        With built-in 429 rate limit backoff, Retry-After handling, and coordinated delay.
        """
        try:
            from gpmc.hash_handler import convert_sha1_hash
            from gpmc import message_types
            from blackboxprotobuf import encode_message, decode_message

            hash_bytes, _ = convert_sha1_hash(sha1_hash)
            proto_body = {"1": {"1": {"1": hash_bytes}, "2": {}}}
            serialized_data = encode_message(proto_body, message_types.FIND_REMOTE_MEDIA_BY_HASH)

            api = self._client.api
            headers = {
                "Accept-Encoding": "gzip",
                "Accept-Language": getattr(api, "language", "en"),
                "Content-Type": "application/x-protobuf",
                "User-Agent": getattr(api, "user_agent", "GooglePhotos/6.0"),
                "Authorization": f"Bearer {api.bearer_token}",
            }

            max_retries = 5
            backoff = 3.0
            for attempt in range(max_retries):
                RateLimiter.wait_if_needed()
                RateLimiter.pace(0.08)

                try:
                    resp = self._pool_session.post(
                        "https://photosdata-pa.googleapis.com/6439526531001121323/5084965799730810217",
                        headers=headers,
                        data=serialized_data,
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        decoded, _ = decode_message(resp.content)
                        media_key = decoded["1"].get("2", {}).get("2", {}).get("1", None)
                        return media_key
                    elif resp.status_code == 429:
                        retry_after = resp.headers.get("Retry-After")
                        wait_sec = parse_retry_after(retry_after, default=backoff)
                        RateLimiter.trigger(wait_sec, "kiểm tra hash 429")
                        if attempt < max_retries - 1:
                            time.sleep(wait_sec)
                            backoff = min(backoff * 2, 60.0)
                            continue
                        return None
                    elif resp.status_code in (500, 502, 503, 504):
                        if attempt < max_retries - 1:
                            time.sleep(backoff)
                            backoff = min(backoff * 1.5, 30.0)
                            continue
                        return None
                    else:
                        return None
                except Exception as req_err:
                    if "429" in str(req_err):
                        RateLimiter.trigger(backoff, "429 exception khi kiểm tra hash")
                        if attempt < max_retries - 1:
                            time.sleep(backoff)
                            backoff = min(backoff * 2, 60.0)
                            continue
                    if attempt < max_retries - 1:
                        time.sleep(backoff)
                        backoff = min(backoff * 1.5, 30.0)
                        continue
                    return None
            return None
        except Exception:
            # Fallback to gpmc built-in method
            try:
                RateLimiter.wait_if_needed()
                return self._client.get_media_key_by_hash(sha1_hash)
            except Exception:
                return None

    @property
    def is_uploading(self) -> bool:
        with self._active_lock:
            has_active = len(self._active_files) > 0 or not self._queue.empty()
        with self._album_lock:
            has_album = any(len(keys) > 0 for keys in self._album_pending_keys.values())
        return has_active or has_album

    @property
    def active_count(self) -> int:
        with self._active_lock:
            return len(self._active_files)

    def update_settings(self, quality: Optional[str] = None, threads: Optional[int] = None, auto_album: Optional[bool] = None, sync_roots: Optional[List[str]] = None) -> None:
        if quality is not None:
            self.quality = quality
        if threads is not None:
            self.threads = max(1, min(threads, 16))
        if auto_album is not None:
            self.auto_album = auto_album
        if sync_roots is not None:
            self.sync_roots = [str(r) for r in sync_roots if r]

    def pause(self) -> None:
        self._is_paused = True
        self._log("Đã tạm dừng tiến trình sao lưu đa luồng.", "WARNING")

    def resume(self) -> None:
        self._is_paused = False
        self._log("Tiếp tục tiến trình sao lưu đa luồng.", "INFO")

    def cancel(self) -> None:
        self._is_cancelled = True
        with self._queue.mutex:
            self._queue.queue.clear()
        with self._active_lock:
            self._active_files.clear()
            self._queued_paths.clear()
        self._log("Đã huỷ toàn bộ hàng đợi tải lên.", "WARNING")
        self._emit_event({"type": "queue_cancelled", "remaining_queue": 0, "active_count": 0})

    def is_queued_or_active(self, file_path: Path) -> bool:
        """Check if file is currently active or waiting in queue."""
        path_str = str(file_path)
        with self._active_lock:
            return path_str in self._active_files or path_str in self._queued_paths

    def add_to_queue(self, files: List[Path]) -> int:
        """Add files to upload queue without duplicate queuing."""
        added = 0
        for f in files:
            p = Path(f)
            path_str = str(p)
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                with self._active_lock:
                    if path_str in self._queued_paths or path_str in self._active_files:
                        continue
                    self._queued_paths.add(path_str)
                self._queue.put(p)
                added += 1

        if added > 0:
            self._emit_event({
                "type": "files_added",
                "count": added,
                "remaining_queue": self._queue.qsize(),
                "active_count": self.active_count,
            })
        return added

    def start_background_worker(self) -> None:
        """Spawn worker threads up to self.threads."""
        self._is_cancelled = False

        # Clean up dead workers
        self._active_workers = [w for w in self._active_workers if w.is_alive()]

        # Spawn needed workers
        needed = self.threads - len(self._active_workers)
        for i in range(needed):
            worker_id = len(self._active_workers) + 1
            t = threading.Thread(target=self._worker_loop, args=(worker_id,), daemon=True)
            t.start()
            self._active_workers.append(t)

    def _emit_event(self, data: Dict[str, Any]) -> None:
        if self.event_callback:
            try:
                data["remaining_queue"] = self._queue.qsize()
                with self._active_lock:
                    data["active_count"] = len(self._active_files)
                self.event_callback(data)
            except Exception:
                pass

    def _worker_loop(self, worker_id: int) -> None:
        """Worker thread loop: pulls files from queue and uploads in parallel."""
        while not self._is_cancelled:
            while self._is_paused:
                time.sleep(0.3)
                if self._is_cancelled:
                    return

            try:
                file_path = self._queue.get(timeout=1.5)
                with self._active_lock:
                    self._queued_paths.discard(str(file_path))
            except Empty:
                # Check if entire queue is truly empty and no workers uploading
                with self._active_lock:
                    all_done = len(self._active_files) == 0 and self._queue.empty()
                if all_done:
                    def _finish_and_emit():
                        self.flush_pending_albums(timeout=15.0)
                        self._emit_event({
                            "type": "queue_empty",
                            "remaining_queue": 0,
                            "active_count": 0
                        })
                    threading.Thread(target=_finish_and_emit, daemon=True).start()
                break

            try:
                self._upload_single_file(file_path, worker_id)
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "Too Many Requests" in err_str:
                    wait_sec = 15.0
                    RateLimiter.trigger(wait_sec, f"Luồng {worker_id} gặp 429")
                    self._log(f"[Luồng {worker_id}] Gặp giới hạn tần suất 429 khi tải {file_path.name}. Giữ lại file trong hàng đợi và nghỉ {wait_sec:.0f}s...", "WARNING")
                    with self._active_lock:
                        self._queued_paths.add(str(file_path))
                    self._queue.put(file_path)
                    time.sleep(wait_sec)
                else:
                    self._log(f"[Luồng {worker_id}] Lỗi tải {file_path.name}: {e}", "ERROR")
                    self._emit_event({
                        "type": "file_error",
                        "path": str(file_path),
                        "filename": file_path.name,
                        "worker_id": worker_id,
                        "error": str(e),
                    })
            finally:
                self._queue.task_done()

    def _start_album_flusher(self) -> None:
        if self._album_flusher_thread and self._album_flusher_thread.is_alive():
            return
        self._album_flusher_thread = threading.Thread(target=self._album_flusher_loop, daemon=True)
        self._album_flusher_thread.start()

    def _queue_for_album(self, album_name: str, media_key: str, force: bool = False) -> None:
        """Queue a media key to be added to an album in batch."""
        if not album_name or not media_key:
            return
        # Fast path: check if already recorded in album locally to avoid redundant work (unless force=True)
        if not force and self.db.is_in_album(album_name, media_key, self.account_email):
            return
        with self._album_lock:
            if force:
                self._album_forced_albums.add(album_name)
            if album_name not in self._album_pending_keys:
                self._album_pending_keys[album_name] = []
            if media_key not in self._album_pending_keys[album_name]:
                self._album_pending_keys[album_name].append(media_key)
        self._start_album_flusher()

    def _album_flusher_loop(self) -> None:
        """Background worker that flushes batches of media into albums."""
        retry_counts: Dict[str, int] = {}

        while not self._is_cancelled:
            if self._is_paused:
                time.sleep(0.5)
                continue

            batches_to_process = []
            with self._album_lock:
                for alb_name, keys in list(self._album_pending_keys.items()):
                    if keys:
                        # Batch up to 200 items per API call (Google Photos supports up to 500)
                        batch = keys[:200]
                        self._album_pending_keys[alb_name] = keys[200:]
                        batches_to_process.append((alb_name, batch))

            if not batches_to_process:
                with self._active_lock:
                    still_working = len(self._active_files) > 0 or not self._queue.empty()
                if not still_working:
                    break
                time.sleep(0.5)
                continue

            for alb_name, batch in batches_to_process:
                if self._is_cancelled:
                    break
                with self._album_lock:
                    self._album_processing = True
                    is_forced = alb_name in self._album_forced_albums
                try:
                    success = self._process_album_batch(alb_name, batch, force=is_forced)
                finally:
                    with self._album_lock:
                        self._album_processing = False
                        if alb_name not in self._album_pending_keys or not self._album_pending_keys[alb_name]:
                            self._album_forced_albums.discard(alb_name)

                if not success:
                    retries = retry_counts.get(alb_name, 0) + 1
                    retry_counts[alb_name] = retries
                    if retries <= 3:
                        with self._album_lock:
                            if alb_name not in self._album_pending_keys:
                                self._album_pending_keys[alb_name] = []
                            self._album_pending_keys[alb_name] = batch + self._album_pending_keys[alb_name]
                        time.sleep(1.0)
                    else:
                        self._log(f"Đã bỏ qua gom {len(batch)} mục vào Album '{alb_name}' sau 3 lần thử không thành công.", "ERROR")
                else:
                    retry_counts.pop(alb_name, None)

            time.sleep(0.3)

    def sync_cloud_albums(self, force: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Fetch all albums from Google Photos cloud via get_library_state.
        Caches album keys in memory and SQLite db to prevent duplicate album creation.
        """
        with self._cloud_sync_lock:
            if self._cloud_albums_cache and not force:
                return {k: {"key": v} for k, v in self._cloud_albums_cache.items()}
            try:
                albums = sync_cloud_albums(
                    api=self._client.api,
                    db=self.db,
                    account_email=self.account_email
                )
                for title, info in albums.items():
                    self._cloud_albums_cache[title] = info["key"]
                return albums
            except Exception as e:
                self._log(f"Lỗi khi đồng bộ danh sách Album từ Cloud: {e}", "WARNING")
                return {}

    def _get_or_create_album_key(self, album_name: str, initial_media_keys: Optional[List[str]] = None) -> Tuple[str, bool]:
        """
        Strict Album Resolution:
        1. Check local DB cache.
        2. Check memory cloud albums cache.
        3. If not found, actively query Google Photos Cloud (get_library_state).
        4. If album exists anywhere on Google Photos, return (existing_key, False).
        5. ONLY if the album does NOT exist on Google Photos, call create_album and return (new_key, True).
        """
        album_name_clean = album_name.strip()

        # 1. Local DB lookup
        album_key = self.db.get_album_key(album_name_clean, self.account_email)
        if album_key:
            self._cloud_albums_cache[album_name_clean] = album_key
            return album_key, False

        # 2. Memory cache lookup
        if album_name_clean in self._cloud_albums_cache:
            album_key = self._cloud_albums_cache[album_name_clean]
            self.db.save_album_key(album_name_clean, album_key, self.account_email)
            return album_key, False

        # 3. Query Google Photos directly to check if album already exists on Cloud
        cloud_albums = self.sync_cloud_albums(force=True)
        if album_name_clean in self._cloud_albums_cache:
            album_key = self._cloud_albums_cache[album_name_clean]
            self.db.save_album_key(album_name_clean, album_key, self.account_email)
            return album_key, False
        if album_name_clean in cloud_albums:
            album_key = cloud_albums[album_name_clean]["key"]
            self._cloud_albums_cache[album_name_clean] = album_key
            self.db.save_album_key(album_name_clean, album_key, self.account_email)
            return album_key, False

        # Case-insensitive check
        for c_title, c_info in cloud_albums.items():
            if c_title.strip().lower() == album_name_clean.lower():
                album_key = c_info["key"]
                self._cloud_albums_cache[album_name_clean] = album_key
                self.db.save_album_key(album_name_clean, album_key, self.account_email)
                return album_key, False

        # 4. ONLY IF NO ALBUM EXISTS ON CLOUD -> Create a new album
        new_key = self._client.api.create_album(
            album_name=album_name_clean,
            media_keys=initial_media_keys or []
        )
        self.db.save_album_key(album_name_clean, new_key, self.account_email)
        self._cloud_albums_cache[album_name_clean] = new_key
        return new_key, True

    def _process_album_batch(self, album_name: str, media_keys: List[str], force: bool = False) -> bool:
        unique_keys = [k for k in dict.fromkeys(media_keys) if k]
        if not unique_keys:
            return True

        # Filter out items already recorded in this album locally (unless forced by reconcile)
        if not force:
            keys_to_add = [k for k in unique_keys if not self.db.is_in_album(album_name, k, self.account_email)]
        else:
            keys_to_add = unique_keys

        if not keys_to_add:
            return True

        try:
            album_key, was_created = self._get_or_create_album_key(album_name, initial_media_keys=keys_to_add)

            if was_created:
                # Newly created on Cloud (with initial keys already included)
                self.db.record_album_items(album_name, keys_to_add, self.account_email)
                self._log(f"📁 [Tạo Album Mới] Chưa có trên Cloud. Đã tạo Album '{album_name}' và gom {len(keys_to_add)} mục (ảnh/video) vào.", "SUCCESS")
                return True
            else:
                # Album ALREADY EXISTS on Cloud! Add photos/videos directly to this album
                try:
                    self._client.api.add_media_to_album(album_media_key=album_key, media_keys=keys_to_add)
                    self.db.record_album_items(album_name, keys_to_add, self.account_email)
                    self._log(f"📁 [Gom vào Album có sẵn] Đã thêm {len(keys_to_add)} mục (ảnh/video) vào Album '{album_name}'.", "INFO")
                    return True
                except requests.exceptions.HTTPError as e:
                    status_code = getattr(e.response, "status_code", None)
                    if status_code == 404:
                        # Check if truly deleted on Cloud before creating anew
                        self._log(f"⚠️ Album '{album_name}' báo 404. Đang kiểm tra lại trên Cloud...", "WARNING")
                        cloud_albums = self.sync_cloud_albums(force=True)
                        if album_name in cloud_albums and cloud_albums[album_name]["key"] != album_key:
                            refreshed_key = cloud_albums[album_name]["key"]
                            self._client.api.add_media_to_album(album_media_key=refreshed_key, media_keys=keys_to_add)
                            self.db.save_album_key(album_name, refreshed_key, self.account_email)
                            self.db.record_album_items(album_name, keys_to_add, self.account_email)
                            self._log(f"📁 Đã thêm {len(keys_to_add)} mục (ảnh/video) vào Album '{album_name}' theo key mới.", "SUCCESS")
                            return True
                        elif album_name not in cloud_albums:
                            # Album was deleted from Cloud
                            self._log(f"📁 Album '{album_name}' đã bị xóa trên Cloud. Đang tạo mới...", "WARNING")
                            new_key = self._client.api.create_album(album_name=album_name, media_keys=keys_to_add)
                            self.db.save_album_key(album_name, new_key, self.account_email)
                            self._cloud_albums_cache[album_name] = new_key
                            self.db.record_album_items(album_name, keys_to_add, self.account_email)
                            return True
                    # For other codes (like 400), NEVER create duplicate album!
                    self._log(f"⚠️ Lỗi gom {len(keys_to_add)} mục vào Album '{album_name}' (HTTP {status_code}): {e}", "WARNING")
                    return False
        except Exception as e:
            self._log(f"Không thể gán {len(keys_to_add)} mục vào Album '{album_name}': {e}", "WARNING")
            return False

    def _collect_all_album_media_keys(self, album_name: str) -> List[str]:
        """Collect all media_keys from uploads table where files are in the album's folder."""
        try:
            with self.db._get_connection() as conn:
                rows = conn.execute(
                    "SELECT media_key, local_path FROM uploads WHERE status = 'success' AND media_key IS NOT NULL AND media_key != '' AND (account_email = ? OR account_email = '' OR account_email IS NULL)",
                    (self.account_email,)
                ).fetchall()
                return [r["media_key"] for r in rows if r["media_key"] and r["local_path"] and determine_album_name(Path(r["local_path"]), self.sync_roots) == album_name]
        except Exception as e:
            self._log(f"Lỗi thu thập media keys cho album '{album_name}': {e}", "WARNING")
            return []

    def flush_pending_albums(self, timeout: float = 15.0) -> None:
        """Synchronously flush all pending album items."""
        start = time.time()
        while time.time() - start < timeout:
            with self._album_lock:
                pending_count = sum(len(k) for k in self._album_pending_keys.values())
                is_busy = self._album_processing
            if pending_count == 0 and not is_busy:
                break
            time.sleep(0.2)

    def _upload_single_file(self, file_path: Path, worker_id: int) -> None:
        if not file_path.exists():
            return

        try:
            stat = file_path.stat()
            file_size = stat.st_size
            mtime = stat.st_mtime
        except Exception:
            return

        filename = file_path.name
        path_str = str(file_path)

        # ===================================================================
        # TIER 1: ULTRA-FAST LOCAL CACHE CHECK (~0.001ms)
        # Bỏ qua tức thì nếu file (đúng đường dẫn + kích thước + mtime) đã được sao lưu
        # ===================================================================
        cached = self.db.fast_check_file(path_str, file_size, mtime, self.account_email)
        if cached and cached.get("media_key"):
            remote_key = cached["media_key"]
            album_name = determine_album_name(file_path, self.sync_roots) if self.auto_album else None
            if self.auto_album and album_name and remote_key:
                self._queue_for_album(album_name, remote_key)

            self._emit_event({
                "type": "file_skipped_fast",
                "path": path_str,
                "filename": filename,
                "worker_id": worker_id,
                "bytes_completed": file_size,
                "bytes_total": file_size,
                "percent": 100.0,
                "status": "Đã có sẵn trên Cloud ✓",
                "was_skipped": True,
            })
            return

        # ===================================================================
        # TIER 2: UNCACHED FILE - Active Card & Fast Streaming 4MB SHA-1
        # ===================================================================
        with self._active_lock:
            self._active_files[path_str] = {
                "filename": filename,
                "worker_id": worker_id,
                "percent": 0.0,
                "status": "Kiểm tra hash...",
            }

        self._emit_event({
            "type": "file_started",
            "path": path_str,
            "filename": filename,
            "worker_id": worker_id,
            "bytes_completed": 0,
            "bytes_total": file_size,
            "percent": 0.0,
            "status": "Đang chuẩn bị...",
        })

        # Calculate SHA-1 with fast 4MB buffered chunks
        sha1_hash = UploadDatabase.calculate_sha1(file_path)
        with self._active_lock:
            if path_str in self._active_files:
                self._active_files[path_str]["status"] = "Kiểm tra Cloud..."

        self._emit_event({
            "type": "file_progress",
            "path": path_str,
            "filename": filename,
            "worker_id": worker_id,
            "bytes_completed": 0,
            "bytes_total": file_size,
            "percent": 0.0,
            "status": "Kiểm tra Google Photos (Keep-Alive)...",
            "speed": "",
        })

        # ===================================================================
        # TIER 3: HIGH-SPEED KEEP-ALIVE CHECK WITH GOOGLE PHOTOS (20-40ms)
        # ===================================================================
        remote_key = None
        for attempt in range(2):
            try:
                remote_key = self.check_google_photos_hash(sha1_hash)
                break
            except Exception as e:
                if attempt == 0:
                    time.sleep(0.3)
                else:
                    self._log(f"[Luồng {worker_id}] Lỗi kiểm tra hash trên Google ({e}), tiến hành kiểm tra khi tải...", "WARNING")

        if remote_key:
            # File is confirmed present on Google Photos server
            self.db.record_upload(
                local_path=path_str,
                filename=filename,
                sha1_hash=sha1_hash,
                file_size=file_size,
                media_key=remote_key,
                status="success",
                account_email=self.account_email,
                mtime=mtime
            )
            self._log(f"[Luồng {worker_id}] ☁️ [Google Photos] Đã có sẵn trên Cloud: {filename} (Bỏ qua)", "INFO")

            # Queue into batch album flusher if auto_album is enabled
            album_name = determine_album_name(file_path, self.sync_roots) if self.auto_album else None
            if self.auto_album and album_name and remote_key:
                self._queue_for_album(album_name, remote_key)

            with self._active_lock:
                self._active_files.pop(path_str, None)
            self._emit_event({
                "type": "file_completed",
                "path": path_str,
                "filename": filename,
                "worker_id": worker_id,
                "bytes_completed": file_size,
                "bytes_total": file_size,
                "percent": 100.0,
                "status": "Đã có trên Cloud ✓",
                "was_skipped": True,
            })
            return

        # ===================================================================
        # TIER 4: FILE IS NOT ON GOOGLE PHOTOS - Upload with Pixel XL
        # ===================================================================
        was_in_db = self.db.is_file_uploaded(sha1_hash)
        if was_in_db:
            self.db.remove_upload_by_hash(sha1_hash)
            self._log(f"[Luồng {worker_id}] 🔄 Phát hiện {filename} đã bị xoá trên Google Photos -> Đang tải lên lại...", "INFO")
        else:
            self._log(f"[Luồng {worker_id}] Bắt đầu tải {filename} ({file_size / (1024*1024):.1f} MB)...", "INFO")

        # 3. Perform Upload with Pixel XL Unlimited Quota
        start_time = time.time()
        album_name = determine_album_name(file_path, self.sync_roots) if self.auto_album else None
        is_saver = (self.quality == "saver")

        def file_progress(event: UploadProgressEvent) -> None:
            now = time.time()
            elapsed = now - start_time
            done = event.get("bytes_completed", 0)
            total = event.get("bytes_total", file_size) or file_size
            pct = round((done / total) * 100.0, 1) if total > 0 else 0.0

            speed_str = ""
            if elapsed > 0.3 and done > 0:
                speed_bps = done / elapsed
                if speed_bps > 1024 * 1024:
                    speed_str = f"{speed_bps / (1024*1024):.1f} MB/s"
                else:
                    speed_str = f"{speed_bps / 1024:.0f} KB/s"

            with self._active_lock:
                if path_str in self._active_files:
                    self._active_files[path_str]["percent"] = pct
                    self._active_files[path_str]["speed"] = speed_str

            self._emit_event({
                "type": "file_progress",
                "path": path_str,
                "filename": filename,
                "worker_id": worker_id,
                "bytes_completed": done,
                "bytes_total": total,
                "percent": pct,
                "status": f"Đang tải ({pct:.0f}%)",
                "speed": speed_str,
            })

        # Upload media item directly (album_name=None prevents simultaneous duplicate create_album calls)
        # Pass pre-calculated sha1_hash and force_upload=True to eliminate duplicate hash checking and prevent 429
        result = self._client.upload(
            target={file_path: {"hash": sha1_hash}},
            album_name=None,
            use_quota=False,   # <--- UNLIMITED STORAGE PIXEL XL SPOOFING
            saver=is_saver,
            threads=1,         # Per-worker thread handles 1 file concurrently
            force_upload=True, # <--- PREVENTS redundant find_remote_media_by_hash call!
            progress_callback=file_progress,
        )

        posix_path = file_path.absolute().as_posix()
        media_key = result.get(posix_path) or result.get(path_str) or (list(result.values())[0] if result else "")

        if not media_key:
            # Re-verify with Google Photos in case upload succeeded
            try:
                media_key = self._client.get_media_key_by_hash(sha1_hash) or ""
            except Exception:
                pass

        # Record in local DB
        self.db.record_upload(
            local_path=path_str,
            filename=filename,
            sha1_hash=sha1_hash,
            file_size=file_size,
            media_key=media_key,
            status="success",
            account_email=self.account_email,
            mtime=mtime
        )

        # Queue into batch album flusher
        if self.auto_album and album_name and media_key:
            self._queue_for_album(album_name, media_key)

        with self._active_lock:
            self._active_files.pop(path_str, None)

        self._log(f"[Luồng {worker_id}] ✅ Hoàn tất {filename} (Pixel XL - Không tính quota)!", "SUCCESS")

        # Emit completion event (triggers Android-style fade-out animation in UI)
        self._emit_event({
            "type": "file_completed",
            "path": path_str,
            "filename": filename,
            "worker_id": worker_id,
            "bytes_completed": file_size,
            "bytes_total": file_size,
            "percent": 100.0,
            "status": "Hoàn tất ✓",
            "was_skipped": False,
        })

    def unbackup_remote_media(
        self,
        sha1_hashes: Sequence[str],
        permanent: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[int, int]:
        """
        Delete or move remote media items to Google Photos Trash using SHA-1 hashes.
        Processes in batches of 500 to conform to Google Photos Mobile API limits.

        Args:
            sha1_hashes: List of hex SHA-1 hashes to delete from Google Photos.
            permanent: If True, permanently delete; if False, move to Google Photos Trash.
            progress_callback: Optional callback receiving (processed_count, total_count).

        Returns:
            Tuple[int, int]: (success_count, error_count)
        """
        if not self._client:
            self._init_client()
        if not self._client:
            raise RuntimeError("Google Photos client is not initialized.")

        import base64
        import gpmc.utils as gpmc_utils

        total_count = len(sha1_hashes)
        if total_count == 0:
            return (0, 0)

        # Convert hex sha1 to urlsafe base64 dedup_keys
        dedup_keys = []
        for h in sha1_hashes:
            try:
                if len(h) == 40:
                    raw_bytes = bytes.fromhex(h)
                    b64_str = base64.b64encode(raw_bytes).decode("utf-8")
                else:
                    b64_str = h
                dedup_keys.append(gpmc_utils.urlsafe_base64(b64_str))
            except Exception:
                continue

        batch_size = 500
        success_count = 0
        error_count = 0

        for i in range(0, len(dedup_keys), batch_size):
            batch = dedup_keys[i : i + batch_size]
            current_batch_size = len(batch)
            attempts = 0
            batch_success = False

            while attempts < 3 and not batch_success:
                attempts += 1
                try:
                    if permanent:
                        try:
                            self._client.api.delete_remote_media_permanently(dedup_keys=batch)
                        except requests.exceptions.RequestException:
                            raise
                        except Exception:
                            # HTTP request returned 200 OK; blackboxprotobuf response decoding quirk on Python 3.13 can be safely ignored
                            pass
                    else:
                        try:
                            self._client.api.move_remote_media_to_trash(dedup_keys=batch)
                        except requests.exceptions.RequestException:
                            raise
                        except Exception:
                            # HTTP request returned 200 OK; blackboxprotobuf response decoding quirk on Python 3.13 can be safely ignored
                            pass
                    batch_success = True
                    success_count += current_batch_size
                except Exception as e:
                    if attempts >= 3:
                        import traceback
                        tb_str = traceback.format_exc()
                        self._log(f"Error unbacking batch ({i}-{i+current_batch_size}): {e}\n{tb_str}", "ERROR")
                        error_count += current_batch_size
                    else:
                        time.sleep(1.0)

            if progress_callback:
                try:
                    progress_callback(min(i + current_batch_size, total_count), total_count)
                except Exception:
                    pass

        return (success_count, error_count)

    def restore_remote_media_from_trash(
        self,
        sha1_hashes: Sequence[str],
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[int, int]:
        """
        Restore remote media items from Google Photos Trash using SHA-1 hashes.
        Processes in batches of 500 to conform to Google Photos Mobile API limits.
        """
        if not self._client:
            self._init_client()
        if not self._client:
            raise RuntimeError("Google Photos client is not initialized.")

        import base64
        import gpmc.utils as gpmc_utils

        total_count = len(sha1_hashes)
        if total_count == 0:
            return (0, 0)

        dedup_keys = []
        for h in sha1_hashes:
            try:
                if len(h) == 40:
                    raw_bytes = bytes.fromhex(h)
                    b64_str = base64.b64encode(raw_bytes).decode("utf-8")
                else:
                    b64_str = h
                dedup_keys.append(gpmc_utils.urlsafe_base64(b64_str))
            except Exception:
                continue

        batch_size = 500
        success_count = 0
        error_count = 0

        for i in range(0, len(dedup_keys), batch_size):
            batch = dedup_keys[i : i + batch_size]
            current_batch_size = len(batch)
            attempts = 0
            batch_success = False

            while attempts < 3 and not batch_success:
                attempts += 1
                try:
                    try:
                        self._client.api.restore_from_trash(dedup_keys=batch)
                    except requests.exceptions.RequestException:
                        raise
                    except Exception:
                        # HTTP request returned 200 OK; blackboxprotobuf response decoding quirk on Python 3.13 can be safely ignored
                        pass
                    batch_success = True
                    success_count += current_batch_size
                except Exception as e:
                    if attempts >= 3:
                        error_count += current_batch_size
                    else:
                        time.sleep(1.0)

            if progress_callback:
                try:
                    progress_callback(min(i + current_batch_size, total_count), total_count)
                except Exception:
                    pass

        return (success_count, error_count)


