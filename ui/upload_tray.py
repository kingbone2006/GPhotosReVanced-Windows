"""Visual Upload Card and Tray for Google Photos ReVanced Windows.
Emulates Android Google Photos backup carousel with live thumbnails,
progress rings/bars, and smooth completion fade-out animation.
"""

import os
import threading
from pathlib import Path
from typing import Optional, Dict
from PIL import Image, ImageOps
import customtkinter as ctk
from core.i18n import t


# Global thumbnail cache to prevent re-reading images from disk
_THUMB_CACHE: Dict[str, ctk.CTkImage] = {}
_CACHE_LOCK = threading.Lock()


def get_file_thumbnail(file_path: Path, size=(96, 96)) -> Optional[ctk.CTkImage]:
    """Generate or retrieve a cached square thumbnail for image/video files."""
    path_str = str(file_path)
    with _CACHE_LOCK:
        if path_str in _THUMB_CACHE:
            return _THUMB_CACHE[path_str]

    ext = file_path.suffix.lower()
    img = None
    try:
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}:
            with Image.open(file_path) as raw:
                # Correct orientation if EXIF present
                raw = ImageOps.exif_transpose(raw)
                # Crop and resize to square
                img = ImageOps.fit(raw, size, Image.Resampling.LANCZOS)
        elif ext in {".mp4", ".mov", ".mkv", ".avi", ".webm", ".3gp"}:
            # Generate a nice video card placeholder
            img = Image.new("RGB", size, color="#1e293b")
        else:
            # Generic file placeholder
            img = Image.new("RGB", size, color="#334155")
    except Exception:
        img = Image.new("RGB", size, color="#1e293b")

    if img:
        ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
        with _CACHE_LOCK:
            # Keep cache reasonable
            if len(_THUMB_CACHE) > 200:
                _THUMB_CACHE.pop(next(iter(_THUMB_CACHE)))
            _THUMB_CACHE[path_str] = ctk_img
        return ctk_img
    return None


class UploadPhotoCard(ctk.CTkFrame):
    """
    Individual card representing a photo or video being actively uploaded.
    Has thumbnail, progress bar, worker tag, and handles smooth fade-out when uploaded.
    """
    def __init__(self, parent, file_path: Path, worker_id: int = 1, on_removed: Optional[callable] = None):
        super().__init__(
            parent,
            width=135,
            height=185,
            fg_color="#18181b",
            border_color="#27272a",
            border_width=1,
            corner_radius=10
        )
        self.pack_propagate(False)

        self.file_path = file_path
        self.worker_id = worker_id
        self.on_removed = on_removed
        self._is_animating = False

        # 1. Thumbnail Container
        self.thumb_frame = ctk.CTkFrame(self, width=115, height=96, fg_color="#09090b", corner_radius=8)
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
        disp_name = file_path.name
        if len(disp_name) > 16:
            disp_name = disp_name[:11] + "..." + file_path.suffix
        self.lbl_name = ctk.CTkLabel(
            self,
            text=disp_name,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f4f4f5",
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
            text_color="#a1a1aa",
            anchor="w"
        )
        self.lbl_status.pack(fill="x", padx=8, pady=(0, 6))

        # Load thumbnail asynchronously
        threading.Thread(target=self._load_thumbnail, daemon=True).start()

    def _load_thumbnail(self):
        thumb = get_file_thumbnail(self.file_path, size=(96, 96))
        if thumb:
            self.after(0, lambda: self._apply_thumb(thumb))

    def _apply_thumb(self, thumb: ctk.CTkImage):
        try:
            self.lbl_thumb.configure(image=thumb, text="")
        except Exception:
            pass

    def update_progress(self, percent: float, speed: str = ""):
        if self._is_animating:
            return
        self.progress_bar.set(percent / 100.0)
        txt = f"{percent:.0f}%"
        if speed:
            txt += f" • {speed}"
        self.lbl_status.configure(text=txt, text_color="#38bdf8")

    def animate_complete_and_vanish(self, was_skipped: bool = False):
        """
        Triggers the Android Google Photos finish effect:
        Shows checkmark, briefly glows green, shrinks/slides away, and removes itself.
        """
        if self._is_animating:
            return
        self._is_animating = True

        # 1. Show Completion checkmark
        self.progress_bar.set(1.0)
        self.progress_bar.configure(progress_color="#22c55e")
        self.lbl_status.configure(text=t("card_uploaded") if not was_skipped else t("card_exists"), text_color="#4ade80")
        self.lbl_badge.configure(text=t("card_done"), fg_color="#14532d", text_color="#86efac")
        self.configure(border_color="#22c55e", fg_color="#052e16")

        # 2. Wait 400ms so user sees the green checkmark
        self.after(450, self._start_fade_steps)

    def _start_fade_steps(self):
        # Step-by-step collapse and disappearance (mimics Android upload disappearing smoothly)
        fade_colors = ["#064e3b", "#065f46", "#1e293b", "#0f172a", "#020617"]
        
        def step(idx: int):
            if idx < len(fade_colors):
                try:
                    self.configure(fg_color=fade_colors[idx], border_color="#18181b")
                    # Shrink slightly
                    curr_h = self.cget("height")
                    if curr_h > 40:
                        self.configure(height=curr_h - 18)
                    self.after(40, lambda: step(idx + 1))
                except Exception:
                    self._cleanup()
            else:
                self._cleanup()

        step(0)

    def _cleanup(self):
        try:
            if self.on_removed:
                self.on_removed(self.file_path)
            self.destroy()
        except Exception:
            pass


