"""Cloud Albums and Photos Explorer for Google Photos ReVanced Windows.
Provides full desktop album management:
- View all photos or albums with cover art and photo counts
- Instant search/filter by album or photo name
- Bulk 'Select All' checkbox
- Download albums to PC into folders named after the album name
- Browse and preview individual photos inside each album
"""

import os
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.db import UploadDatabase
from core.downloader import AlbumDownloader, sanitize_folder_name
from core.i18n import t
from ui.upload_tray import get_file_thumbnail


class AlbumsView(ctk.CTkFrame):
    """
    Main container for Albums & Photos Explorer tab.
    Supports switching between Albums Grid, Photos Grid, and Album Detail view.
    """
    def __init__(self, parent, db: UploadDatabase, config_mgr, get_uploader_func=None):
        super().__init__(parent, fg_color="transparent")
        self.db = db
        self.config_mgr = config_mgr
        self.get_uploader = get_uploader_func

        self._all_albums: List[Dict[str, Any]] = []
        self._filtered_albums: List[Dict[str, Any]] = []
        self._selected_album_names: set = set()
        self._current_viewing_album: Optional[str] = None
        self._downloader: Optional[AlbumDownloader] = None
        self._active_mode = "albums"  # "albums" or "photos"

        # Build UI Structure
        self._build_header()

        # Container for swappable views (Album list vs Photo viewer)
        self.content_container = ctk.CTkFrame(self, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, padx=12, pady=(4, 8))

        # 1. Main Grid Container
        self.albums_scroll = ctk.CTkScrollableFrame(
            self.content_container,
            fg_color="#18181b",
            corner_radius=8
        )
        self.albums_scroll.pack(fill="both", expand=True)

        # 2. Photos Viewer Container (hidden by default)
        self.photos_container = ctk.CTkFrame(self.content_container, fg_color="#18181b", corner_radius=8)
        self._build_photos_viewer_ui()

        # Load initial data
        self.after(300, self.load_albums)

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="#27272a", corner_radius=10)
        self.header_frame.pack(fill="x", padx=12, pady=(8, 4))

        # Top Switcher: Albums vs All Photos
        top_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(8, 2))

        self.seg_view = ctk.CTkSegmentedButton(
            top_row,
            values=["📁 Xem Album", "🖼️ Xem Tất Cả Ảnh"],
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_switch_view_mode
        )
        self.seg_view.pack(side="left")
        self.seg_view.set("📁 Xem Album")

        # Row 2: Search & Controls
        self.controls_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.controls_row.pack(fill="x", padx=12, pady=(4, 10))

        # Search Bar
        self.search_entry = ctk.CTkEntry(
            self.controls_row,
            placeholder_text=t("albums_search_placeholder"),
            width=300,
            height=32,
            font=ctk.CTkFont(size=12)
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search())

        # Select All Checkbox
        self.chk_select_all = ctk.CTkCheckBox(
            self.controls_row,
            text=t("albums_select_all"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_toggle_select_all
        )
        self.chk_select_all.pack(side="left", padx=8)

        # Selected Counter
        self.lbl_selected_counter = ctk.CTkLabel(
            self.controls_row,
            text=t("albums_selected_count", count=0, total=0),
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa"
        )
        self.lbl_selected_counter.pack(side="left", padx=8)

        # Download Selected Button
        self.btn_download_selected = ctk.CTkButton(
            self.controls_row,
            text=t("btn_download_selected_albums", count=0),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._download_selected_albums
        )
        self.btn_download_selected.pack(side="right", padx=(6, 0))

        # Refresh Button
        self.btn_refresh = ctk.CTkButton(
            self.controls_row,
            text=t("btn_refresh_albums"),
            fg_color="#3f3f46",
            hover_color="#52525b",
            width=80,
            height=32,
            command=self.load_albums
        )
        self.btn_refresh.pack(side="right", padx=6)

    def _on_switch_view_mode(self, mode: str):
        if "Ảnh" in mode:
            self._active_mode = "photos"
            self.chk_select_all.pack_forget()
            self.lbl_selected_counter.pack_forget()
            self.btn_download_selected.pack_forget()
            self.search_entry.configure(placeholder_text="🔍 Tìm ảnh theo tên file...")
            self._render_all_photos_grid()
        else:
            self._active_mode = "albums"
            self.chk_select_all.pack(side="left", padx=8)
            self.lbl_selected_counter.pack(side="left", padx=8)
            self.btn_download_selected.pack(side="right", padx=(6, 0))
            self.search_entry.configure(placeholder_text=t("albums_search_placeholder"))
            self._render_album_grid()

    def _build_photos_viewer_ui(self):
        """Header and scroll area for viewing photos inside an album."""
        p_header = ctk.CTkFrame(self.photos_container, fg_color="#27272a", corner_radius=8)
        p_header.pack(fill="x", padx=12, pady=10)

        self.btn_back = ctk.CTkButton(
            p_header,
            text=t("btn_back_to_albums"),
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#3f3f46",
            hover_color="#52525b",
            width=150,
            height=30,
            command=self._show_albums_view
        )
        self.btn_back.pack(side="left", padx=10, pady=8)

        self.lbl_viewing_album_title = ctk.CTkLabel(
            p_header,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f4f4f5"
        )
        self.lbl_viewing_album_title.pack(side="left", padx=12)

        self.btn_download_this = ctk.CTkButton(
            p_header,
            text=t("btn_download_this_album"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._download_current_album
        )
        self.btn_download_this.pack(side="right", padx=10, pady=8)

        # Scroll area for photos
        self.photos_scroll = ctk.CTkScrollableFrame(
            self.photos_container,
            fg_color="#18181b",
            corner_radius=8
        )
        self.photos_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    def load_albums(self):
        """Load all albums from database and refresh grid."""
        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""
        self._all_albums = self.db.get_all_albums(email)
        self._on_search()

    def _on_search(self):
        if self._active_mode == "photos":
            self._render_all_photos_grid()
            return

        query = self.search_entry.get().strip().lower()
        if not query:
            self._filtered_albums = list(self._all_albums)
        else:
            self._filtered_albums = [
                a for a in self._all_albums if query in a.get("album_name", "").lower()
            ]
        self._render_album_grid()

    def _render_album_grid(self):
        for widget in self.albums_scroll.winfo_children():
            widget.destroy()

        total = len(self._all_albums)
        sel = len(self._selected_album_names)
        self.lbl_selected_counter.configure(
            text=t("albums_selected_count", count=sel, total=total)
        )
        self.btn_download_selected.configure(
            text=t("btn_download_selected_albums", count=sel)
        )

        if not self._filtered_albums:
            lbl_empty = ctk.CTkLabel(
                self.albums_scroll,
                text=t("albums_empty"),
                font=ctk.CTkFont(size=13),
                text_color="#71717a",
                justify="center"
            )
            lbl_empty.pack(expand=True, pady=60)
            return

        cols = 3
        for idx, album in enumerate(self._filtered_albums):
            album_name = album.get("album_name", "Untitled")
            photo_count = album.get("photo_count", 0)
            cover_path = album.get("cover_path", "")

            row = idx // cols
            col = idx % cols

            card = ctk.CTkFrame(self.albums_scroll, fg_color="#27272a", corner_radius=10)
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.albums_scroll.grid_columnconfigure(col, weight=1)

            top_bar = ctk.CTkFrame(card, fg_color="transparent")
            top_bar.pack(fill="x", padx=10, pady=(10, 4))

            is_sel = album_name in self._selected_album_names
            chk = ctk.CTkCheckBox(
                top_bar,
                text="",
                width=24,
                command=lambda name=album_name: self._toggle_album_selection(name)
            )
            if is_sel:
                chk.select()
            chk.pack(side="left")

            disp_name = album_name if len(album_name) <= 22 else album_name[:19] + "..."
            lbl_title = ctk.CTkLabel(
                top_bar,
                text=disp_name,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#f4f4f5",
                anchor="w",
                cursor="hand2"
            )
            lbl_title.pack(side="left", fill="x", expand=True, padx=4)
            lbl_title.bind("<Button-1>", lambda e, name=album_name: self._open_album_photos(name))

            thumb_box = ctk.CTkFrame(card, height=110, fg_color="#18181b", corner_radius=8)
            thumb_box.pack(fill="x", padx=10, pady=4)
            thumb_box.pack_propagate(False)

            lbl_cover = ctk.CTkLabel(thumb_box, text="📁", font=ctk.CTkFont(size=36), cursor="hand2")
            lbl_cover.place(relx=0.5, rely=0.5, anchor="center")
            lbl_cover.bind("<Button-1>", lambda e, name=album_name: self._open_album_photos(name))

            if cover_path and Path(cover_path).exists():
                thumb = get_file_thumbnail(Path(cover_path), size=(130, 100))
                if thumb:
                    lbl_cover.configure(image=thumb, text="")

            bottom_bar = ctk.CTkFrame(card, fg_color="transparent")
            bottom_bar.pack(fill="x", padx=10, pady=(4, 10))

            lbl_cnt = ctk.CTkLabel(
                bottom_bar,
                text=t("album_photos_count", count=photo_count),
                font=ctk.CTkFont(size=11),
                text_color="#38bdf8"
            )
            lbl_cnt.pack(side="left")

            btn_view = ctk.CTkButton(
                bottom_bar,
                text=t("btn_view_photos"),
                font=ctk.CTkFont(size=11),
                width=75,
                height=24,
                fg_color="#3f3f46",
                hover_color="#52525b",
                command=lambda name=album_name: self._open_album_photos(name)
            )
            btn_view.pack(side="right", padx=(4, 0))

            btn_dl = ctk.CTkButton(
                bottom_bar,
                text=t("btn_download_album"),
                font=ctk.CTkFont(size=11),
                width=65,
                height=24,
                fg_color="#2563eb",
                hover_color="#1d4ed8",
                command=lambda name=album_name: self._download_single_album(name)
            )
            btn_dl.pack(side="right")

    def _render_all_photos_grid(self):
        """Render all backed-up photos in a responsive gallery stream."""
        for widget in self.albums_scroll.winfo_children():
            widget.destroy()

        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""
        photos = self.db.get_all_photos(email)

        query = self.search_entry.get().strip().lower()
        if query:
            photos = [p for p in photos if query in p.get("filename", "").lower()]

        if not photos:
            lbl_empty = ctk.CTkLabel(
                self.albums_scroll,
                text="Chưa có ảnh nào được sao lưu.",
                font=ctk.CTkFont(size=13),
                text_color="#71717a"
            )
            lbl_empty.pack(expand=True, pady=60)
            return

        cols = 4
        for idx, photo in enumerate(photos):
            filename = photo.get("filename", "photo.jpg")
            local_path = photo.get("local_path", "")
            fsize = photo.get("file_size", 0)
            mb = fsize / (1024 * 1024)

            row = idx // cols
            col = idx % cols

            p_card = ctk.CTkFrame(self.albums_scroll, fg_color="#27272a", corner_radius=8)
            p_card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            self.albums_scroll.grid_columnconfigure(col, weight=1)

            t_box = ctk.CTkFrame(p_card, height=110, fg_color="#18181b", corner_radius=6)
            t_box.pack(fill="x", padx=6, pady=(6, 2))
            t_box.pack_propagate(False)

            lbl_img = ctk.CTkLabel(t_box, text="📷", font=ctk.CTkFont(size=24), cursor="hand2")
            lbl_img.place(relx=0.5, rely=0.5, anchor="center")

            if local_path and Path(local_path).exists():
                lbl_img.bind("<Double-Button-1>", lambda e, p=local_path: self._open_file_system(p))
                t_img = get_file_thumbnail(Path(local_path), size=(120, 100))
                if t_img:
                    lbl_img.configure(image=t_img, text="")

            disp_fname = filename if len(filename) <= 18 else filename[:14] + "..." + Path(filename).suffix
            ctk.CTkLabel(
                p_card,
                text=disp_fname,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#f4f4f5",
                anchor="w"
            ).pack(fill="x", padx=6, pady=(2, 0))

            ctk.CTkLabel(
                p_card,
                text=f"{mb:.1f} MB",
                font=ctk.CTkFont(size=9),
                text_color="#9ca3af",
                anchor="w"
            ).pack(fill="x", padx=6, pady=(0, 6))

    def _toggle_album_selection(self, album_name: str):
        if album_name in self._selected_album_names:
            self._selected_album_names.remove(album_name)
        else:
            self._selected_album_names.add(album_name)

        sel = len(self._selected_album_names)
        total = len(self._all_albums)
        self.lbl_selected_counter.configure(
            text=t("albums_selected_count", count=sel, total=total)
        )
        self.btn_download_selected.configure(
            text=t("btn_download_selected_albums", count=sel)
        )

    def _on_toggle_select_all(self):
        val = self.chk_select_all.get()
        if val:
            for a in self._filtered_albums:
                self._selected_album_names.add(a.get("album_name"))
        else:
            for a in self._filtered_albums:
                self._selected_album_names.discard(a.get("album_name"))

        self._render_album_grid()

    # =========================================================================
    # Album Detail Photos View Mode
    # =========================================================================
    def _open_album_photos(self, album_name: str):
        self._current_viewing_album = album_name
        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""
        photos = self.db.get_album_photos(album_name, email)

        self.albums_scroll.pack_forget()
        self.photos_container.pack(fill="both", expand=True)

        self.lbl_viewing_album_title.configure(
            text=f"📁 {album_name} ({len(photos)} ảnh)"
        )

        for widget in self.photos_scroll.winfo_children():
            widget.destroy()

        if not photos:
            lbl_empty = ctk.CTkLabel(
                self.photos_scroll,
                text="Chưa có ảnh nào trong album này.",
                font=ctk.CTkFont(size=13),
                text_color="#71717a"
            )
            lbl_empty.pack(expand=True, pady=40)
            return

        cols = 4
        for idx, photo in enumerate(photos):
            filename = photo.get("filename", "photo.jpg")
            local_path = photo.get("local_path", "")
            fsize = photo.get("file_size", 0)
            mb = fsize / (1024 * 1024)

            row = idx // cols
            col = idx % cols

            p_card = ctk.CTkFrame(self.photos_scroll, fg_color="#27272a", corner_radius=8)
            p_card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            self.photos_scroll.grid_columnconfigure(col, weight=1)

            t_box = ctk.CTkFrame(p_card, height=110, fg_color="#18181b", corner_radius=6)
            t_box.pack(fill="x", padx=6, pady=(6, 2))
            t_box.pack_propagate(False)

            lbl_img = ctk.CTkLabel(t_box, text="📷", font=ctk.CTkFont(size=24), cursor="hand2")
            lbl_img.place(relx=0.5, rely=0.5, anchor="center")

            if local_path and Path(local_path).exists():
                lbl_img.bind("<Double-Button-1>", lambda e, p=local_path: self._open_file_system(p))
                t_img = get_file_thumbnail(Path(local_path), size=(120, 100))
                if t_img:
                    lbl_img.configure(image=t_img, text="")

            disp_fname = filename if len(filename) <= 18 else filename[:14] + "..." + Path(filename).suffix
            ctk.CTkLabel(
                p_card,
                text=disp_fname,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#f4f4f5",
                anchor="w"
            ).pack(fill="x", padx=6, pady=(2, 0))

            ctk.CTkLabel(
                p_card,
                text=f"{mb:.1f} MB",
                font=ctk.CTkFont(size=9),
                text_color="#9ca3af",
                anchor="w"
            ).pack(fill="x", padx=6, pady=(0, 6))

    def _open_file_system(self, file_path: str):
        try:
            os.startfile(file_path)
        except Exception:
            pass

    def _show_albums_view(self):
        self.photos_container.pack_forget()
        self.albums_scroll.pack(fill="both", expand=True)
        self._current_viewing_album = None

    # =========================================================================
    # Downloading Albums
    # =========================================================================
    def _download_single_album(self, album_name: str):
        self._run_download_albums([album_name])

    def _download_current_album(self):
        if self._current_viewing_album:
            self._run_download_albums([self._current_viewing_album])

    def _download_selected_albums(self):
        if not self._selected_album_names:
            messagebox.showinfo(t("alert_info"), "Vui lòng tích chọn ít nhất 1 album để tải về.", parent=self)
            return
        self._run_download_albums(list(self._selected_album_names))

    def _run_download_albums(self, album_names: List[str]):
        dest = filedialog.askdirectory(title=t("dialog_select_download_dir"))
        if not dest:
            return

        dest_root = Path(dest)
        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""

        payload = []
        for name in album_names:
            photos = self.db.get_album_photos(name, email)
            payload.append({
                "album_name": name,
                "items": photos
            })

        api_client = None
        if self.get_uploader:
            uploader = self.get_uploader()
            if uploader and uploader._client:
                api_client = uploader._client.api

        dlg = DownloadProgressDialog(self.winfo_toplevel(), album_names, dest_root)

        downloader = AlbumDownloader(api=api_client)
        self._downloader = downloader

        def run():
            try:
                res = downloader.download_albums(
                    albums=payload,
                    destination_root=dest_root,
                    progress_callback=dlg.update_progress
                )
                self.after(0, lambda: dlg.on_finished(res))
            except Exception as e:
                self.after(0, lambda: dlg.on_error(str(e)))

        threading.Thread(target=run, daemon=True).start()


class DownloadProgressDialog(ctk.CTkToplevel):
    """Modal dialog displaying live multi-album download progress."""
    def __init__(self, parent, album_names: List[str], dest_dir: Path):
        super().__init__(parent)
        self.dest_dir = dest_dir
        self.title(t("downloading_album_title"))
        self.geometry("520x240")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(
            self,
            text=f"📥 Đang tải {len(album_names)} album về máy",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        ).pack(padx=20, pady=(18, 6), anchor="w")

        self.lbl_status = ctk.CTkLabel(
            self,
            text="Đang chuẩn bị danh sách ảnh...",
            font=ctk.CTkFont(size=12),
            text_color="#e4e4e7",
            anchor="w"
        )
        self.lbl_status.pack(fill="x", padx=20, pady=(2, 8))

        self.progress_bar = ctk.CTkProgressBar(self, height=12, corner_radius=6)
        self.progress_bar.pack(fill="x", padx=20, pady=8)
        self.progress_bar.set(0)

        self.lbl_detail = ctk.CTkLabel(
            self,
            text=f"Lưu vào: {dest_dir}",
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa",
            anchor="w"
        )
        self.lbl_detail.pack(fill="x", padx=20, pady=4)

        self.btn_open_folder = ctk.CTkButton(
            self,
            text="Mở thư mục",
            command=self._open_folder,
            fg_color="#15803d",
            hover_color="#166534"
        )

    def update_progress(self, data: dict):
        curr_alb = data.get("current_album", "")
        curr_file = data.get("current_file", "")
        done = data.get("completed_files", 0)
        total = data.get("total_files", 1)
        pct = data.get("percent", 0.0)
        speed = data.get("speed", "")

        txt = f"[{done}/{total}] {curr_alb} > {curr_file}"
        if speed:
            txt += f" ({speed})"

        self.progress_bar.set(pct)
        self.lbl_status.configure(text=txt)

    def on_finished(self, res: dict):
        self.progress_bar.set(1.0)
        cnt = res.get("files_count", 0)
        albs = res.get("albums_count", 0)
        dest = res.get("destination", "")

        self.lbl_status.configure(
            text=f"✅ Hoàn tất! Đã lưu {albs} album ({cnt} ảnh) an toàn vào máy.",
            text_color="#4ade80"
        )
        self.btn_open_folder.pack(pady=10)

    def on_error(self, err_msg: str):
        self.lbl_status.configure(
            text=f"❌ Lỗi: {err_msg}",
            text_color="#ef4444"
        )

    def _open_folder(self):
        try:
            os.startfile(self.dest_dir)
        except Exception:
            pass
        self.destroy()
