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
from core.thumb_manager import CloudThumbManager
from ui.upload_tray import get_file_thumbnail


MAX_ALBUMS_PER_PAGE = 30   # Render at most 30 album cards at once to prevent UI freeze
MAX_PHOTOS_PER_PAGE = 60   # Render at most 60 photo cards at once


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

        self._cloud_thumb_mgr = CloudThumbManager()
        self._all_albums: List[Dict[str, Any]] = []
        self._filtered_albums: List[Dict[str, Any]] = []
        self._selected_album_names: set = set()
        self._current_viewing_album: Optional[str] = None
        self._downloader: Optional[AlbumDownloader] = None
        self._active_mode = "albums"  # "albums" or "photos"
        self._albums_page = 0    # Current page for lazy-loaded album grid
        self._photos_page = 0    # Current page for lazy-loaded photos grid
        self._all_photos_list: List[Dict[str, Any]] = []
        self._album_photos_list: List[Dict[str, Any]] = []
        self._album_photos_page = 0
        self._is_loading_more = False
        self._is_syncing_album = False

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

        # Infinite Scroll Hooks for albums & photos
        self._setup_infinite_scroll()

        # Load initial data (deferred to let engine init first)
        self.after(1500, self.load_albums)

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
            width=230,
            height=32,
            font=ctk.CTkFont(size=12)
        )
        self.search_entry.pack(side="left", padx=(0, 6))
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search())

        # Album Filter (Tất cả / Có ảnh / Trống)
        self.filter_album_type = ctk.CTkSegmentedButton(
            self.controls_row,
            values=[t("filter_all_albums"), t("filter_with_photos"), t("filter_empty_albums")],
            font=ctk.CTkFont(size=11),
            command=lambda v: self._on_search()
        )
        self.filter_album_type.pack(side="left", padx=(0, 8))
        self.filter_album_type.set(t("filter_all_albums"))

        # Select All Checkbox
        self.chk_select_all = ctk.CTkCheckBox(
            self.controls_row,
            text=t("albums_select_all"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_toggle_select_all
        )
        self.chk_select_all.pack(side="left", padx=6)

        # Selected Counter
        self.lbl_selected_counter = ctk.CTkLabel(
            self.controls_row,
            text=t("albums_selected_count", count=0, total=0),
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa"
        )
        self.lbl_selected_counter.pack(side="left", padx=6)

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
            width=75,
            height=32,
            command=self.load_albums
        )
        self.btn_refresh.pack(side="right", padx=4)

        # Clean Empty Albums Button
        self.btn_clean_empty = ctk.CTkButton(
            self.controls_row,
            text=t("btn_clean_empty_albums"),
            fg_color="#e11d48",
            hover_color="#be123c",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_clean_empty_albums
        )
        self.btn_clean_empty.pack(side="right", padx=4)

        # Reconcile & Fill Missing Photos to Albums Button
        self.btn_sync_missing = ctk.CTkButton(
            self.controls_row,
            text=t("btn_sync_missing_albums"),
            fg_color="#d97706",
            hover_color="#b45309",
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._on_sync_missing_photos_to_albums
        )
        self.btn_sync_missing.pack(side="right", padx=4)

    def _on_switch_view_mode(self, mode: str):
        if "Ảnh" in mode:
            self._active_mode = "photos"
            self.filter_album_type.pack_forget()
            self.chk_select_all.pack_forget()
            self.lbl_selected_counter.pack_forget()
            self.btn_download_selected.pack_forget()
            self.btn_clean_empty.pack_forget()
            self.btn_sync_missing.pack_forget()
            self.search_entry.configure(placeholder_text="🔍 Tìm ảnh theo tên file...")
            self._render_all_photos_grid()
        else:
            self._active_mode = "albums"
            self.filter_album_type.pack(side="left", padx=(0, 8), after=self.search_entry)
            self.chk_select_all.pack(side="left", padx=6)
            self.lbl_selected_counter.pack(side="left", padx=6)
            self.btn_download_selected.pack(side="right", padx=(6, 0))
            self.btn_refresh.pack(side="right", padx=4)
            self.btn_clean_empty.pack(side="right", padx=4)
            self.btn_sync_missing.pack(side="right", padx=4)
            self.search_entry.configure(placeholder_text=t("albums_search_placeholder"))
            self._render_album_grid()

    def _on_sync_missing_photos_to_albums(self):
        uploader = self.get_uploader() if self.get_uploader else None
        if not uploader:
            messagebox.showwarning(t("alert_warning"), "Engine chưa sẵn sàng hoặc chưa kết nối tài khoản.")
            return

        self.btn_sync_missing.configure(state="disabled", text=t("btn_sync_missing_albums_scanning"))

        def _bg_check():
            try:
                from core.uploader import reconcile_album_photos
                active_acc = self.config_mgr.get_active_account()
                email = active_acc.get("email", "") if active_acc else ""
                sync_folders = self.config_mgr.config.get("sync_folders", [])

                # 1. Sync remote albums to ensure we know all existing cloud albums
                cloud_albums = uploader.sync_cloud_albums(force=True)

                discrepancies, missing_to_upload, already_uploaded_needing_album = reconcile_album_photos(
                    scan_roots=sync_folders,
                    db=self.db,
                    account_email=email,
                    api=uploader._client.api if getattr(uploader, "_client", None) else None,
                    cloud_albums=cloud_albums
                )

                def _on_result():
                    self.btn_sync_missing.configure(state="normal", text=t("btn_sync_missing_albums"))
                    total_missing = len(missing_to_upload) + len(already_uploaded_needing_album)

                    if not discrepancies or total_missing == 0:
                        messagebox.showinfo(
                            t("alert_info"),
                            "✅ Tuyệt vời! Tất cả Album trên Server Google Photos đều đã đồng bộ đủ ảnh và video giống hệt như các thư mục trên máy tính."
                        )
                        return

                    existing_count = sum(1 for d in discrepancies if d.get("album_exists_on_cloud"))
                    new_count = len(discrepancies) - existing_count
                    missing_upload_vids = sum(d.get("missing_upload_videos", 0) for d in discrepancies)
                    missing_upload_photos = len(missing_to_upload) - missing_upload_vids

                    confirm = messagebox.askyesno(
                        "Phát hiện Album cần đồng bộ",
                        f"Phát hiện {len(discrepancies)} album cần xử lý trên Server Google Photos (thiếu tổng cộng {total_missing:,} file ảnh & video so với máy tính):\n\n"
                        f"• {existing_count} Album ĐÃ CÓ trên Server: sẽ được THÊM TIẾP file thiếu vào (tuyệt đối không tạo trùng)\n"
                        f"• {new_count} Album MỚI: chưa có trên Server, sẽ tự động tạo album mới\n"
                        f"• {len(missing_to_upload):,} file cần tải lên mới: gồm {missing_upload_photos:,} ảnh và {missing_upload_vids:,} video\n"
                        f"• {len(already_uploaded_needing_album):,} file đã có trên Cloud sẽ gom bù ngay vào đúng Album\n\n"
                        f"Bạn có muốn bắt đầu tự động tải lên và bù toàn bộ ảnh & video vào các Album này ngay bây giờ không?"
                    )

                    if confirm:
                        # Ensure uploader is unpaused so background workers immediately process
                        uploader.resume()

                        # Notify main window to update button state
                        try:
                            mw = self.winfo_toplevel()
                            if mw and hasattr(mw, "_is_paused"):
                                mw._is_paused = False
                                if hasattr(mw, "btn_pause"):
                                    mw.btn_pause.configure(text=t("btn_pause"), fg_color="#d97706", hover_color="#b45309")
                                if hasattr(mw, "lbl_stat_status"):
                                    mw.lbl_stat_status.configure(text=t("status_monitoring"), text_color="#4ade80")
                        except Exception:
                            pass

                        # 1. For media already on cloud, queue into album flusher with force=True
                        for alb_name, m_key in already_uploaded_needing_album:
                            uploader._queue_for_album(alb_name, m_key, force=True)

                        # 2. For media needing upload, queue to uploader
                        if missing_to_upload:
                            added = uploader.add_to_queue(missing_to_upload)
                            uploader.start_background_worker()
                            uploader._log(
                                f"🚀 [Đồng bộ Album] Đã đưa {added:,} file thiếu ({missing_upload_photos:,} ảnh, {missing_upload_vids:,} video) của {len(discrepancies)} album vào hàng đợi tải lên đa luồng!",
                                "SUCCESS"
                            )
                        else:
                            uploader._start_album_flusher()

                        messagebox.showinfo(
                            t("alert_info"),
                            f"Đã bắt đầu tiến trình bù {total_missing:,} ảnh & video cho {len(discrepancies)} album!\nTheo dõi tiến độ tại tab Dashboard."
                        )

                self.after(0, _on_result)

            except Exception as e:
                def _on_err():
                    self.btn_sync_missing.configure(state="normal", text=t("btn_sync_missing_albums"))
                    messagebox.showerror(t("alert_error"), f"Lỗi khi kiểm tra đồng bộ album:\n{e}")
                self.after(0, _on_err)

        threading.Thread(target=_bg_check, daemon=True).start()

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

        self.btn_delete_this = ctk.CTkButton(
            p_header,
            text=t("btn_delete_album_app"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._delete_current_viewing_album
        )
        self.btn_delete_this.pack(side="right", padx=(4, 10), pady=8)

        self.btn_download_this = ctk.CTkButton(
            p_header,
            text=t("btn_download_this_album"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._download_current_album
        )
        self.btn_download_this.pack(side="right", padx=(4, 4), pady=8)

        self.btn_sync_this = ctk.CTkButton(
            p_header,
            text="🔄 Đồng bộ từ Cloud",
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=30,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._manual_sync_current_album
        )
        self.btn_sync_this.pack(side="right", padx=(4, 4), pady=8)

        self.lbl_sync_status = ctk.CTkLabel(
            p_header,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#38bdf8"
        )
        self.lbl_sync_status.pack(side="right", padx=8)

        # Scroll area for photos
        self.photos_scroll = ctk.CTkScrollableFrame(
            self.photos_container,
            fg_color="#18181b",
            corner_radius=8
        )
        self.photos_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 10))

    def _setup_infinite_scroll(self):
        """Hook into canvas scroll events to automatically load more content ahead of reaching the bottom."""
        try:
            # 1. Main container (Albums or All Photos stream)
            orig_set_albums = self.albums_scroll._scrollbar.set
            def _on_albums_scroll(first, last):
                orig_set_albums(first, last)
                try:
                    # Trigger proactive pre-loading when scrollbar reaches >= 75%
                    if float(last) >= 0.75:
                        self._check_auto_load_more()
                except Exception:
                    pass

            self.albums_scroll._parent_canvas.configure(yscrollcommand=_on_albums_scroll)

            # 2. Photos container (inside Album Detail view)
            orig_set_photos = self.photos_scroll._scrollbar.set
            def _on_photos_scroll(first, last):
                orig_set_photos(first, last)
                try:
                    if float(last) >= 0.75:
                        self._check_auto_load_more_album_photos()
                except Exception:
                    pass

            self.photos_scroll._parent_canvas.configure(yscrollcommand=_on_photos_scroll)
        except Exception:
            pass

    def _check_auto_load_more(self):
        """Automatically load the next batch of albums or photos when scrolling."""
        if self._is_loading_more:
            return

        if self._active_mode == "albums":
            start = self._albums_page * MAX_ALBUMS_PER_PAGE
            end = min(start + MAX_ALBUMS_PER_PAGE, len(self._filtered_albums))
            if end < len(self._filtered_albums):
                self._is_loading_more = True
                self._albums_page += 1
                self._render_album_page()
                self.after(300, lambda: setattr(self, '_is_loading_more', False))

        elif self._active_mode == "photos":
            start = self._photos_page * MAX_PHOTOS_PER_PAGE
            end = min(start + MAX_PHOTOS_PER_PAGE, len(self._all_photos_list))
            if end < len(self._all_photos_list):
                self._is_loading_more = True
                self._photos_page += 1
                self._render_photos_page()
                self.after(300, lambda: setattr(self, '_is_loading_more', False))

    def _check_auto_load_more_album_photos(self):
        """Automatically load the next batch of photos in the album detail view."""
        if self._is_loading_more:
            return

        start = self._album_photos_page * MAX_PHOTOS_PER_PAGE
        end = min(start + MAX_PHOTOS_PER_PAGE, len(self._album_photos_list))
        if end < len(self._album_photos_list):
            self._is_loading_more = True
            self._album_photos_page += 1
            self._render_album_detail_photos_page()
            self.after(300, lambda: setattr(self, '_is_loading_more', False))

    def load_albums(self):
        """Load all albums from database immediately (<5ms) and refresh grid, then sync cloud in background."""
        import threading
        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""
        sync_folders = self.config_mgr.config.get("sync_folders", []) if self.config_mgr else []

        # 1. Immediate render from local SQLite: 0ms delay!
        self._all_albums = self.db.get_all_albums(email, sync_roots=sync_folders)
        self._on_search()

        # 2. Background sync to fetch any newly created cloud albums
        def _bg_load():
            uploader = self.get_uploader() if self.get_uploader else None
            if uploader and hasattr(uploader, "sync_cloud_albums"):
                try:
                    uploader.sync_cloud_albums(max_pages=0)
                    refreshed = self.db.get_all_albums(email, sync_roots=sync_folders)
                    def _update_ui():
                        if self._all_albums != refreshed:
                            self._all_albums = refreshed
                            self._on_search()
                    self.after(0, _update_ui)
                except Exception:
                    pass

        threading.Thread(target=_bg_load, daemon=True).start()

    def _on_search(self):
        if self._active_mode == "photos":
            self._render_all_photos_grid()
            return

        query = self.search_entry.get().strip().lower()
        flt = getattr(self, "filter_album_type", None)
        flt_val = flt.get() if flt else ""

        filtered = list(self._all_albums)

        # Filter by category: All, Has Photos, or Empty
        if flt_val == t("filter_with_photos") or "Có ảnh" in flt_val or "With" in flt_val:
            filtered = [a for a in filtered if a.get("photo_count", 0) > 0]
        elif flt_val == t("filter_empty_albums") or "Trống" in flt_val or "Empty" in flt_val:
            filtered = [a for a in filtered if a.get("photo_count", 0) <= 0]

        # Search query by name
        if query:
            filtered = [a for a in filtered if query in a.get("album_name", "").lower()]

        self._filtered_albums = filtered
        self._render_album_grid()

    def _on_clean_empty_albums(self):
        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""

        empty_albums = [a for a in self._all_albums if a.get("photo_count", 0) <= 0]
        if not empty_albums:
            messagebox.showinfo(
                "Dọn dẹp Album",
                "✅ Tuyệt vời! Thư viện hiện không có bất kỳ Album trống (0 ảnh) nào."
            )
            return

        preview_lines = "\n".join([f"• {a.get('album_name', 'Unnamed')}" for a in empty_albums[:10]])
        if len(empty_albums) > 10:
            preview_lines += f"\n... và {len(empty_albums) - 10} album rỗng khác."

        confirm = messagebox.askyesno(
            "Xác nhận Dọn dẹp Album trống",
            f"Phát hiện {len(empty_albums)} album rỗng (0 ảnh) không chứa dữ liệu:\n\n"
            f"{preview_lines}\n\n"
            f"Bạn có muốn xoá và dọn dẹp toàn bộ {len(empty_albums)} album rỗng này khỏi ứng dụng không?\n\n"
            f"• Các album rỗng sẽ bị xoá khỏi danh sách quản lý\n"
            f"• Ứng dụng sẽ tự động bỏ qua để không bao giờ tải lại các vỏ rỗng này."
        )

        if not confirm:
            return

        cleaned_names = self.db.clean_empty_albums(email)
        for name in cleaned_names:
            self._selected_album_names.discard(name)

        uploader = self.get_uploader() if self.get_uploader else None
        if uploader and hasattr(uploader, "_cloud_albums_cache"):
            for name in cleaned_names:
                uploader._cloud_albums_cache.pop(name, None)

        self.load_albums()

        open_web = messagebox.askyesno(
            "Dọn dẹp hoàn tất",
            f"✅ Đã dọn dẹp thành công {len(cleaned_names)} album rỗng khỏi ứng dụng!\n\n"
            f"💡 Lưu ý: Trên máy chủ Google Photos, các vỏ album rỗng (0 ảnh) được Google lưu lại theo quy định của họ.\n\n"
            f"Bạn có muốn mở trang Web photos.google.com/albums để kiểm tra hoặc xoá hẳn vỏ rỗng trên Cloud không?"
        )
        if open_web:
            import webbrowser
            webbrowser.open("https://photos.google.com/albums")

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

        # Reset page and render first page
        self._albums_page = 0
        self._render_album_page()

    def _render_album_page(self):
        """Render the next page of albums (MAX_ALBUMS_PER_PAGE at a time)."""
        start = self._albums_page * MAX_ALBUMS_PER_PAGE
        end = min(start + MAX_ALBUMS_PER_PAGE, len(self._filtered_albums))
        page_albums = self._filtered_albums[start:end]

        if not page_albums:
            return

        # Remove existing "Load More" button if present
        for widget in self.albums_scroll.winfo_children():
            if hasattr(widget, '_is_load_more_btn'):
                widget.destroy()

        cols = 3
        for idx_in_page, album in enumerate(page_albums):
            idx = start + idx_in_page
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

            btn_card_del = ctk.CTkButton(
                top_bar,
                text="✕",
                width=22,
                height=22,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="transparent",
                hover_color="#ef4444",
                text_color="#71717a",
                command=lambda name=album_name: self._confirm_delete_album(name)
            )
            btn_card_del.pack(side="right")

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
            elif album.get("cover_media_key"):
                cover_key = album.get("cover_media_key")
                c_thumb = self._cloud_thumb_mgr.get_thumbnail(
                    media_key=cover_key,
                    size=(130, 100),
                    api_client_provider=self._get_api_client,
                    widget_to_bind=lbl_cover
                )
                if c_thumb:
                    lbl_cover.configure(image=c_thumb, text="")
                    lbl_cover.image = c_thumb

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

        # Add status indicator / auto-load hook if there are more albums to show
        remaining = len(self._filtered_albums) - end
        next_row = (end // cols) + 1
        if remaining > 0:
            load_more = ctk.CTkButton(
                self.albums_scroll,
                text=f"⏳ Tự động tải thêm khi cuộn... (còn {remaining} album, bấm để tải ngay)",
                fg_color="#27272a",
                hover_color="#3f3f46",
                text_color="#9ca3af",
                font=ctk.CTkFont(size=11),
                height=32,
                command=self._load_more_albums
            )
            load_more._is_load_more_btn = True
            load_more.grid(row=next_row, column=0, columnspan=cols, padx=8, pady=10, sticky="ew")
        elif len(self._filtered_albums) > MAX_ALBUMS_PER_PAGE:
            end_lbl = ctk.CTkLabel(
                self.albums_scroll,
                text=f"✅ Đã hiển thị toàn bộ {len(self._filtered_albums)} album",
                font=ctk.CTkFont(size=11),
                text_color="#71717a"
            )
            end_lbl._is_load_more_btn = True
            end_lbl.grid(row=next_row, column=0, columnspan=cols, padx=8, pady=10, sticky="ew")

    def _load_more_albums(self):
        """Load the next page of albums."""
        self._check_auto_load_more()

    def _render_all_photos_grid(self):
        """Render all backed-up photos in a responsive gallery stream with pagination."""
        for widget in self.albums_scroll.winfo_children():
            widget.destroy()

        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""
        photos = self.db.get_all_photos(email)

        query = self.search_entry.get().strip().lower()
        if query:
            photos = [p for p in photos if query in p.get("filename", "").lower()]

        self._all_photos_list = photos
        self._photos_page = 0

        if not photos:
            lbl_empty = ctk.CTkLabel(
                self.albums_scroll,
                text="Chưa có ảnh nào được sao lưu.",
                font=ctk.CTkFont(size=13),
                text_color="#71717a"
            )
            lbl_empty.pack(expand=True, pady=60)
            return

        self._render_photos_page()

    def _render_photos_page(self):
        """Render the next page of photos (MAX_PHOTOS_PER_PAGE at a time)."""
        start = self._photos_page * MAX_PHOTOS_PER_PAGE
        end = min(start + MAX_PHOTOS_PER_PAGE, len(self._all_photos_list))
        page_photos = self._all_photos_list[start:end]

        if not page_photos:
            return

        # Remove existing "Load More" button if present
        for widget in self.albums_scroll.winfo_children():
            if hasattr(widget, '_is_load_more_btn'):
                widget.destroy()

        cols = 4
        for idx_in_page, photo in enumerate(page_photos):
            idx = start + idx_in_page
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
            elif photo.get("media_key"):
                m_key = photo.get("media_key")
                c_img = self._cloud_thumb_mgr.get_thumbnail(
                    media_key=m_key,
                    size=(120, 100),
                    api_client_provider=self._get_api_client,
                    widget_to_bind=lbl_img
                )
                if c_img:
                    lbl_img.configure(image=c_img, text="")
                    lbl_img.image = c_img

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

        # Add status indicator / auto-load hook if there are more photos
        remaining = len(self._all_photos_list) - end
        next_row = (end // cols) + 1
        if remaining > 0:
            load_more = ctk.CTkButton(
                self.albums_scroll,
                text=f"⏳ Tự động tải thêm khi cuộn... (còn {remaining} ảnh, bấm để tải ngay)",
                fg_color="#27272a",
                hover_color="#3f3f46",
                text_color="#9ca3af",
                font=ctk.CTkFont(size=11),
                height=32,
                command=self._load_more_photos
            )
            load_more._is_load_more_btn = True
            load_more.grid(row=next_row, column=0, columnspan=cols, padx=8, pady=10, sticky="ew")
        elif len(self._all_photos_list) > MAX_PHOTOS_PER_PAGE:
            end_lbl = ctk.CTkLabel(
                self.albums_scroll,
                text=f"✅ Đã hiển thị toàn bộ {len(self._all_photos_list)} ảnh",
                font=ctk.CTkFont(size=11),
                text_color="#71717a"
            )
            end_lbl._is_load_more_btn = True
            end_lbl.grid(row=next_row, column=0, columnspan=cols, padx=8, pady=10, sticky="ew")

    def _load_more_photos(self):
        """Load the next page of photos."""
        self._check_auto_load_more()

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
    def _get_api_client(self):
        """Helper to obtain or create an initialized Google Photos API client."""
        if self.get_uploader:
            uploader = self.get_uploader()
            if uploader:
                if not getattr(uploader, "_client", None):
                    try:
                        uploader._init_client()
                    except Exception:
                        pass
                if getattr(uploader, "_client", None):
                    return uploader._client.api

        active_acc = self.config_mgr.get_active_account()
        if active_acc:
            auth_data = active_acc.get("auth_data")
            if auth_data:
                try:
                    import gpmc
                    temp_client = gpmc.Client(auth_data=auth_data)
                    return temp_client.api
                except Exception:
                    pass
        return None

    def _update_album_title(self, album_name: str, cur_count: int, target_count: int = 0):
        video_exts = {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm", ".3gp", ".mts"}
        num_vids = sum(1 for p in self._album_photos_list if Path(p.get("filename", "")).suffix.lower() in video_exts)
        num_imgs = len(self._album_photos_list) - num_vids
        if num_vids > 0:
            count_str = f"{len(self._album_photos_list)} mục: {num_imgs} ảnh, {num_vids} video"
        else:
            count_str = f"{len(self._album_photos_list)} ảnh"

        if target_count and target_count > len(self._album_photos_list):
            count_str += f" (Đang tìm đủ {target_count} mục từ Cloud...)"

        self.lbl_viewing_album_title.configure(text=f"📁 {album_name} ({count_str})")

    def _manual_sync_current_album(self):
        if not self._current_viewing_album:
            return
        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""
        sync_folders = self.config_mgr.config.get("sync_folders", []) if self.config_mgr else []
        album_meta = next((a for a in self._all_albums if a.get("album_name") == self._current_viewing_album), None)
        remote_cnt = album_meta.get("photo_count", 0) if album_meta else 0
        self._sync_album_in_background(self._current_viewing_album, email, sync_folders, remote_cnt, force=True)

    def _open_album_photos(self, album_name: str):
        self._current_viewing_album = album_name
        self._is_loading_more = False
        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""
        sync_folders = self.config_mgr.config.get("sync_folders", []) if self.config_mgr else []
        photos = self.db.get_album_photos(album_name, email, sync_roots=sync_folders)

        album_meta = next((a for a in self._all_albums if a.get("album_name") == album_name), None)
        remote_cnt = album_meta.get("photo_count", 0) if album_meta else 0

        self.albums_scroll.pack_forget()
        self.photos_container.pack(fill="both", expand=True)

        self._album_photos_list = photos
        self._album_photos_page = 0
        self._update_album_title(album_name, len(photos), remote_cnt)

        if hasattr(self, "lbl_sync_status"):
            self.lbl_sync_status.configure(text="")

        for widget in self.photos_scroll.winfo_children():
            widget.destroy()

        if not photos:
            lbl_empty = ctk.CTkLabel(
                self.photos_scroll,
                text="Đang đồng bộ danh sách ảnh từ Google Photos..." if remote_cnt > 0 else "Chưa có ảnh nào trong album này.",
                font=ctk.CTkFont(size=13),
                text_color="#71717a"
            )
            lbl_empty.pack(expand=True, pady=40)
        else:
            self._render_album_detail_photos_page()

        if remote_cnt > len(photos):
            self._sync_album_in_background(album_name, email, sync_folders, remote_cnt)

    def _sync_album_in_background(self, album_name: str, email: str, sync_folders: list, target_count: int, force: bool = False):
        """Fetch remaining pages from Cloud in background to populate complete album items."""
        if self._is_syncing_album and not force:
            return
        api_client = self._get_api_client()
        if not api_client:
            if hasattr(self, "lbl_sync_status"):
                self.lbl_sync_status.configure(text="⚠️ Chưa kết nối Cloud", text_color="#f59e0b")
            return

        self._is_syncing_album = True
        if hasattr(self, "btn_sync_this"):
            self.btn_sync_this.configure(state="disabled", text="⏳ Đang quét...")
        if hasattr(self, "lbl_sync_status"):
            self.lbl_sync_status.configure(text="⏳ Đang kết nối Cloud...", text_color="#38bdf8")

        def worker():
            from core.uploader import sync_cloud_albums

            def on_page_progress(cur_page: int, max_p: int):
                new_photos = self.db.get_album_photos(album_name, email, sync_roots=sync_folders)
                def live_update():
                    if self._current_viewing_album != album_name:
                        return
                    cur_cnt = len(new_photos)
                    if hasattr(self, "lbl_sync_status"):
                        self.lbl_sync_status.configure(
                            text=f"⏳ Đang quét Cloud... Trang {cur_page}/{max_p} ({cur_cnt}/{target_count} mục)" if target_count else f"⏳ Trang {cur_page} ({cur_cnt} mục)",
                            text_color="#38bdf8"
                        )
                    if cur_cnt != len(self._album_photos_list):
                        self._album_photos_list = new_photos
                        self._album_photos_page = 0
                        self._update_album_title(album_name, cur_cnt, target_count)
                        for w in self.photos_scroll.winfo_children():
                            w.destroy()
                        self._render_album_detail_photos_page()
                self.after(0, live_update)

            try:
                sync_cloud_albums(
                    api=api_client,
                    db=self.db,
                    account_email=email,
                    target_album_names=[album_name],
                    max_pages=80,
                    progress_callback=on_page_progress
                )
            except Exception:
                pass
            finally:
                self._is_syncing_album = False
                final_photos = self.db.get_album_photos(album_name, email, sync_roots=sync_folders)
                def on_finish():
                    if hasattr(self, "btn_sync_this"):
                        self.btn_sync_this.configure(state="normal", text="🔄 Đồng bộ từ Cloud")
                    if self._current_viewing_album == album_name:
                        self._album_photos_list = final_photos
                        self._album_photos_page = 0
                        f_cnt = len(final_photos)
                        self._update_album_title(album_name, f_cnt, 0)
                        if hasattr(self, "lbl_sync_status"):
                            if target_count and f_cnt >= target_count:
                                self.lbl_sync_status.configure(text=f"✅ Đã đủ {f_cnt}/{target_count} mục", text_color="#4ade80")
                            elif f_cnt > 0:
                                self.lbl_sync_status.configure(text=f"✅ Đã tìm thấy {f_cnt} mục", text_color="#4ade80")
                            else:
                                self.lbl_sync_status.configure(text="ℹ️ Không tìm thấy thêm mục nào", text_color="#9ca3af")
                        for w in self.photos_scroll.winfo_children():
                            w.destroy()
                        self._render_album_detail_photos_page()
                self.after(0, on_finish)

        threading.Thread(target=worker, daemon=True).start()

    def _render_album_detail_photos_page(self):
        """Render the next page of photos inside the current album view."""
        start = self._album_photos_page * MAX_PHOTOS_PER_PAGE
        end = min(start + MAX_PHOTOS_PER_PAGE, len(self._album_photos_list))
        page_photos = self._album_photos_list[start:end]

        if not page_photos:
            return

        # Remove existing indicator or button
        for widget in self.photos_scroll.winfo_children():
            if hasattr(widget, '_is_load_more_btn'):
                widget.destroy()

        cols = 4
        for idx_in_page, photo in enumerate(page_photos):
            idx = start + idx_in_page
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

            video_exts = {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm", ".3gp", ".mts"}
            is_vid = Path(filename).suffix.lower() in video_exts
            default_icon = "🎬" if is_vid else "📷"

            lbl_img = ctk.CTkLabel(t_box, text=default_icon, font=ctk.CTkFont(size=26), cursor="hand2")
            lbl_img.place(relx=0.5, rely=0.5, anchor="center")

            if local_path and Path(local_path).exists():
                lbl_img.bind("<Double-Button-1>", lambda e, p=local_path: self._open_file_system(p))
                t_img = get_file_thumbnail(Path(local_path), size=(120, 100))
                if t_img:
                    lbl_img.configure(image=t_img, text="")
                elif is_vid:
                    lbl_img.configure(text="🎬 VIDEO", font=ctk.CTkFont(size=13, weight="bold"), text_color="#38bdf8")
            elif photo.get("media_key"):
                m_key = photo.get("media_key")
                c_img = self._cloud_thumb_mgr.get_thumbnail(
                    media_key=m_key,
                    size=(120, 100),
                    api_client_provider=self._get_api_client,
                    widget_to_bind=lbl_img
                )
                if c_img:
                    lbl_img.configure(image=c_img, text="")
                    lbl_img.image = c_img

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

        # Add status indicator / auto-load hook if there are more photos
        remaining = len(self._album_photos_list) - end
        next_row = (end // cols) + 1
        if remaining > 0:
            load_more = ctk.CTkButton(
                self.photos_scroll,
                text=f"⏳ Tự động tải thêm khi cuộn... (còn {remaining} ảnh, bấm để tải ngay)",
                fg_color="#27272a",
                hover_color="#3f3f46",
                text_color="#9ca3af",
                font=ctk.CTkFont(size=11),
                height=32,
                command=self._load_more_album_photos
            )
            load_more._is_load_more_btn = True
            load_more.grid(row=next_row, column=0, columnspan=cols, padx=8, pady=10, sticky="ew")
        elif len(self._album_photos_list) > MAX_PHOTOS_PER_PAGE:
            end_lbl = ctk.CTkLabel(
                self.photos_scroll,
                text=f"✅ Đã hiển thị toàn bộ {len(self._album_photos_list)} ảnh",
                font=ctk.CTkFont(size=11),
                text_color="#71717a"
            )
            end_lbl._is_load_more_btn = True
            end_lbl.grid(row=next_row, column=0, columnspan=cols, padx=8, pady=10, sticky="ew")

    def _load_more_album_photos(self):
        """Load the next page of album detail photos."""
        self._check_auto_load_more_album_photos()

    def _open_file_system(self, file_path: str):
        try:
            os.startfile(file_path)
        except Exception:
            pass

    def _confirm_delete_album(self, album_name: str):
        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""
        if messagebox.askyesno(
            t("confirm_delete_album_title"),
            t("confirm_delete_album_msg", name=album_name),
            parent=self
        ):
            self.db.delete_album(album_name, email)
            self._selected_album_names.discard(album_name)
            self.load_albums()

    def _delete_current_viewing_album(self):
        if not self._current_viewing_album:
            return
        album_name = self._current_viewing_album
        active_acc = self.config_mgr.get_active_account()
        email = active_acc.get("email", "") if active_acc else ""
        if messagebox.askyesno(
            t("confirm_delete_album_title"),
            t("confirm_delete_album_msg", name=album_name),
            parent=self
        ):
            self.db.delete_album(album_name, email)
            self._selected_album_names.discard(album_name)
            self._show_albums_view()
            self.load_albums()

    def _show_albums_view(self):
        self.photos_container.pack_forget()
        self.albums_scroll.pack(fill="both", expand=True)
        self._current_viewing_album = None
        self._is_loading_more = False

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
        sync_folders = self.config_mgr.config.get("sync_folders", []) if self.config_mgr else []
        api_client = self._get_api_client()

        dlg = DownloadProgressDialog(self.winfo_toplevel(), album_names, dest_root)
        downloader = AlbumDownloader(api=api_client, max_threads=4)
        self._downloader = downloader

        def run():
            try:
                # 1. Sync full album contents from cloud if local count < remote count
                albums_to_sync = []
                for name in album_names:
                    album_meta = next((a for a in self._all_albums if a.get("album_name") == name), None)
                    remote_cnt = album_meta.get("photo_count", 0) if album_meta else 0
                    current_photos = self.db.get_album_photos(name, email, sync_roots=sync_folders)
                    if len(current_photos) < remote_cnt:
                        albums_to_sync.append(name)

                if albums_to_sync and api_client:
                    self.after(0, lambda: dlg.set_status(f"Đang đồng bộ danh sách ảnh từ Google Photos ({len(albums_to_sync)} album)..."))
                    from core.uploader import sync_cloud_albums
                    sync_cloud_albums(
                        api=api_client,
                        db=self.db,
                        account_email=email,
                        target_album_names=albums_to_sync,
                        max_pages=60,
                        progress_callback=lambda cur, tot: self.after(0, lambda: dlg.set_status(f"Đang đồng bộ ảnh từ Google Photos (trang {cur})..."))
                    )

                # 2. Build complete payload with up-to-date photo list
                payload = []
                for name in album_names:
                    photos = self.db.get_album_photos(name, email, sync_roots=sync_folders)
                    payload.append({
                        "album_name": name,
                        "items": photos
                    })

                self.after(0, lambda: dlg.set_status("Đang bắt đầu tải tệp về máy..."))
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
        self.album_names = album_names
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

    def set_status(self, text: str):
        self.lbl_status.configure(text=text)

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
        err = res.get("error_count", 0)
        dest = res.get("destination", "")

        if cnt > 0:
            self.lbl_status.configure(
                text=f"✅ Hoàn tất! Đã lưu {albs} album ({cnt} tệp) vào máy.",
                text_color="#4ade80"
            )
        else:
            if err > 0:
                self.lbl_status.configure(
                    text=f"⚠️ Tải thất bại ({err} lỗi). Vui lòng kiểm tra lại kết nối mạng.",
                    text_color="#f59e0b"
                )
            else:
                self.lbl_status.configure(
                    text=f"ℹ️ Album này chưa có ảnh/video nào trong thư viện.",
                    text_color="#94a3b8"
                )
        self.btn_open_folder.pack(pady=10)

    def on_error(self, err_msg: str):
        self.lbl_status.configure(
            text=f"❌ Lỗi: {err_msg}",
            text_color="#ef4444"
        )

    def _open_folder(self):
        try:
            from core.downloader import sanitize_folder_name
            target = self.dest_dir
            if len(self.album_names) == 1:
                sub = self.dest_dir / sanitize_folder_name(self.album_names[0])
                if sub.exists():
                    target = sub
            os.startfile(target)
        except Exception:
            pass
        self.destroy()
