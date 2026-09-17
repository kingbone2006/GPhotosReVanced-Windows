"""Folder Watcher Service for Google Photos ReVanced Windows.
Monitors configured folders for newly added photos and videos,
waiting for file write completion before dispatching to the uploader queue.
"""

import time
import threading
from pathlib import Path
from typing import List, Set, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

from .uploader import PhotoUploader, SUPPORTED_EXTENSIONS


class PhotoEventHandler(FileSystemEventHandler):
    def __init__(self, uploader: PhotoUploader, log_func: Optional[Callable[[str, str], None]] = None):
        super().__init__()
        self.uploader = uploader
        self.log_func = log_func
        self._pending_files: Set[str] = set()
        self._lock = threading.Lock()

    def _log(self, msg: str, level: str = "INFO"):
        if self.log_func:
            self.log_func(msg, level)

    def on_created(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path)

    def _handle_file_event(self, path_str: str):
        path = Path(path_str)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            return

        if self.uploader.is_queued_or_active(path):
            return

        with self._lock:
            if path_str in self._pending_files:
                return
            self._pending_files.add(path_str)

        # Process in separate thread to wait for file writing completion
        threading.Thread(target=self._wait_and_queue, args=(path,), daemon=True).start()

    def _wait_and_queue(self, file_path: Path):
        try:
            if not file_path.exists():
                return

            if self.uploader.is_queued_or_active(file_path):
                return


            # File debounce check: wait until file size is stable (not being actively copied/downloaded)
            last_size = -1
            stable_count = 0
            for _ in range(12):  # Wait up to 6 seconds
                if not file_path.exists():
                    return
                try:
                    curr_size = file_path.stat().st_size
                    if curr_size == last_size and curr_size > 0:
                        stable_count += 1
                        if stable_count >= 2:
                            break
                    else:
                        stable_count = 0
                    last_size = curr_size
                except (OSError, PermissionError):
                    pass
                time.sleep(0.5)

            if file_path.exists() and file_path.stat().st_size > 0:
                if not self.uploader.is_queued_or_active(file_path):
                    self.uploader.add_to_queue([file_path])
                    if not getattr(self.uploader, "_is_paused", False):
                        self._log(f"[Tự động phát hiện] Thêm file mới vào hàng đợi: {file_path.name}", "INFO")
                        self.uploader.start_background_worker()
                    else:
                        self._log(f"[Tự động phát hiện] Đã thêm {file_path.name} vào hàng đợi (Đang tạm dừng, bấm Bắt đầu để tải).", "INFO")
        finally:
            with self._lock:
                self._pending_files.discard(str(file_path))


class FolderWatcher:
    def __init__(self, uploader: PhotoUploader, folders: List[str], log_func: Optional[Callable[[str, str], None]] = None):
        self.uploader = uploader
        self.folders = [f for f in folders if Path(f).exists()]
        self.log_func = log_func
        self.observer: Optional[Observer] = None
        self.handler = PhotoEventHandler(self.uploader, self.log_func)
        self._is_running = False

    def start(self) -> None:
        """Start watching directories."""
        if self._is_running:
            return

        self.observer = Observer()
        active_count = 0
        for f in self.folders:
            p = Path(f)
            if p.exists() and p.is_dir():
                self.observer.schedule(self.handler, str(p), recursive=True)
                active_count += 1

        if active_count > 0:
            self.observer.start()
            self._is_running = True
            if self.log_func:
                self.log_func(f"Đã kích hoạt theo dõi tự động cho {active_count} thư mục.", "SUCCESS")

    def stop(self) -> None:
        """Stop watching directories."""
        if not self._is_running or not self.observer:
            return
        try:
            self.observer.stop()
            self.observer.join(timeout=2.0)
        except Exception:
            pass
        self._is_running = False
        if self.log_func:
            self.log_func("Đã dừng theo dõi thư mục tự động.", "WARNING")

    def update_folders(self, folders: List[str]) -> None:
        """Update monitored folders and restart observer."""
        was_running = self._is_running
        self.stop()
        self.folders = [f for f in folders if Path(f).exists()]
        if was_running:
            self.start()

    def update_folders_async(self, folders: List[str]) -> None:
        """Asynchronously update monitored folders in background thread to keep UI smooth."""
        threading.Thread(target=self.update_folders, args=(folders,), daemon=True).start()

    @property
    def is_running(self) -> bool:
        return self._is_running
