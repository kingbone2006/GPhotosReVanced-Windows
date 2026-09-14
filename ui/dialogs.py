"""Dialog windows for Google Photos ReVanced Windows edition.
Includes Google Account login modal with 1-Click Auto Login (Automatic CDP Token Capture),
Copy Token button, and fallback manual pasting.
"""

import threading
import customtkinter as ctk
from typing import Optional, Callable
from tkinter import messagebox

from core.auth import exchange_oauth_token, validate_auth_data, ConfigManager
from core.auto_auth import AutoLoginService
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
