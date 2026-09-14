"""Visual Multi-Threaded Upload Tray for Google Photos ReVanced Windows.
Emulates Android Google Photos backup carousel with live thumbnails,
progress rings/bars, and zero-flicker fixed worker slots to prevent layout thrashing.
"""

import os
import threading
from pathlib import Path
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageOps
import customtkinter as ctk
from core.i18n import t


# Global thumbnail cache and background worker pool
_THUMB_CACHE: Dict[str, ctk.CTkImage] = {}
_CACHE_LOCK = threading.Lock()
_THUMB_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ThumbWorker")


def get_file_thumbnail(file_path: Path, size=(96, 96)) -> Optional[ctk.CTkImage]:
    """Generate or retrieve a cached square thumbnail for image/video files using fast decoding."""
    path_str = str(file_path)
    with _CACHE_LOCK:
        if path_str in _THUMB_CACHE:
            return _THUMB_CACHE[path_str]

    ext = file_path.suffix.lower()
    img = None
    try:
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
            with Image.open(file_path) as raw:
                # Fast DCT draft decoding for JPEG to save massive CPU and RAM
                if ext in {".jpg", ".jpeg"}:
                    try:
                        raw.draft("RGB", (128, 128))
                    except Exception:
                        pass
                raw = ImageOps.exif_transpose(raw)
                # Fast BILINEAR resampling for 96x96 thumbnails (4x faster than Lanczos)
                img = ImageOps.fit(raw, size, Image.Resampling.BILINEAR)
        elif ext in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".3gp"}:
            img = Image.new("RGB", size, color="#1e293b")
        else:
            img = Image.new("RGB", size, color="#334155")
    except Exception:
        img = Image.new("RGB", size, color="#1e293b")

    if img:
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
        with _CACHE_LOCK:
            if len(_THUMB_CACHE) > 500:
                _THUMB_CACHE.pop(next(iter(_THUMB_CACHE)))
            _THUMB_CACHE[path_str] = ctk_img
        return ctk_img
    return None


class WorkerSlotCard(ctk.CTkFrame):
    """
    Dedicated worker slot card. Reuses widgets in-place to guarantee ZERO overlapping,
    eliminate layout recalculations, and deliver smooth 60fps performance.
    """
    def __init__(self, parent, worker_id: int = 1):
        super().__init__(
            parent,
            width=140,
            height=190,
            fg_color="#18181b",
            border_color="#27272a",
            border_width=1,
            corner_radius=10
        )
        self.pack_propagate(False)

        self.worker_id = worker_id
        self.current_file: Optional[Path] = None
        self._complete_timer: Optional[str] = None

        # 1. Thumbnail Container
        self.thumb_frame = ctk.CTkFrame(self, width=120, height=96, fg_color="#09090b", corner_radius=8)
        self.thumb_frame.pack(padx=8, pady=(8, 4))
        self.thumb_frame.pack_propagate(False)

        self.lbl_thumb = ctk.CTkLabel(self.thumb_frame, text="📷", font=ctk.CTkFont(size=24))
        self.lbl_thumb.place(relx=0.5, rely=0.5, anchor="center")

        # Worker thread badge (top-left of thumbnail)
        self.lbl_badge = ctk.CTkLabel(
            self.thumb_frame,
            text=f"{t('card_thread')} {worker_id}",
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color="#1e3a8a",
            text_color="#93c5fd",
            corner_radius=4,
            padx=4,
            pady=1
        )
        self.lbl_badge.place(x=4, y=4)

        # 2. File name label
        self.lbl_name = ctk.CTkLabel(
            self,
            text=f"Luồng #{worker_id}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#a1a1aa",
            anchor="w"
        )
        self.lbl_name.pack(fill="x", padx=8, pady=(2, 2))

        # 3. Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, height=6, corner_radius=3)
        self.progress_bar.pack(fill="x", padx=8, pady=2)
        self.progress_bar.set(0.0)

        # 4. Status / Speed label
        self.lbl_status = ctk.CTkLabel(
            self,
            text=t("card_waiting"),
            font=ctk.CTkFont(size=10),
            text_color="#71717a",
            anchor="w"
        )
        self.lbl_status.pack(fill="x", padx=8, pady=(0, 6))

    def set_active_file(self, file_path: Path, percent: float = 0.0, speed: str = ""):
        # Cancel any pending reset timer
        if self._complete_timer:
            try:
                self.after_cancel(self._complete_timer)
            except Exception:
                pass
            self._complete_timer = None

        if self.current_file != file_path:
            self.current_file = file_path
            disp_name = file_path.name
            if len(disp_name) > 16:
                disp_name = disp_name[:11] + "..." + file_path.suffix
            self.lbl_name.configure(text=disp_name, text_color="#f4f4f5")
            self.configure(border_color="#3b82f6", fg_color="#18181b")
            self.lbl_badge.configure(
                text=f"{t('card_thread')} {self.worker_id}",
                fg_color="#1e3a8a",
                text_color="#93c5fd"
            )
            self.progress_bar.configure(progress_color="#3b82f6")
            self.progress_bar.set(percent / 100.0)
            self.lbl_thumb.configure(image="", text="⏳")

            # Asynchronously load thumbnail in thread pool
            _THUMB_EXECUTOR.submit(self._async_load_thumb, file_path)

        # Update progress and speed
        self.progress_bar.set(percent / 100.0)
        txt = f"{percent:.0f}%"
        if speed:
            txt += f" • {speed}"
        elif percent == 0:
            txt = t("card_waiting")
        self.lbl_status.configure(text=txt, text_color="#38bdf8")

    def _async_load_thumb(self, file_path: Path):
        thumb = get_file_thumbnail(file_path, size=(96, 96))
        if thumb and self.current_file == file_path:
            self.after(0, lambda: self._apply_thumb(thumb, file_path))

    def _apply_thumb(self, thumb: ctk.CTkImage, file_path: Path):
        if self.current_file == file_path:
            try:
                self.lbl_thumb.configure(image=thumb, text="")
            except Exception:
                pass

    def set_completed(self, file_path: Path, was_skipped: bool = False):
        if self.current_file != file_path:
            return

        self.progress_bar.set(1.0)
        self.progress_bar.configure(progress_color="#22c55e")
        self.lbl_status.configure(
            text=t("card_uploaded") if not was_skipped else t("card_exists"),
            text_color="#4ade80"
        )
        self.lbl_badge.configure(
            text=t("card_done"),
            fg_color="#14532d",
            text_color="#86efac"
        )
        self.configure(border_color="#22c55e", fg_color="#052e16")

        # After 1.5s, if no new file has been assigned, transition back to standby
        self._complete_timer = self.after(1500, self.set_standby)

    def set_error(self, file_path: Path, error_msg: str):
        if self.current_file != file_path:
            return
        self.progress_bar.configure(progress_color="#ef4444")
        self.lbl_status.configure(text=error_msg[:16], text_color="#ef4444")
        self.lbl_badge.configure(text="LỖI", fg_color="#7f1d1d", text_color="#fca5a5")
        self.configure(border_color="#ef4444", fg_color="#18181b")
        self._complete_timer = self.after(2000, self.set_standby)

    def set_standby(self):
        self._complete_timer = None
        self.current_file = None
        self.configure(border_color="#27272a", fg_color="#18181b")
        self.lbl_name.configure(text=f"Luồng #{self.worker_id}", text_color="#71717a")
        self.lbl_status.configure(text=t("card_waiting"), text_color="#71717a")
        self.lbl_badge.configure(
            text=f"{t('card_thread')} {self.worker_id}",
            fg_color="#27272a",
            text_color="#a1a1aa"
        )
        self.lbl_thumb.configure(image="", text="📷")
        self.progress_bar.set(0.0)
        self.progress_bar.configure(progress_color="#3b82f6")


