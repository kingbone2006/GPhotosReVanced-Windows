"""Uploader engine for Google Photos ReVanced Windows edition.
Features multi-threaded parallel uploads (Pixel XL unlimited spoofing),
per-file live event callbacks, deduplication, and worker pool management.
"""

import os
import time
import threading
from pathlib import Path
from queue import Queue, Empty
from typing import Optional, Callable, Dict, Any, List

import requests
import gpmc
from gpmc.client import UploadProgressEvent
from .db import UploadDatabase

SUPPORTED_EXTENSIONS = {
    # Images
    ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".gif",
    ".bmp", ".tiff", ".tif", ".ico", ".svg",
    # RAW
    ".dng", ".cr2", ".cr3", ".nef", ".arw", ".rw2", ".orf", ".pef",
    # Videos
    ".mp4", ".mov", ".m4v", ".mkv", ".avi", ".wmv", ".flv", ".webm", ".3gp", ".mts"
}


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
        self.threads = max(1, min(threads, 10))
        self.quality = quality  # "original" (Pixel XL Unlimited) or "saver"
        self.auto_album = auto_album

        self._client: Optional[gpmc.Client] = None
        self._is_paused = False
        self._is_cancelled = False
        self._queue: Queue[Path] = Queue()
        self._queued_paths: set = set()
        self._active_workers: List[threading.Thread] = []
        self._active_files: Dict[str, Dict[str, Any]] = {}
        self._active_lock = threading.Lock()

        # Batching & SQLite Caching for Albums to guarantee 1 Album per folder
        self._album_pending_keys: Dict[str, List[str]] = {}
        self._album_lock = threading.Lock()
        self._album_flusher_thread: Optional[threading.Thread] = None
        self._album_processing = False

        # High-Speed Keep-Alive connection pool for checking Google Photos hash
        self._pool_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=25,
            pool_maxsize=25,
            max_retries=requests.adapters.Retry(total=2, backoff_factor=0.3, status_forcelist=[502, 503, 504])
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
        except Exception as e:
            self._log(f"Lỗi khởi tạo Google Photos Client: {e}", "ERROR")
            raise

    def check_google_photos_hash(self, sha1_hash: str) -> Optional[str]:
        """
        Check if file hash exists on Google Photos using persistent Keep-Alive session.
        Reuses TLS connections to achieve 20-40ms response times (10-15x faster than recreating sessions).
        """
        try:
            import gpmc.utils
            from gpmc import message_types
            from gpmc.message_encoder import encode_message
            from gpmc.message_decoder import decode_message

            hash_bytes, _ = gpmc.utils.convert_sha1_hash(sha1_hash)
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
            resp = self._pool_session.post(
                "https://photosdata-pa.googleapis.com/6439526531001121323/5084965799730810217",
                headers=headers,
                data=serialized_data,
                timeout=12,
            )
            if resp.status_code == 200:
                decoded, _ = decode_message(resp.content)
                media_key = decoded["1"].get("2", {}).get("2", {}).get("1", None)
                return media_key
            return None
        except Exception:
            # Fallback to gpmc built-in method
            try:
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

    def update_settings(self, quality: Optional[str] = None, threads: Optional[int] = None, auto_album: Optional[bool] = None) -> None:
        if quality is not None:
            self.quality = quality
        if threads is not None:
            self.threads = max(1, min(threads, 10))
        if auto_album is not None:
            self.auto_album = auto_album

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

    def _queue_for_album(self, album_name: str, media_key: str) -> None:
        """Queue a media key to be added to an album in batch."""
        if not album_name or not media_key:
            return
        # Fast path: check if already recorded in album locally to avoid redundant work
        if self.db.is_in_album(album_name, media_key, self.account_email):
            return
        with self._album_lock:
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
                try:
                    success = self._process_album_batch(alb_name, batch)
                finally:
                    with self._album_lock:
                        self._album_processing = False

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
                        self._log(f"Đã bỏ qua gom {len(batch)} ảnh vào Album '{alb_name}' sau 3 lần thử không thành công.", "ERROR")
                else:
                    retry_counts.pop(alb_name, None)

            time.sleep(0.3)

    def _process_album_batch(self, album_name: str, media_keys: List[str]) -> bool:
        unique_keys = [k for k in dict.fromkeys(media_keys) if k]
        if not unique_keys:
            return True

        # Filter out items already recorded in this album
        keys_to_add = [k for k in unique_keys if not self.db.is_in_album(album_name, k, self.account_email)]
        if not keys_to_add:
            return True

        try:
            album_key = self.db.get_album_key(album_name, self.account_email)

            if not album_key:
                # Create the album ONCE for this account
                album_key = self._client.api.create_album(album_name=album_name, media_keys=keys_to_add)
                self.db.save_album_key(album_name, album_key, self.account_email)
                self.db.record_album_items(album_name, keys_to_add, self.account_email)
                self._log(f"📁 [Auto-Album] Đã tạo Album '{album_name}' và gom {len(keys_to_add)} ảnh vào.", "SUCCESS")
                return True
            else:
                # Add this batch into the existing album
                try:
                    self._client.api.add_media_to_album(album_media_key=album_key, media_keys=keys_to_add)
                    self.db.record_album_items(album_name, keys_to_add, self.account_email)
                    self._log(f"📁 [Auto-Album] Đã gom thêm {len(keys_to_add)} ảnh vào Album '{album_name}'.", "INFO")
                    return True
                except requests.exceptions.HTTPError as e:
                    status_code = getattr(e.response, "status_code", None)
                    # 404 (Album deleted or not found) or 400/403 (Invalid album key / from other account)
                    if status_code in (400, 403, 404):
                        self._log(f"⚠️ Album '{album_name}' không còn hợp lệ trên Cloud (HTTP {status_code}). Đang tạo mới...", "WARNING")
                        self.db.delete_album_key(album_name, self.account_email)
                        self.db.clear_album_items(album_name, self.account_email)
                        new_album_key = self._client.api.create_album(album_name=album_name, media_keys=keys_to_add)
                        self.db.save_album_key(album_name, new_album_key, self.account_email)
                        self.db.record_album_items(album_name, keys_to_add, self.account_email)
                        self._log(f"📁 [Auto-Album] Đã tạo lại Album '{album_name}' thành công và gom {len(keys_to_add)} ảnh vào.", "SUCCESS")
                        return True
                    else:
                        raise
        except Exception as e:
            self._log(f"Không thể gán {len(keys_to_add)} ảnh vào Album '{album_name}': {e}", "WARNING")
            return False

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
            album_name = file_path.parent.name if self.auto_album else None
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
            album_name = file_path.parent.name if self.auto_album else None
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
        album_name = file_path.parent.name if self.auto_album else None
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
        result = self._client.upload(
            target=file_path,
            album_name=None,
            use_quota=False,   # <--- UNLIMITED STORAGE PIXEL XL SPOOFING
            saver=is_saver,
            threads=1,         # Per-worker thread handles 1 file concurrently
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
