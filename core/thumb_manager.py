"""
Cloud Thumbnail Manager for Google Photos ReVanced.
Handles asynchronous fetching, disk caching, and thread-safe Tkinter CTkImage binding
for album covers and individual media item thumbnails.
"""

import io
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Tuple, Callable, Dict, Any, Set
from PIL import Image
import customtkinter as ctk


class CloudThumbManager:
    """Manages downloading, caching, and binding of thumbnails for cloud media."""

    def __init__(self, cache_dir: Optional[Path] = None, max_workers: int = 4):
        if cache_dir is None:
            app_data = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "GPhotosReVanced"
            cache_dir = app_data / "thumbs"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="CloudThumb")
        self._lock = threading.Lock()
        self._mem_cache: Dict[Tuple[str, int, int], ctk.CTkImage] = {}
        self._pending_keys: Set[str] = set()

    def get_thumbnail(
        self,
        media_key: str,
        size: Tuple[int, int] = (130, 100),
        api_client_provider: Optional[Callable[[], Any]] = None,
        on_loaded: Optional[Callable[[ctk.CTkImage], None]] = None,
        widget_to_bind: Optional[Any] = None
    ) -> Optional[ctk.CTkImage]:
        """
        Retrieves a thumbnail for media_key.
        - If cached in memory, returns immediately.
        - If cached on disk, loads, caches in memory, and returns immediately.
        - If not cached, triggers background download via api_client_provider.
          When ready, updates widget_to_bind and/or calls on_loaded on the Tkinter main thread.
        """
        if not media_key:
            return None

        cache_key = (media_key, size[0], size[1])
        with self._lock:
            if cache_key in self._mem_cache:
                return self._mem_cache[cache_key]

        disk_path = self.cache_dir / f"{media_key}.jpg"
        if disk_path.exists():
            try:
                img = Image.open(disk_path)
                img.load()
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                with self._lock:
                    self._mem_cache[cache_key] = ctk_img
                return ctk_img
            except Exception:
                try:
                    disk_path.unlink(missing_ok=True)
                except Exception:
                    pass

        # If not on disk, schedule download in background
        if api_client_provider is None:
            return None

        with self._lock:
            if media_key in self._pending_keys:
                return None
            self._pending_keys.add(media_key)

        def _bg_fetch():
            try:
                api = api_client_provider()
                if not api or not hasattr(api, "get_thumbnail"):
                    return
                # Request double the display size for sharpness
                w = max(size[0] * 2, 160)
                h = max(size[1] * 2, 120)
                jpeg_bytes = api.get_thumbnail(media_key, width=w, height=h, force_jpeg=True)
                if not jpeg_bytes:
                    return

                # Write to disk cache atomically
                temp_path = disk_path.with_suffix(".tmp")
                with open(temp_path, "wb") as f:
                    f.write(jpeg_bytes)
                temp_path.replace(disk_path)

                # Open PIL Image to verify
                pil_img = Image.open(io.BytesIO(jpeg_bytes))
                pil_img.load()

                def _apply_on_main():
                    try:
                        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
                        with self._lock:
                            self._mem_cache[cache_key] = ctk_img

                        if widget_to_bind is not None:
                            if hasattr(widget_to_bind, "winfo_exists") and widget_to_bind.winfo_exists():
                                widget_to_bind.configure(image=ctk_img, text="")
                                widget_to_bind.image = ctk_img

                        if on_loaded:
                            on_loaded(ctk_img)
                    except Exception:
                        pass

                # Dispatch safely to Tkinter event loop
                if widget_to_bind is not None and hasattr(widget_to_bind, "after"):
                    widget_to_bind.after(0, _apply_on_main)
            except Exception:
                pass
            finally:
                with self._lock:
                    self._pending_keys.discard(media_key)

        self._executor.submit(_bg_fetch)
        return None