class ActiveUploadTray(ctk.CTkFrame):
    """
    Container frame that displays the grid/carousel of actively uploading photos.
    Uses fixed worker slots to completely prevent widget overlapping and GUI stutter.
    """
    def __init__(self, parent):
        super().__init__(parent, fg_color="#27272a", corner_radius=10)

        # Header of the tray
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")

        self.lbl_title = ctk.CTkLabel(
            title_box,
            text="Đang sao lưu lên Google Photos (Multi-Threaded)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f4f4f5"
        )
        self.lbl_title.pack(side="left")

        self.lbl_active_threads = ctk.CTkLabel(
            title_box,
            text="4 luồng song song",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#1e3a8a",
            text_color="#93c5fd",
            corner_radius=4,
            padx=6,
            pady=1
        )
        self.lbl_active_threads.pack(side="left", padx=8)

        self.lbl_counter = ctk.CTkLabel(
            header,
            text="0 đang tải • 0 trong hàng đợi",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        )
        self.lbl_counter.pack(side="right")

        # Scrollable container for worker slot cards
        self.cards_scroll = ctk.CTkScrollableFrame(
            self,
            height=215,
            orientation="horizontal",
            fg_color="#18181b",
            corner_radius=8
        )
        self.cards_scroll.pack(fill="x", padx=16, pady=(0, 10))

        # Fixed worker slots: worker_id (1..N) -> WorkerSlotCard
        self.slots: Dict[int, WorkerSlotCard] = {}
        self._current_threads = 4
        self.set_thread_count(4)

    def set_thread_count(self, threads: int):
        self._current_threads = threads
        self.lbl_active_threads.configure(text=f"{threads} luồng song song")

        # Create slots up to target threads
        for wid in range(1, threads + 1):
            if wid not in self.slots:
                card = WorkerSlotCard(self.cards_scroll, worker_id=wid)
                card.pack(side="left", padx=6, pady=6)
                self.slots[wid] = card
            else:
                self.slots[wid].pack(side="left", padx=6, pady=6)

        # Hide extra slots if thread count decreased
        for wid, card in list(self.slots.items()):
            if wid > threads:
                card.pack_forget()

    def add_or_update_file(self, file_path: Path, worker_id: int, percent: float = 0.0, speed: str = ""):
        # Ensure slot exists
        if worker_id not in self.slots:
            card = WorkerSlotCard(self.cards_scroll, worker_id=worker_id)
            card.pack(side="left", padx=6, pady=6)
            self.slots[worker_id] = card

        self.slots[worker_id].set_active_file(file_path, percent, speed)

    def mark_completed(self, file_path: Path, was_skipped: bool = False):
        # Find which slot is handling this file
        for card in self.slots.values():
            if card.current_file == file_path:
                card.set_completed(file_path, was_skipped=was_skipped)
                break

    def mark_error(self, file_path: Path, error_msg: str):
        for card in self.slots.values():
            if card.current_file == file_path:
                card.set_error(file_path, error_msg)
                break

    def clear_all(self):
        for card in self.slots.values():
            card.set_standby()

    def update_counts(self, active_count: int, remaining_queue: int):
        self.lbl_counter.configure(text=f"{active_count} đang tải • {remaining_queue} trong hàng đợi")