class ActiveUploadTray(ctk.CTkFrame):
    """
    Container frame that displays the grid/carousel of actively uploading photos.
    Manages multi-threaded card slots and gracefully vanishes completed photos.
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

        # Scrollable container for cards
        self.cards_scroll = ctk.CTkScrollableFrame(
            self,
            height=210,
            orientation="horizontal",
            fg_color="#18181b",
            corner_radius=8
        )
        self.cards_scroll.pack(fill="x", padx=16, pady=(0, 10))

        # Placeholder when empty
        self.lbl_empty = ctk.CTkLabel(
            self.cards_scroll,
            text="✨ Tất cả ảnh và video đã được sao lưu an toàn lên Cloud!\nChưa có ảnh nào đang tải lên.",
            font=ctk.CTkFont(size=12),
            text_color="#71717a",
            justify="center",
            height=180
        )
        self.lbl_empty.pack(fill="both", expand=True, padx=20, pady=20)

        # Cards registry: path_str -> UploadPhotoCard
        self._cards: Dict[str, UploadPhotoCard] = {}

    def set_thread_count(self, threads: int):
        self.lbl_active_threads.configure(text=f"{threads} luồng song song")

    def add_or_update_file(self, file_path: Path, worker_id: int, percent: float = 0.0, speed: str = ""):
        path_str = str(file_path)

        # Hide empty placeholder if first card
        if self.lbl_empty.winfo_ismapped():
            self.lbl_empty.pack_forget()

        if path_str not in self._cards:
            card = UploadPhotoCard(
                parent=self.cards_scroll,
                file_path=file_path,
                worker_id=worker_id,
                on_removed=self._on_card_removed
            )
            card.pack(side="left", padx=6, pady=6)
            self._cards[path_str] = card

        self._cards[path_str].update_progress(percent, speed)

    def mark_completed(self, file_path: Path, was_skipped: bool = False):
        path_str = str(file_path)
        if path_str in self._cards:
            self._cards[path_str].animate_complete_and_vanish(was_skipped=was_skipped)

    def mark_error(self, file_path: Path, error_msg: str):
        path_str = str(file_path)
        if path_str in self._cards:
            self._cards[path_str].lbl_status.configure(text="Lỗi tải", text_color="#ef4444")
            self._cards[path_str].progress_bar.configure(progress_color="#ef4444")
            self.after(2000, lambda: self._cards.get(path_str) and self._cards[path_str].animate_complete_and_vanish())

    def clear_all(self):
        for card in list(self._cards.values()):
            try:
                card.destroy()
            except Exception:
                pass
        self._cards.clear()
        self._check_empty()

    def update_counts(self, active_count: int, remaining_queue: int):
        self.lbl_counter.configure(text=f"{active_count} đang tải • {remaining_queue} trong hàng đợi")
        if active_count == 0 and remaining_queue == 0:
            self._check_empty()

    def _on_card_removed(self, file_path: Path):
        path_str = str(file_path)
        self._cards.pop(path_str, None)
        self._check_empty()

    def _check_empty(self):
        if len(self._cards) == 0:
            if not self.lbl_empty.winfo_ismapped():
                self.lbl_empty.pack(fill="both", expand=True, padx=20, pady=20)
