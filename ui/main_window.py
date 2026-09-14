"""Main UI window for Google Photos ReVanced Windows edition.
Features modern Windows 11 Fluent Dark interface, real-time multi-threaded
upload carousel (Android Google Photos style with vanishing completed cards),
folder management, bilingual support (English default, Vietnamese), and live activity logs.
"""

import os
import sys
import time
import threading
from pathlib import Path
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.auth import ConfigManager
from core.db import UploadDatabase
from core.uploader import PhotoUploader, SUPPORTED_EXTENSIONS
from core.watcher import FolderWatcher
from core.i18n import set_language, get_language, t
from ui.dialogs import LoginDialog
from ui.upload_tray import ActiveUploadTray


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Appearance & Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Google Photos ReVanced - Windows Edition (Pixel XL Spoofing)")
        self.geometry("1060x760")
        self.minsize(920, 640)

        # Core Managers
        self.config_mgr = ConfigManager()
        # Initialize active language from config (default 'en')
        current_lang = self.config_mgr.config.get("language", "en")
        set_language(current_lang)

        self.db = UploadDatabase()
        self.uploader: PhotoUploader = None
        self.watcher: FolderWatcher = None

        # UI State
        self._is_paused = False

        # Build Interface
        self._build_header()
        self._build_tabs()
        self._build_footer()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Initialize Backend Engine
        self.after(200, self._init_engine)

    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, height=80, fg_color="#18181b")
        self.header_frame.pack(fill="x", side="top")

        # Left: Branding
        brand_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        brand_frame.pack(side="left", padx=20, pady=12)

        title_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_box.pack(anchor="w")

        app_title = ctk.CTkLabel(
            title_box,
            text=t("app_title"),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ffffff"
        )
        app_title.pack(side="left")

        badge = ctk.CTkLabel(
            title_box,
            text=t("badge_pixel"),
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#166534",
            text_color="#4ade80",
            corner_radius=6,
            padx=8,
            pady=2
        )
        badge.pack(side="left", padx=10)

        self.lbl_subtitle = ctk.CTkLabel(
            brand_frame,
            text=t("app_subtitle"),
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        )
        self.lbl_subtitle.pack(anchor="w", pady=(2, 0))

        # Right: Account status card
        self.account_frame = ctk.CTkFrame(self.header_frame, fg_color="#27272a", corner_radius=8)
        self.account_frame.pack(side="right", padx=20, pady=14)

        self.account_label = ctk.CTkLabel(
            self.account_frame,
            text=t("account_loading"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f4f4f5",
            padx=12
        )
        self.account_label.pack(side="left", padx=(6, 4))

        self.btn_account = ctk.CTkButton(
            self.account_frame,
            text=t("btn_connect_account"),
            font=ctk.CTkFont(size=12),
            height=30,
            width=120,
            command=self._open_login_dialog
        )
        self.btn_account.pack(side="left", padx=(0, 6), pady=4)

    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(10, 10))

        self.tab_dashboard = self.tabview.add("dashboard")
        self.tab_folders = self.tabview.add("folders")
        self.tab_logs = self.tabview.add("logs")
        self.tab_settings = self.tabview.add("settings")

        self.tabview._segmented_button._buttons_dict["dashboard"].configure(text=t("tab_dashboard"))
        self.tabview._segmented_button._buttons_dict["folders"].configure(text=t("tab_folders"))
        self.tabview._segmented_button._buttons_dict["logs"].configure(text=t("tab_logs"))
        self.tabview._segmented_button._buttons_dict["settings"].configure(text=t("tab_settings"))

        self._build_dashboard_tab()
        self._build_folders_tab()
        self._build_logs_tab()
        self._build_settings_tab()

    def _build_dashboard_tab(self):
        tab = self.tab_dashboard

        # 1. Stats Row with Header & Reset
        stats_top = ctk.CTkFrame(tab, fg_color="transparent")
        stats_top.pack(fill="x", padx=16, pady=(8, 2))

        self.lbl_stats_top = ctk.CTkLabel(
            stats_top,
            text=t("stats_header"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#a1a1aa"
        )
        self.lbl_stats_top.pack(side="left")

        self.btn_reset_stats_top = ctk.CTkButton(
            stats_top,
            text=t("btn_reset_stats_quick"),
            font=ctk.CTkFont(size=11),
            width=140,
            height=26,
            fg_color="#3f3f46",
            hover_color="#52525b",
            command=self._confirm_reset_statistics
        )
        self.btn_reset_stats_top.pack(side="right")

        stats_frame = ctk.CTkFrame(tab, fg_color="transparent")
        stats_frame.pack(fill="x", padx=10, pady=(2, 12))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="stats")

        # Card 1: Total Uploaded
        c1 = ctk.CTkFrame(stats_frame, fg_color="#27272a", corner_radius=10)
        c1.grid(row=0, column=0, padx=6, pady=4, sticky="nsew")
        self.lbl_card1_title = ctk.CTkLabel(c1, text=t("stat_backed_up"), font=ctk.CTkFont(size=12), text_color="#a1a1aa")
        self.lbl_card1_title.pack(pady=(10, 2))
        self.lbl_stat_files = ctk.CTkLabel(c1, text="0 files", font=ctk.CTkFont(size=20, weight="bold"), text_color="#38bdf8")
        self.lbl_stat_files.pack(pady=(0, 10))

        # Card 2: Saved Quota
        c2 = ctk.CTkFrame(stats_frame, fg_color="#27272a", corner_radius=10)
        c2.grid(row=0, column=1, padx=6, pady=4, sticky="nsew")
        self.lbl_card2_title = ctk.CTkLabel(c2, text=t("stat_saved_storage"), font=ctk.CTkFont(size=12), text_color="#a1a1aa")
        self.lbl_card2_title.pack(pady=(10, 2))
        self.lbl_stat_saved = ctk.CTkLabel(c2, text="0.00 GB", font=ctk.CTkFont(size=20, weight="bold"), text_color="#4ade80")
        self.lbl_stat_saved.pack(pady=(0, 10))

        # Card 3: Auto-Sync Status
        c3 = ctk.CTkFrame(stats_frame, fg_color="#27272a", corner_radius=10)
        c3.grid(row=0, column=2, padx=6, pady=4, sticky="nsew")
        self.lbl_card3_title = ctk.CTkLabel(c3, text=t("stat_auto_sync"), font=ctk.CTkFont(size=12), text_color="#a1a1aa")
        self.lbl_card3_title.pack(pady=(10, 2))
        self.lbl_stat_status = ctk.CTkLabel(c3, text=t("status_ready"), font=ctk.CTkFont(size=18, weight="bold"), text_color="#fbbf24")
        self.lbl_stat_status.pack(pady=(0, 10))

        # Card 4: Device Model
        c4 = ctk.CTkFrame(stats_frame, fg_color="#27272a", corner_radius=10)
        c4.grid(row=0, column=3, padx=6, pady=4, sticky="nsew")
        self.lbl_card4_title = ctk.CTkLabel(c4, text=t("stat_emulated_device"), font=ctk.CTkFont(size=12), text_color="#a1a1aa")
        self.lbl_card4_title.pack(pady=(10, 2))
        self.lbl_stat_device = ctk.CTkLabel(c4, text="Pixel XL (marlin)", font=ctk.CTkFont(size=18, weight="bold"), text_color="#c084fc")
        self.lbl_stat_device.pack(pady=(0, 10))

        # 2. Quick Upload Controls Bar
        action_card = ctk.CTkFrame(tab, fg_color="#27272a", corner_radius=10)
        action_card.pack(fill="x", padx=16, pady=(0, 10))

        btn_row = ctk.CTkFrame(action_card, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=10)

        self.btn_manual_files = ctk.CTkButton(
            btn_row,
            text=t("btn_select_files"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold"),
            command=self._manual_upload_files
        )
        self.btn_manual_files.pack(side="left", padx=(0, 6))

        self.btn_manual_folder = ctk.CTkButton(
            btn_row,
            text=t("btn_upload_folder"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=ctk.CTkFont(weight="bold"),
            command=self._manual_upload_folder
        )
        self.btn_manual_folder.pack(side="left", padx=6)

        self.btn_pause = ctk.CTkButton(
            btn_row,
            text=t("btn_pause"),
            fg_color="#d97706",
            hover_color="#b45309",
            width=90,
            command=self._toggle_pause
        )
        self.btn_pause.pack(side="left", padx=6)

        self.btn_cancel = ctk.CTkButton(
            btn_row,
            text=t("btn_cancel"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            width=70,
            command=self._cancel_queue
        )
        self.btn_cancel.pack(side="left", padx=6)

        self.btn_reset_action = ctk.CTkButton(
            btn_row,
            text=t("btn_reset_stats"),
            fg_color="#3f3f46",
            hover_color="#52525b",
            width=120,
            command=self._confirm_reset_statistics
        )
        self.btn_reset_action.pack(side="left", padx=6)

        # Right: Quick Thread Selector
        thread_box = ctk.CTkFrame(btn_row, fg_color="transparent")
        thread_box.pack(side="right")

        self.lbl_quick_threads_title = ctk.CTkLabel(
            thread_box,
            text=t("lbl_threads"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f4f4f5"
        )
        self.lbl_quick_threads_title.pack(side="left", padx=(0, 6))

        self.combo_quick_threads = ctk.CTkComboBox(
            thread_box,
            values=[t("thread_opt_1"), t("thread_opt_2"), t("thread_opt_4"), t("thread_opt_6"), t("thread_opt_8")],
            width=190,
            command=self._on_change_quick_threads
        )
        self.combo_quick_threads.pack(side="left")
        self._update_quick_thread_options()

        # 3. Visual Android-style Upload Gallery (Upload Tray)
        self.upload_tray = ActiveUploadTray(tab)
        self.upload_tray.pack(fill="x", padx=16, pady=(0, 10))

        # 4. Summary Macro Progress Bar
        summary_card = ctk.CTkFrame(tab, fg_color="#27272a", corner_radius=10)
        summary_card.pack(fill="x", padx=16, pady=(0, 10))

        s_header = ctk.CTkFrame(summary_card, fg_color="transparent")
        s_header.pack(fill="x", padx=16, pady=(8, 2))

        self.lbl_current_file = ctk.CTkLabel(
            s_header,
            text=t("queue_ready_empty"),
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8"
        )
        self.lbl_current_file.pack(side="left")

        self.lbl_speed = ctk.CTkLabel(
            s_header,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#4ade80"
        )
        self.lbl_speed.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(summary_card, height=10, corner_radius=5)
        self.progress_bar.pack(fill="x", padx=16, pady=(4, 6))
        self.progress_bar.set(0)

        self.lbl_progress_status = ctk.CTkLabel(
            summary_card,
            text=t("backup_mode_footer"),
            font=ctk.CTkFont(size=11),
            text_color="#71717a",
            anchor="w"
        )
        self.lbl_progress_status.pack(fill="x", padx=16, pady=(0, 8))

    def _build_folders_tab(self):
        tab = self.tab_folders

        self.lbl_folders_guide = ctk.CTkLabel(
            tab,
            text=t("folders_guide"),
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa",
            wraplength=850,
            justify="left"
        )
        self.lbl_folders_guide.pack(anchor="w", padx=16, pady=(12, 10))

        # Folder list container
        self.folder_list_frame = ctk.CTkScrollableFrame(tab, height=320, fg_color="#27272a", corner_radius=10)
        self.folder_list_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Bottom buttons for folders
        btn_box = ctk.CTkFrame(tab, fg_color="transparent")
        btn_box.pack(fill="x", padx=16, pady=(0, 14))

        self.btn_add_folder = ctk.CTkButton(
            btn_box,
            text=t("btn_add_folder"),
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(weight="bold"),
            command=self._add_sync_folder
        )
        self.btn_add_folder.pack(side="left", padx=(0, 8))

        self.btn_scan_all = ctk.CTkButton(
            btn_box,
            text=t("btn_scan_all"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self._scan_all_folders_now
        )
        self.btn_scan_all.pack(side="left", padx=8)

        self.switch_auto_album = ctk.CTkSwitch(
            btn_box,
            text=t("switch_auto_album"),
            command=self._on_toggle_auto_album
        )
        self.switch_auto_album.pack(side="right", padx=8)

    def _build_logs_tab(self):
        tab = self.tab_logs

        top_row = ctk.CTkFrame(tab, fg_color="transparent")
        top_row.pack(fill="x", padx=16, pady=(12, 6))

        self.lbl_logs_header = ctk.CTkLabel(
            top_row,
            text=t("logs_header"),
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.lbl_logs_header.pack(side="left")

        self.btn_clear_logs = ctk.CTkButton(
            top_row,
            text=t("btn_clear_logs"),
            width=100,
            height=28,
            fg_color="#3f3f46",
            hover_color="#52525b",
            command=self._clear_logs
        )
        self.btn_clear_logs.pack(side="right")

        self.log_textbox = ctk.CTkTextbox(tab, font=ctk.CTkFont(family="Consolas", size=11))
        self.log_textbox.pack(fill="both", expand=True, padx=16, pady=(0, 14))

    def _build_settings_tab(self):
        tab = self.tab_settings

        card = ctk.CTkFrame(tab, fg_color="#27272a", corner_radius=10)
        card.pack(fill="x", padx=16, pady=16)

        self.lbl_settings_header = ctk.CTkLabel(card, text=t("settings_header"), font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_settings_header.pack(anchor="w", padx=20, pady=(16, 12))

        # Language Selector
        lang_row = ctk.CTkFrame(card, fg_color="transparent")
        lang_row.pack(fill="x", padx=20, pady=8)
        self.lbl_setting_lang = ctk.CTkLabel(lang_row, text=t("lbl_language"), width=200, anchor="w", font=ctk.CTkFont(size=13))
        self.lbl_setting_lang.pack(side="left")
        self.combo_language = ctk.CTkComboBox(
            lang_row,
            values=["English (Default)", "Tiếng Việt"],
            width=220,
            command=self._on_change_language
        )
        self.combo_language.pack(side="left")
        cur_lang = self.config_mgr.config.get("language", "en")
        self.combo_language.set("Tiếng Việt" if cur_lang == "vi" else "English (Default)")

        # Quality
        q_row = ctk.CTkFrame(card, fg_color="transparent")
        q_row.pack(fill="x", padx=20, pady=8)
        self.lbl_setting_quality = ctk.CTkLabel(q_row, text=t("lbl_quality"), width=200, anchor="w", font=ctk.CTkFont(size=13))
        self.lbl_setting_quality.pack(side="left")
        self.combo_quality = ctk.CTkComboBox(
            q_row,
            values=[t("quality_original"), t("quality_saver")],
            width=380
        )
        self.combo_quality.pack(side="left")
        cur_q = self.config_mgr.config.get("quality", "original")
        self.combo_quality.set(t("quality_original") if cur_q == "original" else t("quality_saver"))

        # Threads
        t_row = ctk.CTkFrame(card, fg_color="transparent")
        t_row.pack(fill="x", padx=20, pady=8)
        self.lbl_setting_threads = ctk.CTkLabel(t_row, text=t("lbl_threads_setting"), width=200, anchor="w", font=ctk.CTkFont(size=13))
        self.lbl_setting_threads.pack(side="left")
        is_vi = get_language() == "vi"
        t_vals = ["1", "2", "4 (Khuyên dùng)", "6 (Siêu tốc)", "8 (Tối đa)"] if is_vi else ["1", "2", "4 (Recommended)", "6 (Ultra Speed)", "8 (Maximum)"]
        self.combo_threads = ctk.CTkComboBox(
            t_row,
            values=t_vals,
            width=190
        )
        self.combo_threads.pack(side="left")
        cur_t = self.config_mgr.config.get("threads", 4)
        rec_tag = "(Khuyên dùng)" if is_vi else "(Recommended)"
        self.combo_threads.set(f"{cur_t} {rec_tag}" if cur_t == 4 else str(cur_t))

        # Minimize to tray
        tray_row = ctk.CTkFrame(card, fg_color="transparent")
        tray_row.pack(fill="x", padx=20, pady=10)
        self.switch_tray = ctk.CTkSwitch(tray_row, text=t("switch_tray"))
        self.switch_tray.pack(side="left")
        if self.config_mgr.config.get("minimize_to_tray", True):
            self.switch_tray.select()

        # Save button
        self.btn_save_settings = ctk.CTkButton(
            card,
            text=t("btn_save_settings"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold"),
            height=36,
            command=self._save_settings
        )
        self.btn_save_settings.pack(anchor="w", padx=20, pady=(16, 20))

        # Database & Stats Management Card
        data_card = ctk.CTkFrame(tab, fg_color="#27272a", corner_radius=10)
        data_card.pack(fill="x", padx=16, pady=(0, 16))

        self.lbl_data_header = ctk.CTkLabel(data_card, text=t("data_mgmt_header"), font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_data_header.pack(anchor="w", padx=20, pady=(16, 8))

        self.lbl_data_desc = ctk.CTkLabel(
            data_card,
            text=t("data_mgmt_desc"),
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa"
        )
        self.lbl_data_desc.pack(anchor="w", padx=20, pady=(0, 12))

        self.btn_reset_data = ctk.CTkButton(
            data_card,
            text=t("btn_reset_data"),
            fg_color="#7f1d1d",
            hover_color="#991b1b",
            font=ctk.CTkFont(weight="bold"),
            height=34,
            command=self._confirm_reset_statistics
        )
        self.btn_reset_data.pack(anchor="w", padx=20, pady=(0, 16))

    def _build_footer(self):
        footer = ctk.CTkFrame(self, height=28, fg_color="#18181b", corner_radius=0)
        footer.pack(fill="x", side="bottom")

        self.lbl_foot = ctk.CTkLabel(
            footer,
            text=t("app_footer"),
            font=ctk.CTkFont(size=11),
            text_color="#71717a"
        )
        self.lbl_foot.pack(side="left", padx=16, pady=2)

    # ------------------ Dynamic Language Switching ------------------

    def _on_change_language(self, choice: str):
        lang_code = "vi" if "Việt" in choice else "en"
        self.config_mgr.config["language"] = lang_code
        self.config_mgr.save_config()
        set_language(lang_code)
        self._apply_language()
        self.append_log(f"Language switched to: {choice}", "INFO")

    def _apply_language(self):
        """Re-apply all localized strings to UI elements without restarting."""
        self.lbl_subtitle.configure(text=t("app_subtitle"))

        # Update tabs
        self.tabview._segmented_button._buttons_dict["dashboard"].configure(text=t("tab_dashboard"))
        self.tabview._segmented_button._buttons_dict["folders"].configure(text=t("tab_folders"))
        self.tabview._segmented_button._buttons_dict["logs"].configure(text=t("tab_logs"))
        self.tabview._segmented_button._buttons_dict["settings"].configure(text=t("tab_settings"))

        # Header account button
        active_acc = self.config_mgr.get_active_account()
        if active_acc and active_acc.get("auth_data"):
            email = active_acc.get("email", "Google Account")
            self.account_label.configure(text=f"👤 {email}")
            self.btn_account.configure(text=t("btn_switch_account"))
        else:
            self.account_label.configure(text=t("account_unconnected"))
            self.btn_account.configure(text=t("btn_connect_account"))

        # Dashboard top
        self.lbl_stats_top.configure(text=t("stats_header"))
        self.btn_reset_stats_top.configure(text=t("btn_reset_stats_quick"))

        # Dashboard cards
        self.lbl_card1_title.configure(text=t("stat_backed_up"))
        self.lbl_card2_title.configure(text=t("stat_saved_storage"))
        self.lbl_card3_title.configure(text=t("stat_auto_sync"))
        self.lbl_card4_title.configure(text=t("stat_emulated_device"))

        # Auto sync card status
        if self.watcher and self.watcher.is_running:
            self.lbl_stat_status.configure(text=t("status_monitoring"), text_color="#4ade80")
        else:
            self.lbl_stat_status.configure(text=t("status_ready"), text_color="#fbbf24")

        # Actions
        self.btn_manual_files.configure(text=t("btn_select_files"))
        self.btn_manual_folder.configure(text=t("btn_upload_folder"))
        self.btn_pause.configure(text=t("btn_resume") if self._is_paused else t("btn_pause"))
        self.btn_cancel.configure(text=t("btn_cancel"))
        self.btn_reset_action.configure(text=t("btn_reset_stats"))
        self.lbl_quick_threads_title.configure(text=t("lbl_threads"))

        # Update quick threads combobox
        self._update_quick_thread_options()

        # Status footer
        if not self.uploader or not self.uploader.queue:
            self.lbl_current_file.configure(text=t("queue_ready_empty"))
        self.lbl_progress_status.configure(text=t("backup_mode_footer"))

        # Folders tab
        self.lbl_folders_guide.configure(text=t("folders_guide"))
        self.btn_add_folder.configure(text=t("btn_add_folder"))
        self.btn_scan_all.configure(text=t("btn_scan_all"))
        self.switch_auto_album.configure(text=t("switch_auto_album"))
        self._refresh_folder_list()

        # Logs tab
        self.lbl_logs_header.configure(text=t("logs_header"))
        self.btn_clear_logs.configure(text=t("btn_clear_logs"))

        # Settings tab
        self.lbl_settings_header.configure(text=t("settings_header"))
        self.lbl_setting_lang.configure(text=t("lbl_language"))
        self.lbl_setting_quality.configure(text=t("lbl_quality"))
        self.combo_quality.configure(values=[t("quality_original"), t("quality_saver")])
        cur_q = self.config_mgr.config.get("quality", "original")
        self.combo_quality.set(t("quality_original") if cur_q == "original" else t("quality_saver"))

        self.lbl_setting_threads.configure(text=t("lbl_threads_setting"))
        is_vi = get_language() == "vi"
        t_vals = ["1", "2", "4 (Khuyên dùng)", "6 (Siêu tốc)", "8 (Tối đa)"] if is_vi else ["1", "2", "4 (Recommended)", "6 (Ultra Speed)", "8 (Maximum)"]
        self.combo_threads.configure(values=t_vals)
        cur_t = self.config_mgr.config.get("threads", 4)
        rec_tag = "(Khuyên dùng)" if is_vi else "(Recommended)"
        self.combo_threads.set(f"{cur_t} {rec_tag}" if cur_t == 4 else str(cur_t))

        self.switch_tray.configure(text=t("switch_tray"))
        self.btn_save_settings.configure(text=t("btn_save_settings"))

        self.lbl_data_header.configure(text=t("data_mgmt_header"))
        self.lbl_data_desc.configure(text=t("data_mgmt_desc"))
        self.btn_reset_data.configure(text=t("btn_reset_data"))

        # Footer
        self.lbl_foot.configure(text=t("app_footer"))

    def _update_quick_thread_options(self):
        is_vi = get_language() == "vi"
        cur_threads = self.config_mgr.config.get("threads", 4)
        if is_vi:
            options = ["1 luồng", "2 luồng", "4 luồng (Khuyên dùng)", "6 luồng (Siêu tốc)", "8 luồng (Tối đa)"]
            sel = f"{cur_threads} luồng (Khuyên dùng)" if cur_threads == 4 else f"{cur_threads} luồng (Siêu tốc)" if cur_threads == 6 else f"{cur_threads} luồng (Tối đa)" if cur_threads == 8 else f"{cur_threads} luồng"
        else:
            options = ["1 thread", "2 threads", "4 threads (Recommended)", "6 threads (Ultra Speed)", "8 threads (Maximum)"]
            sel = f"{cur_threads} threads (Recommended)" if cur_threads == 4 else f"{cur_threads} threads (Ultra Speed)" if cur_threads == 6 else f"{cur_threads} threads (Maximum)" if cur_threads == 8 else f"{cur_threads} threads"

        self.combo_quick_threads.configure(values=options)
        self.combo_quick_threads.set(sel)

    # ------------------ Core Logic & Event Handling ------------------

    def append_log(self, message: str, level: str = "INFO"):
        now_str = time.strftime("%H:%M:%S")
        prefix = {
            "SUCCESS": "✅ [SUCCESS]",
            "INFO": "ℹ️ [INFO]",
            "WARNING": "⚠️ [WARNING]",
            "ERROR": "❌ [ERROR]",
        }.get(level, f"[{level}]")

        # In thời gian thực ra cửa sổ Console (CMD/PowerShell) phục vụ debug
        try:
            print(f"[{now_str}] {prefix} {message}", flush=True)
        except Exception:
            try:
                clean_msg = message.encode("ascii", "replace").decode("ascii")
                print(f"[{now_str}] [{level}] {clean_msg}", flush=True)
            except Exception:
                pass

        def _write():
            try:
                line = f"[{now_str}] {prefix} {message}\n"
                self.log_textbox.insert("end", line)
                self.log_textbox.see("end")
            except Exception:
                pass
        self.after(0, _write)

    def _handle_uploader_event(self, data: dict):
        def _process():
            evt_type = data.get("type")
            path_str = data.get("path", "")
            file_path = Path(path_str) if path_str else None
            worker_id = data.get("worker_id", 1)
            percent = data.get("percent", 0.0)
            speed = data.get("speed", "")
            active_count = data.get("active_count", 0)
            rem_queue = data.get("remaining_queue", 0)

            # Update tray counters
            self.upload_tray.update_counts(active_count, rem_queue)

            if evt_type == "file_started" and file_path:
                prep_txt = "Preparing..." if get_language() == "en" else "Đang chuẩn bị..."
                self.upload_tray.add_or_update_file(file_path, worker_id, 0.0, prep_txt)
                if get_language() == "en":
                    self.lbl_current_file.configure(text=f"Uploading {active_count} files in parallel • {rem_queue} remaining in queue")
                else:
                    self.lbl_current_file.configure(text=f"Đang tải song song {active_count} file • Còn lại {rem_queue} trong hàng đợi")
            elif evt_type == "file_progress" and file_path:
                self.upload_tray.add_or_update_file(file_path, worker_id, percent, speed)
                if speed:
                    speed_lbl = f"Speed: {speed}" if get_language() == "en" else f"Tốc độ: {speed}"
                    self.lbl_speed.configure(text=speed_lbl)
                self.progress_bar.set(percent / 100.0)
            elif evt_type == "file_completed" and file_path:
                was_skipped = data.get("was_skipped", False)
                self.upload_tray.mark_completed(file_path, was_skipped=was_skipped)
                self._refresh_stats()
            elif evt_type == "file_skipped" and file_path:
                self.upload_tray.mark_completed(file_path, was_skipped=True)
            elif evt_type == "file_error" and file_path:
                err_lbl = "Error" if get_language() == "en" else "Lỗi"
                self.upload_tray.mark_error(file_path, data.get("error", err_lbl))
            elif evt_type in ("queue_empty", "queue_cancelled"):
                empty_msg = "Ready. All photos safely backed up to Google Photos!" if get_language() == "en" else "Sẵn sàng. Tất cả ảnh đã được sao lưu an toàn lên Cloud!"
                self.lbl_current_file.configure(text=empty_msg)
                self.lbl_speed.configure(text="")
                self.progress_bar.set(0)
                self._refresh_stats()

        self.after(0, _process)

    def _refresh_stats(self):
        stats = self.db.get_statistics()
        self.lbl_stat_files.configure(text=f"{stats['total_files']:,} files")
        self.lbl_stat_saved.configure(text=f"{stats['total_gb']:.2f} GB")

    def _init_engine(self):
        self.append_log("Starting Google Photos ReVanced engine...", "INFO")
        active_acc = self.config_mgr.get_active_account()

        if not active_acc or not active_acc.get("auth_data"):
            self.account_label.configure(text=t("account_unconnected"))
            self.btn_account.configure(text=t("btn_connect_account"))
            self.append_log("No Google account connected. Please sign in to activate unlimited backup.", "WARNING")
            self._open_login_dialog()
            return

        email = active_acc.get("email", "Google Account")
        auth_data = active_acc.get("auth_data")

        self.account_label.configure(text=f"👤 {email}")
        self.btn_account.configure(text=t("btn_switch_account"))

        try:
            # Initialize Uploader with multi-threading
            quality = self.config_mgr.config.get("quality", "original")
            threads = int(self.config_mgr.config.get("threads", 4))
            auto_album = self.config_mgr.config.get("auto_album", False)
            if auto_album:
                self.switch_auto_album.select()
            else:
                self.switch_auto_album.deselect()

            self.uploader = PhotoUploader(
                auth_data=auth_data,
                db=self.db,
                quality=quality,
                threads=threads,
                auto_album=auto_album,
                log_callback=self.append_log,
                log_func=self.append_log,
                event_callback=self._handle_uploader_event
            )
            self.uploader.start_background_worker()
            self.upload_tray.set_thread_count(threads)

            # Initialize Watcher
            sync_folders = self.config_mgr.config.get("sync_folders", [])
            self.watcher = FolderWatcher(
                uploader=self.uploader,
                folders=sync_folders,
                log_func=self.append_log
            )

            if self.config_mgr.config.get("auto_sync", True):
                self.watcher.start()
                self.lbl_stat_status.configure(text=t("status_monitoring"), text_color="#4ade80")

            self._refresh_folder_list()
            self._refresh_stats()
            self.append_log(f"System ready! Multi-threaded engine ({threads} threads) activated.", "SUCCESS")

        except Exception as e:
            self.append_log(f"Engine initialization error: {e}", "ERROR")
            messagebox.showerror(t("alert_error"), f"Could not connect account:\n{e}")

    def _on_change_quick_threads(self, choice: str):
        t_str = choice.split(" ")[0]
        if t_str.isdigit():
            threads = int(t_str)
            self.config_mgr.config["threads"] = threads
            self.config_mgr.save_config()
            if self.uploader:
                self.uploader.update_settings(threads=threads)
                self.uploader.start_background_worker()
            self.upload_tray.set_thread_count(threads)
            self.append_log(f"Switched to {threads} concurrent threads.", "INFO")

    def _open_login_dialog(self):
        LoginDialog(self, self.config_mgr, on_success=self._on_login_success)

    def _on_login_success(self, email: str):
        self.append_log(f"Successfully signed in: {email}", "SUCCESS")
        self._init_engine()

    def _refresh_folder_list(self):
        for widget in self.folder_list_frame.winfo_children():
            widget.destroy()

        folders = self.config_mgr.config.get("sync_folders", [])
        if not folders:
            ctk.CTkLabel(
                self.folder_list_frame,
                text=t("folders_empty"),
                text_color="gray"
            ).pack(pady=20)
            return

        for idx, folder in enumerate(folders):
            row = ctk.CTkFrame(self.folder_list_frame, fg_color="#18181b", corner_radius=8)
            row.pack(fill="x", padx=6, pady=4)

            lbl = ctk.CTkLabel(row, text=f"📁  {folder}", font=ctk.CTkFont(size=12), anchor="w")
            lbl.pack(side="left", padx=12, pady=8)

            btn_del = ctk.CTkButton(
                row,
                text=t("btn_delete_folder"),
                width=70,
                height=26,
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                command=lambda f=folder: self._remove_sync_folder(f)
            )
            btn_del.pack(side="right", padx=8, pady=6)

    def _add_sync_folder(self):
        folder = filedialog.askdirectory(
            parent=self,
            title=t("dialog_select_folder_title")
        )
        if not folder:
            return
        folders = self.config_mgr.config.get("sync_folders", [])
        if folder not in folders:
            folders.append(folder)
            self.config_mgr.config["sync_folders"] = folders
            self.config_mgr.save_config()
            self._refresh_folder_list()
            if self.watcher:
                self.watcher.update_folders_async(folders)
            self.append_log(f"Added new monitored folder: {folder}", "SUCCESS")

            # Ask user if they want to scan and backup existing photos in this new folder
            answer = messagebox.askyesno(
                t("dialog_scan_existing_title"),
                t("dialog_scan_existing_msg", folder=Path(folder).name),
                parent=self
            )
            if answer and self.uploader:
                self._scan_single_folder_in_background(Path(folder))

    def _remove_sync_folder(self, folder: str):
        folders = self.config_mgr.config.get("sync_folders", [])
        if folder in folders:
            folders.remove(folder)
            self.config_mgr.config["sync_folders"] = folders
            self.config_mgr.save_config()
            self._refresh_folder_list()
            if self.watcher:
                self.watcher.update_folders_async(folders)
            self.append_log(f"Removed monitored folder: {folder}", "INFO")

    def _scan_single_folder_in_background(self, folder_path: Path):
        self.append_log(f"Scanning folder: {folder_path.name}...", "INFO")

        def task():
            found = []
            try:
                for root, _, files in os.walk(folder_path):
                    for f in files:
                        ext = os.path.splitext(f)[1].lower()
                        if ext in SUPPORTED_EXTENSIONS:
                            found.append(Path(root) / f)
            except Exception as e:
                self.after(0, lambda: self.append_log(f"Error scanning folder {folder_path.name}: {e}", "ERROR"))
                return

            if not found:
                self.after(0, lambda: self.append_log(f"No photos/videos found in '{folder_path.name}'.", "INFO"))
                return

            added = self.uploader.add_to_queue(found)
            self.uploader.start_background_worker()
            self.after(0, lambda: self.append_log(
                f"Added {added} files from '{folder_path.name}' to multi-threaded queue ({self.uploader.threads} threads).",
                "SUCCESS"
            ))

        threading.Thread(target=task, daemon=True).start()

    def _scan_all_folders_now(self):
        if not self.uploader:
            messagebox.showwarning(t("alert_warning"), t("alert_login_first"), parent=self)
            return

        folders = self.config_mgr.config.get("sync_folders", [])
        if not folders:
            messagebox.showinfo(t("alert_info"), t("dialog_no_monitored_folders"), parent=self)
            return

        self.append_log("Starting background scan of all monitored folders...", "INFO")

        def task():
            all_files = []
            for folder in folders:
                p = Path(folder)
                if p.exists() and p.is_dir():
                    try:
                        for root, _, files in os.walk(p):
                            for f in files:
                                ext = os.path.splitext(f)[1].lower()
                                if ext in SUPPORTED_EXTENSIONS:
                                    all_files.append(Path(root) / f)
                    except Exception:
                        pass

            if not all_files:
                self.after(0, lambda: messagebox.showinfo(
                    t("alert_info"),
                    t("dialog_no_media_found"),
                    parent=self
                ))
                return

            added = self.uploader.add_to_queue(all_files)
            self.uploader.start_background_worker()
            self.after(0, lambda: self.append_log(
                f"Scan complete. Added {added} files to multi-threaded upload queue.",
                "SUCCESS"
            ))

        threading.Thread(target=task, daemon=True).start()

    def _manual_upload_files(self):
        if not self.uploader:
            messagebox.showwarning(t("alert_warning"), t("alert_login_first"), parent=self)
            return
        files = filedialog.askopenfilenames(
            parent=self,
            title=t("dialog_select_files_title"),
            filetypes=[
                ("Media Files", "*.jpg *.jpeg *.png *.webp *.heic *.mp4 *.mov *.mkv *.avi *.dng *.cr2 *.nef"),
                ("All Files", "*.*")
            ]
        )
        if files:
            paths = [Path(f) for f in files]
            def task():
                added = self.uploader.add_to_queue(paths)
                self.uploader.start_background_worker()
                self.after(0, lambda: self.append_log(
                    f"Added {added} files to upload queue ({self.uploader.threads} threads).",
                    "INFO"
                ))
            threading.Thread(target=task, daemon=True).start()

    def _manual_upload_folder(self):
        if not self.uploader:
            messagebox.showwarning(t("alert_warning"), t("alert_login_first"), parent=self)
            return
        folder = filedialog.askdirectory(parent=self, title=t("dialog_select_folder_title"))
        if folder:
            self._scan_single_folder_in_background(Path(folder))

    def _toggle_pause(self):
        if not self.uploader:
            return
        if self._is_paused:
            self.uploader.resume()
            self.btn_pause.configure(text=t("btn_pause"), fg_color="#d97706")
            self._is_paused = False
        else:
            self.uploader.pause()
            self.btn_pause.configure(text=t("btn_resume"), fg_color="#16a34a")
            self._is_paused = True

    def _cancel_queue(self):
        if self.uploader:
            self.uploader.cancel()
            self.upload_tray.clear_all()
            self.progress_bar.set(0)
            self.lbl_current_file.configure(text=t("queue_cancelled"))

    def _on_toggle_auto_album(self):
        val = bool(self.switch_auto_album.get())
        self.config_mgr.config["auto_album"] = val
        self.config_mgr.save_config()
        if self.uploader:
            self.uploader.update_settings(auto_album=val)
        self.append_log(f"Auto-create Album by folder name: {'ENABLED' if val else 'DISABLED'}.", "INFO")

    def _clear_logs(self):
        self.log_textbox.delete("1.0", "end")

    def _save_settings(self):
        lang_choice = self.combo_language.get()
        lang_code = "vi" if "Việt" in lang_choice else "en"
        q_val = "original" if "Original" in self.combo_quality.get() else "saver"
        t_str = self.combo_threads.get().split(" ")[0]
        threads = int(t_str) if t_str.isdigit() else 4
        tray_val = bool(self.switch_tray.get())

        self.config_mgr.config["language"] = lang_code
        self.config_mgr.config["quality"] = q_val
        self.config_mgr.config["threads"] = threads
        self.config_mgr.config["minimize_to_tray"] = tray_val
        self.config_mgr.save_config()

        set_language(lang_code)
        self._apply_language()

        if self.uploader:
            self.uploader.update_settings(quality=q_val, threads=threads)
            self.uploader.start_background_worker()
        self.upload_tray.set_thread_count(threads)

        messagebox.showinfo(t("alert_success"), t("dialog_settings_saved"))
        self.append_log(f"Settings saved: Language={lang_code}, Threads={threads}, Quality={q_val}.", "SUCCESS")

    def _confirm_reset_statistics(self):
        answer = messagebox.askyesno(
            t("dialog_reset_confirm_title"),
            t("dialog_reset_confirm_msg"),
            parent=self
        )
        if not answer:
            return

        try:
            self.db.clear_history()
            self._refresh_stats()
            self.upload_tray.clear_all()
            self.progress_bar.set(0)
            self.lbl_current_file.configure(text=t("queue_ready_empty"))
            self.append_log("Statistics reset to 0 files / 0.00 GB.", "SUCCESS")
            messagebox.showinfo(t("alert_success"), t("dialog_reset_success"), parent=self)
        except Exception as e:
            self.append_log(f"Reset statistics error: {e}", "ERROR")
            messagebox.showerror(t("alert_error"), f"Could not reset statistics:\n{e}", parent=self)

    def _on_close(self):
        if self.watcher:
            self.watcher.stop()
        if self.uploader:
            try:
                self.uploader.flush_pending_albums(timeout=3.0)
            except Exception:
                pass
            self.uploader.cancel()
        self.destroy()
        sys.exit(0)
