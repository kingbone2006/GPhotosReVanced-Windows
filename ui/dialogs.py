"""Dialog windows for Google Photos ReVanced Windows edition.
Includes Google Account login modal with 1-Click Auto Login (Automatic CDP Token Capture),
Copy Token button, and fallback manual pasting.
"""

import os
import threading
from pathlib import Path
import customtkinter as ctk
from typing import Optional, Callable
from tkinter import messagebox, filedialog

from core.auth import exchange_oauth_token, validate_auth_data, ConfigManager
from core.auto_auth import AutoLoginService
from core.uploader import SUPPORTED_EXTENSIONS
from core.db import UploadDatabase
from core.i18n import t


class LoginDialog(ctk.CTkToplevel):
    def __init__(self, parent, config_mgr: ConfigManager, on_success: Optional[Callable[[str], None]] = None):
        super().__init__(parent)
        self.config_mgr = config_mgr
        self.on_success = on_success
        self.auto_auth_service = AutoLoginService()

        self.title(t("login_window_title"))
        self.geometry("680x620")
        self.minsize(620, 560)
        self.grab_set()  # Modal window
        self.focus_set()

        self.protocol("WM_DELETE_WINDOW", self._on_dialog_close)

        self._build_ui()

    def _build_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(20, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text=t("login_header"),
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(anchor="w")

        sub_label = ctk.CTkLabel(
            header_frame,
            text=t("login_header_desc"),
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        sub_label.pack(anchor="w", pady=(4, 0))

        # Tabs for methods
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=24, pady=10)

        self.tab_auto = self.tabview.add(t("tab_login_auto"))
        self.tab_manual = self.tabview.add(t("tab_login_manual"))

        self._build_auto_tab()
        self._build_manual_tab()

    def _build_auto_tab(self):
        tab = self.tab_auto

        # Description Box
        guide_box = ctk.CTkFrame(tab, fg_color="#18181b", corner_radius=8)
        guide_box.pack(fill="x", padx=10, pady=(10, 12))

        ctk.CTkLabel(
            guide_box,
            text=t("login_auto_guide"),
            font=ctk.CTkFont(size=12),
            text_color="#e4e4e7",
            justify="left"
        ).pack(anchor="w", padx=14, pady=12)

        # Big Action Button
        self.btn_auto_login = ctk.CTkButton(
            tab,
            text=t("btn_open_browser"),
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(weight="bold", size=14),
            height=42,
            command=self._start_auto_login
        )
        self.btn_auto_login.pack(fill="x", padx=10, pady=(4, 10))

        # Live Status Label
        self.lbl_auto_status = ctk.CTkLabel(
            tab,
            text=t("login_auto_status_ready"),
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8",
            wraplength=580
        )
        self.lbl_auto_status.pack(fill="x", padx=10, pady=(2, 8))

        # Token Captured Result Box (Initially hidden/empty)
        self.result_frame = ctk.CTkFrame(tab, fg_color="#18181b", corner_radius=8)
        self.result_frame.pack(fill="x", padx=10, pady=(4, 10))

        r_header = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        r_header.pack(fill="x", padx=12, pady=(10, 4))

        self.lbl_token_title = ctk.CTkLabel(
            r_header,
            text="Mã oauth_token thu nhận được:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f4f4f5"
        )
        self.lbl_token_title.pack(side="left")

        self.btn_copy_token = ctk.CTkButton(
            r_header,
            text="📋 Sao chép Token",
            width=130,
            height=26,
            fg_color="#3f3f46",
            hover_color="#52525b",
            font=ctk.CTkFont(size=11),
            command=self._copy_token_to_clipboard
        )
        self.btn_copy_token.pack(side="right")

        self.auto_token_entry = ctk.CTkEntry(
            self.result_frame,
            placeholder_text="Mã token sẽ tự động điền vào đây sau khi đăng nhập...",
            height=36,
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.auto_token_entry.pack(fill="x", padx=12, pady=(0, 10))

        # Final connect button
        self.btn_auto_connect = ctk.CTkButton(
            tab,
            text="🚀 Kết nối tài khoản ngay",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold", size=13),
            height=38,
            state="disabled",
            command=lambda: self._submit_token(self.auto_token_entry.get().strip())
        )
        self.btn_auto_connect.pack(fill="x", padx=10, pady=(4, 10))

    def _build_manual_tab(self):
        tab = self.tab_manual

        lbl_desc = ctk.CTkLabel(
            tab,
            text=t("login_manual_guide"),
            font=ctk.CTkFont(size=12),
            justify="left"
        )
        lbl_desc.pack(anchor="w", padx=10, pady=(10, 6))

        # Paste button
        btn_paste = ctk.CTkButton(
            tab,
            text="📋 " + ("Paste from Clipboard" if t("card_thread") == "Thread" else "Dán từ Clipboard"),
            width=200,
            height=28,
            fg_color="#3f3f46",
            hover_color="#52525b",
            font=ctk.CTkFont(size=12),
            command=self._paste_from_clipboard
        )
        btn_paste.pack(anchor="w", padx=10, pady=(0, 8))

        self.manual_text = ctk.CTkTextbox(tab, height=140, font=ctk.CTkFont(family="Consolas", size=11))
        self.manual_text.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        self.btn_manual_connect = ctk.CTkButton(
            tab,
            text=t("btn_submit_manual"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            font=ctk.CTkFont(weight="bold", size=13),
            height=38,
            command=self._submit_manual
        )
        self.btn_manual_connect.pack(fill="x", padx=10, pady=(4, 10))

    # ------------------ Auto-Login Logic ------------------

    def _start_auto_login(self):
        self.btn_auto_login.configure(state="disabled", text="⏳ Đang mở cửa sổ đăng nhập...")
        self.lbl_auto_status.configure(
            text="Đang khởi động cửa sổ Google an toàn...",
            text_color="#38bdf8"
        )

        def on_status(msg: str):
            self.after(0, lambda: self.lbl_auto_status.configure(text=msg, text_color="#38bdf8"))

        def on_token(token: str):
            self.after(0, lambda: self._on_token_captured(token))

        def on_error(err: str):
            self.after(0, lambda: self._on_auto_error(err))

        self.auto_auth_service.start(
            on_status=on_status,
            on_token_captured=on_token,
            on_error=on_error
        )

    def _on_token_captured(self, token: str):
        self.auto_token_entry.delete(0, "end")
        self.auto_token_entry.insert(0, token)
        self.btn_auto_connect.configure(state="normal")
        self.btn_auto_login.configure(state="normal", text="🌐 Đăng nhập lại nếu cần")

        self.lbl_auto_status.configure(
            text="🎉 ĐÃ LẤY TOKEN THÀNH CÔNG! Đang tự động kết nối tài khoản...",
            text_color="#4ade80"
        )
        # Automatically connect after 1 second
        self.after(1000, lambda: self._submit_token(token))

    def _on_auto_error(self, err_msg: str):
        self.btn_auto_login.configure(state="normal", text="🌐 Mở cửa sổ đăng nhập Google (Tự bắt Token)")
        self.lbl_auto_status.configure(text=f"⚠️ {err_msg}", text_color="#ef4444")

    def _copy_token_to_clipboard(self):
        token = self.auto_token_entry.get().strip()
        if token:
            self.clipboard_clear()
            self.clipboard_append(token)
            messagebox.showinfo("Đã sao chép", "Đã sao chép mã oauth_token vào bộ nhớ tạm (Clipboard)!")
        else:
            messagebox.showwarning("Chưa có token", "Chưa có mã token để sao chép. Vui lòng đăng nhập trước.")

    def _paste_from_clipboard(self):
        try:
            val = self.clipboard_get()
            self.manual_text.delete("1.0", "end")
            self.manual_text.insert("1.0", val.strip())
        except Exception:
            messagebox.showwarning("Lỗi", "Không thể đọc dữ liệu từ Clipboard.")

    # ------------------ Token Submission Logic ------------------

    def _submit_token(self, token: str):
        token = token.strip()
        if not token:
            messagebox.showwarning("Cảnh báo", "Mã token không được để trống!")
            return

        self.btn_auto_connect.configure(state="disabled", text="⏳ Đang kích hoạt quyền Pixel XL...")
        self.lbl_auto_status.configure(text="Đang trao đổi token và kiểm tra quyền Google Photos...", text_color="#38bdf8")

        def run():
            try:
                res = exchange_oauth_token(token)
                email = res["email"]
                auth_data = res["auth_data"]

                # Validate with Google Photos API
                validate_auth_data(auth_data)

                # Save to config
                self.config_mgr.add_or_update_account(email, auth_data)

                self.after(0, lambda: self._on_login_completed(email))
            except Exception as e:
                self.after(0, lambda: self._on_login_failed(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _submit_manual(self):
        raw = self.manual_text.get("1.0", "end").strip()
        if not raw:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập token hoặc chuỗi auth_data!")
            return

        self.btn_manual_connect.configure(state="disabled", text="⏳ Đang xác thực...")

        def run():
            try:
                # Check if it's already full auth_data
                if "androidId=" in raw and "Token=" in raw:
                    auth_data = raw
                    val = validate_auth_data(auth_data)
                    email = val["email"]
                else:
                    # Treat as oauth_token
                    res = exchange_oauth_token(raw)
                    email = res["email"]
                    auth_data = res["auth_data"]
                    validate_auth_data(auth_data)

                self.config_mgr.add_or_update_account(email, auth_data)
                self.after(0, lambda: self._on_login_completed(email))
            except Exception as e:
                self.after(0, lambda: self._on_login_failed(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _on_login_completed(self, email: str):
        messagebox.showinfo(
            "Thành công",
            f"🎉 Đã kết nối tài khoản Google: {email}\n\n"
            f"Thiết bị: Giả lập Google Pixel XL\n"
            f"Quyền: Sao lưu trọn đời KHÔNG GIỚI HẠN DUNG LƯỢNG!"
        )
        if self.on_success:
            self.on_success(email)
        self._on_dialog_close()

    def _on_login_failed(self, error_msg: str):
        self.btn_auto_connect.configure(state="normal", text="🚀 Kết nối tài khoản ngay")
        self.btn_manual_connect.configure(state="normal", text="✅ Xác thực & Kết nối")
        self.lbl_auto_status.configure(text=f"Lỗi: {error_msg}", text_color="#ef4444")
        messagebox.showerror("Đăng nhập thất bại", f"Không thể xác thực tài khoản Google:\n\n{error_msg}")

    def _on_dialog_close(self):
        self.auto_auth_service.cancel()
        self.destroy()


class AccountManagerDialog(ctk.CTkToplevel):
    """Dialog allowing users to view, 1-click switch between saved Google accounts,
    remove an existing account, or add a new account.
    """
    def __init__(
        self,
        parent,
        config_mgr: ConfigManager,
        on_switch: Optional[Callable[[str], None]] = None,
        on_add_new: Optional[Callable[[], None]] = None
    ):
        super().__init__(parent)
        self.config_mgr = config_mgr
        self.on_switch = on_switch
        self.on_add_new = on_add_new

        self.title(t("account_manager_title"))
        self.geometry("560x480")
        self.minsize(500, 380)
        self.grab_set()
        self.focus_set()

        self._build_ui()

    def _build_ui(self):
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(20, 10))

        title_lbl = ctk.CTkLabel(
            header_frame,
            text=t("account_manager_header"),
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_lbl.pack(anchor="w")

        desc_lbl = ctk.CTkLabel(
            header_frame,
            text=t("account_manager_desc"),
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        desc_lbl.pack(anchor="w", pady=(4, 0))

        # Scrollable list of accounts
        self.accounts_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="#18181b",
            corner_radius=10
        )
        self.accounts_scroll.pack(fill="both", expand=True, padx=24, pady=(10, 14))

        # Bottom Action Bar
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=24, pady=(0, 20))

        btn_add = ctk.CTkButton(
            bottom_frame,
            text=t("account_btn_add"),
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(weight="bold", size=13),
            height=38,
            command=self._handle_add_new
        )
        btn_add.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_close = ctk.CTkButton(
            bottom_frame,
            text=t("btn_cancel"),
            fg_color="#3f3f46",
            hover_color="#52525b",
            font=ctk.CTkFont(size=13),
            height=38,
            width=90,
            command=self.destroy
        )
        btn_close.pack(side="right")

        self._render_accounts()

    def _render_accounts(self):
        # Clear existing rows
        for child in self.accounts_scroll.winfo_children():
            child.destroy()

        accounts = self.config_mgr.config.get("accounts", [])
        active_acc = self.config_mgr.get_active_account()
        active_email = (active_acc.get("email") or "").strip().lower() if active_acc else ""

        if not accounts:
            empty_lbl = ctk.CTkLabel(
                self.accounts_scroll,
                text=t("account_no_saved"),
                font=ctk.CTkFont(size=13),
                text_color="gray"
            )
            empty_lbl.pack(pady=40)
            return

        for acc in accounts:
            email = (acc.get("email") or "").strip()
            is_active = (email.lower() == active_email)

            card = ctk.CTkFrame(
                self.accounts_scroll,
                fg_color="#064e3b" if is_active else "#27272a",
                border_width=1,
                border_color="#059669" if is_active else "#3f3f46",
                corner_radius=8
            )
            card.pack(fill="x", padx=6, pady=6)

            # Left side: Icon + Email info
            left_frame = ctk.CTkFrame(card, fg_color="transparent")
            left_frame.pack(side="left", fill="both", expand=True, padx=12, pady=10)

            user_icon = ctk.CTkLabel(
                left_frame,
                text="👤",
                font=ctk.CTkFont(size=20)
            )
            user_icon.pack(side="left", padx=(0, 10))

            info_col = ctk.CTkFrame(left_frame, fg_color="transparent")
            info_col.pack(side="left", fill="y", anchor="w")

            email_lbl = ctk.CTkLabel(
                info_col,
                text=email,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#ffffff",
                anchor="w"
            )
            email_lbl.pack(anchor="w")

            if is_active:
                badge_lbl = ctk.CTkLabel(
                    info_col,
                    text=t("account_active_badge"),
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#34d399",
                    anchor="w"
                )
                badge_lbl.pack(anchor="w")
            else:
                sub_lbl = ctk.CTkLabel(
                    info_col,
                    text="Pixel XL Unlimited Backup",
                    font=ctk.CTkFont(size=11),
                    text_color="#9ca3af",
                    anchor="w"
                )
                sub_lbl.pack(anchor="w")

            # Right side: Action buttons
            right_frame = ctk.CTkFrame(card, fg_color="transparent")
            right_frame.pack(side="right", padx=12, pady=10)

            if not is_active:
                btn_switch = ctk.CTkButton(
                    right_frame,
                    text=t("account_switch_to"),
                    width=74,
                    height=30,
                    fg_color="#0284c7",
                    hover_color="#0369a1",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    command=lambda e=email: self._handle_switch(e)
                )
                btn_switch.pack(side="left", padx=(0, 6))

            btn_delete = ctk.CTkButton(
                right_frame,
                text="🗑️",
                width=32,
                height=30,
                fg_color="#7f1d1d",
                hover_color="#991b1b",
                font=ctk.CTkFont(size=12),
                command=lambda e=email: self._handle_remove(e)
            )
            btn_delete.pack(side="left")

    def _handle_switch(self, email: str):
        self.destroy()
        if self.on_switch:
            self.on_switch(email)

    def _handle_remove(self, email: str):
        confirm = messagebox.askyesno(
            t("confirm_remove_account_title"),
            t("confirm_remove_account_msg", email=email),
            parent=self
        )
        if not confirm:
            return

        # Check if the account being removed was active
        active_acc = self.config_mgr.get_active_account()
        was_active = bool(active_acc and active_acc.get("email", "").lower() == email.lower())

        self.config_mgr.remove_account(email)

        accounts = self.config_mgr.config.get("accounts", [])
        if was_active:
            # If there's another account remaining, switch to it
            new_active = self.config_mgr.get_active_account()
            if new_active and self.on_switch:
                self.on_switch(new_active.get("email", ""))
            elif not accounts and self.on_switch:
                self.on_switch("")

        if not accounts:
            self.destroy()
            if self.on_add_new:
                self.on_add_new()
        else:
            self._render_accounts()

    def _handle_add_new(self):
        self.destroy()
        if self.on_add_new:
            self.on_add_new()


class UnbackupDialog(ctk.CTkToplevel):
    """Confirmation and progress dialog for Unbackup Cloud (undoing backup on Google Photos).
    Deletes all uploaded photos/videos and clears albums from Google Photos matching files on the machine.
    """
    def __init__(
        self,
        parent,
        config_mgr: ConfigManager,
        db,
        uploader,
        on_completed: Optional[Callable[[int], None]] = None
    ):
        super().__init__(parent)
        self.config_mgr = config_mgr
        self.db = db
        self.uploader = uploader
        self.on_completed = on_completed

        self.title(t("unbackup_dialog_title"))
        self.geometry("640x630")
        self.minsize(580, 540)
        self.grab_set()
        self.focus_set()

        self._is_running = False
        self._folder_files = []

        active_acc = self.config_mgr.get_active_account()
        self.email = active_acc.get("email", "") if active_acc else ""
        self.info = self.db.get_account_unbackup_info(self.email)

        self._build_ui()
        self._start_folder_scan()

    def _build_ui(self):
        # Header Frame
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 8))

        ctk.CTkLabel(
            header,
            text=t("unbackup_header"),
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#ef4444"
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text=t("unbackup_desc"),
            font=ctk.CTkFont(size=12),
            text_color="gray",
            wraplength=580,
            justify="left"
        ).pack(anchor="w", pady=(4, 0))

        # Content Frame
        content = ctk.CTkFrame(self, fg_color="#18181b", corner_radius=10)
        content.pack(fill="both", expand=True, padx=24, pady=8)

        # 1. Account & Scan Status Box
        stats_box = ctk.CTkFrame(content, fg_color="#27272a", corner_radius=8)
        stats_box.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            stats_box,
            text=f"👤 Tài khoản: {self.email}",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#ffffff"
        ).pack(anchor="w", padx=14, pady=(8, 2))

        # Live folder scan status
        self.lbl_folder_stat = ctk.CTkLabel(
            stats_box,
            text="🔍 Đang tự động quét ảnh/video trên máy tính...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#fbbf24",
            anchor="w",
            wraplength=560,
            justify="left"
        )
        self.lbl_folder_stat.pack(anchor="w", padx=14, pady=2)

        # DB history count
        db_cnt = self.info["total_files"]
        db_gb = self.info["total_gb"]
        self.lbl_db_stat = ctk.CTkLabel(
            stats_box,
            text=f"💾 Lịch sử ứng dụng đã ghi nhận: {db_cnt:,} file ({db_gb:.2f} GB)",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa",
            anchor="w"
        )
        self.lbl_db_stat.pack(anchor="w", padx=14, pady=(2, 8))

        # 2. Scope Selection Box
        scope_box = ctk.CTkFrame(content, fg_color="#27272a", corner_radius=8)
        scope_box.pack(fill="x", padx=16, pady=4)

        ctk.CTkLabel(
            scope_box,
            text="🎯 Phạm vi huỷ sao lưu:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f4f4f5"
        ).pack(anchor="w", padx=14, pady=(8, 4))

        self.scope_var = ctk.StringVar(value="folder")

        self.rb_scope_folder = ctk.CTkRadioButton(
            scope_box,
            text=t("unbackup_scope_folder", count=0),
            value="folder",
            variable=self.scope_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8"
        )
        self.rb_scope_folder.pack(anchor="w", padx=14, pady=2)

        self.rb_scope_db = ctk.CTkRadioButton(
            scope_box,
            text=t("unbackup_scope_db", count=db_cnt),
            value="db",
            variable=self.scope_var,
            font=ctk.CTkFont(size=12),
            text_color="#e4e4e7"
        )
        self.rb_scope_db.pack(anchor="w", padx=14, pady=2)

        # Button to browse custom folder
        self.btn_browse = ctk.CTkButton(
            scope_box,
            text=t("btn_choose_other_folder"),
            fg_color="#374151",
            hover_color="#4b5563",
            height=28,
            font=ctk.CTkFont(size=11),
            command=self._choose_custom_folder
        )
        self.btn_browse.pack(anchor="w", padx=14, pady=(4, 8))

        # 3. Mode Selection (Trash vs Permanent)
        mode_box = ctk.CTkFrame(content, fg_color="#27272a", corner_radius=8)
        mode_box.pack(fill="x", padx=16, pady=4)

        self.mode_var = ctk.StringVar(value="trash")

        rb_trash = ctk.CTkRadioButton(
            mode_box,
            text=t("unbackup_mode_trash"),
            value="trash",
            variable=self.mode_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f4f4f5"
        )
        rb_trash.pack(anchor="w", padx=14, pady=(8, 2))

        ctk.CTkLabel(
            mode_box,
            text=t("unbackup_mode_trash_desc"),
            font=ctk.CTkFont(size=11),
            text_color="#9ca3af",
            wraplength=540,
            justify="left"
        ).pack(anchor="w", padx=36, pady=(0, 4))

        rb_perm = ctk.CTkRadioButton(
            mode_box,
            text=t("unbackup_mode_permanent"),
            value="permanent",
            variable=self.mode_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f87171"
        )
        rb_perm.pack(anchor="w", padx=14, pady=(2, 2))

        ctk.CTkLabel(
            mode_box,
            text=t("unbackup_mode_permanent_desc"),
            font=ctk.CTkFont(size=11),
            text_color="#9ca3af",
            wraplength=540,
            justify="left"
        ).pack(anchor="w", padx=36, pady=(0, 8))

        # 4. Safety Notice Box
        safety_box = ctk.CTkFrame(content, fg_color="#064e3b", border_width=1, border_color="#059669", corner_radius=8)
        safety_box.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(
            safety_box,
            text=t("unbackup_safety_notice"),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#a7f3d0",
            wraplength=550,
            justify="left"
        ).pack(anchor="w", padx=12, pady=6)

        # Progress bar (Hidden initially)
        self.progress_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=16, pady=2)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=10)
        self.progress_bar.set(0)
        self.lbl_progress = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#38bdf8"
        )

        # Action Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(8, 16))

        self.btn_cancel = ctk.CTkButton(
            btn_frame,
            text=t("btn_cancel"),
            fg_color="#3f3f46",
            hover_color="#52525b",
            height=38,
            width=100,
            command=self.destroy
        )
        self.btn_cancel.pack(side="right", padx=(10, 0))

        self.btn_start = ctk.CTkButton(
            btn_frame,
            text=t("unbackup_btn_start"),
            fg_color="#dc2626",
            hover_color="#b91c1c",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=38,
            command=self._start_unbackup
        )
        self.btn_start.pack(side="right", fill="x", expand=True)

    def _start_folder_scan(self):
        sync_folders = self.config_mgr.config.get("sync_folders", [])
        if not sync_folders:
            self.lbl_folder_stat.configure(
                text="Chưa có thư mục đồng bộ nào được thiết lập. Hãy chọn thư mục bên dưới.",
                text_color="#a1a1aa"
            )
            self.scope_var.set("db")
            if self.info["total_files"] == 0:
                self.btn_start.configure(state="disabled")
            return

        folder_names = ", ".join([Path(f).name for f in sync_folders])
        self.lbl_folder_stat.configure(
            text=t("unbackup_scan_machine", folder=folder_names),
            text_color="#fbbf24"
        )

        def scan_worker():
            found = []
            for s in sync_folders:
                p = Path(s)
                if p.exists() and p.is_dir():
                    try:
                        for root, _, files in os.walk(p):
                            for f in files:
                                ext = os.path.splitext(f)[1].lower()
                                if ext in SUPPORTED_EXTENSIONS:
                                    found.append(Path(root) / f)
                    except Exception:
                        pass

            self.after(0, lambda: self._on_folder_scan_finished(found, folder_names))

        threading.Thread(target=scan_worker, daemon=True).start()

    def _on_folder_scan_finished(self, found: list, folder_names: str):
        self._folder_files = found
        cnt = len(found)
        if cnt > 0:
            self.lbl_folder_stat.configure(
                text=t("unbackup_found_folder_files", count=cnt, folder=folder_names),
                text_color="#4ade80"
            )
            self.rb_scope_folder.configure(
                text=t("unbackup_scope_folder", count=cnt),
                state="normal"
            )
            self.scope_var.set("folder")
            self.btn_start.configure(state="normal")
        else:
            self.lbl_folder_stat.configure(
                text=f"Không tìm thấy ảnh/video nào trong {folder_names}",
                text_color="#a1a1aa"
            )
            self.scope_var.set("db")
            if self.info["total_files"] == 0:
                self.btn_start.configure(state="disabled")

    def _choose_custom_folder(self):
        f = filedialog.askdirectory(parent=self, title=t("dialog_select_folder_title"))
        if not f:
            return
        p = Path(f)
        self.lbl_folder_stat.configure(
            text=f"Đang quét thư mục: {p.name}...",
            text_color="#fbbf24"
        )

        def scan_worker():
            found = []
            if p.exists() and p.is_dir():
                try:
                    for root, _, files in os.walk(p):
                        for file in files:
                            ext = os.path.splitext(file)[1].lower()
                            if ext in SUPPORTED_EXTENSIONS:
                                found.append(Path(root) / file)
                except Exception:
                    pass
            self.after(0, lambda: self._on_folder_scan_finished(found, p.name))

        threading.Thread(target=scan_worker, daemon=True).start()

    def _start_unbackup(self):
        if self._is_running:
            return

        scope = self.scope_var.get()
        permanent = (self.mode_var.get() == "permanent")

        # Determine target list
        if scope == "folder" and self._folder_files:
            target_mode = "folder"
            total_items = len(self._folder_files)
        elif self.info["hashes"]:
            target_mode = "db"
            total_items = len(self.info["hashes"])
        elif self._folder_files:
            target_mode = "folder"
            total_items = len(self._folder_files)
        else:
            messagebox.showinfo(t("alert_info"), t("unbackup_no_items"), parent=self)
            return

        self._is_running = True
        self.btn_start.configure(state="disabled", text="⏳ Đang tiến hành huỷ sao lưu...")
        self.btn_cancel.configure(state="disabled")
        self.btn_browse.configure(state="disabled")

        self.progress_bar.pack(fill="x", pady=(4, 4))
        self.lbl_progress.pack(anchor="w", pady=(0, 4))
        self.progress_bar.set(0)

        def run():
            try:
                processed = 0
                success_total = 0

                if target_mode == "folder":
                    batch_size = 500
                    files_list = self._folder_files
                    total_cnt = len(files_list)

                    for i in range(0, total_cnt, batch_size):
                        chunk = files_list[i : i + batch_size]
                        chunk_hashes = []
                        for file_path in chunk:
                            try:
                                h = UploadDatabase.calculate_sha1(file_path)
                                chunk_hashes.append(h)
                            except Exception:
                                continue

                        if chunk_hashes:
                            s_cnt, _ = self.uploader.unbackup_remote_media(
                                sha1_hashes=chunk_hashes,
                                permanent=permanent
                            )
                            success_total += s_cnt

                        processed = min(i + len(chunk), total_cnt)
                        pct = processed / total_cnt if total_cnt > 0 else 0
                        txt = t("unbackup_in_progress", current=processed, total=total_cnt, percent=int(pct * 100))
                        self.after(0, lambda p=pct, m=txt: self._update_ui_progress(p, m))
                else:
                    # Database hashes
                    hashes = self.info["hashes"]
                    def progress(curr, total):
                        pct = curr / total if total > 0 else 0
                        txt = t("unbackup_in_progress", current=curr, total=total, percent=int(pct * 100))
                        self.after(0, lambda p=pct, m=txt: self._update_ui_progress(p, m))

                    s_cnt, _ = self.uploader.unbackup_remote_media(
                        sha1_hashes=hashes,
                        permanent=permanent,
                        progress_callback=progress
                    )
                    success_total = s_cnt

                # Clear DB records for this account
                self.db.clear_account_data(self.email)

                self.after(0, lambda: self._on_success(success_total))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _update_ui_progress(self, pct: float, txt: str):
        self.progress_bar.set(pct)
        self.lbl_progress.configure(text=txt)

    def _on_success(self, count: int):
        self._is_running = False
        messagebox.showinfo(
            t("alert_success"),
            t("unbackup_completed_msg", count=count),
            parent=self
        )
        if self.on_completed:
            self.on_completed(count)
        self.destroy()

    def _on_error(self, err: str):
        self._is_running = False
        self.btn_start.configure(state="normal", text=t("unbackup_btn_start"))
        self.btn_cancel.configure(state="normal")
        self.btn_browse.configure(state="normal")
        messagebox.showerror(
            t("alert_error"),
            t("unbackup_error", error=err),
            parent=self
        )



