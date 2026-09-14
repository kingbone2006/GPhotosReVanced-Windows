"""Internationalization (i18n) module for Google Photos ReVanced Windows edition.
Provides multi-language support (English default, Vietnamese) with dynamic switching.
"""

from typing import Dict, Any

_CURRENT_LANGUAGE = "en"  # Default: English

STRINGS: Dict[str, Dict[str, str]] = {
    # ------------------ Header & Branding ------------------
    "app_title": {
        "en": "Google Photos ReVanced",
        "vi": "Google Photos ReVanced",
    },
    "badge_pixel": {
        "en": "PIXEL XL UNLIMITED",
        "vi": "PIXEL XL UNLIMITED",
    },
    "app_subtitle": {
        "en": "Unlimited Original Quality Cloud Backup • High-Speed Multi-Threading • Pixel XL Spoofing",
        "vi": "Sao lưu ảnh & video không giới hạn dung lượng • Đa luồng tốc độ cao • Giả lập Pixel XL",
    },
    "account_loading": {
        "en": "👤 Loading account...",
        "vi": "👤 Đang tải tài khoản...",
    },
    "account_unconnected": {
        "en": "👤 Not connected",
        "vi": "👤 Chưa kết nối",
    },
    "btn_connect_account": {
        "en": "Connect Account",
        "vi": "Kết nối tài khoản",
    },
    "btn_switch_account": {
        "en": "Switch Account",
        "vi": "Đổi tài khoản",
    },

    # ------------------ Navigation Tabs ------------------
    "tab_dashboard": {
        "en": "📊 Dashboard",
        "vi": "📊 Bảng điều khiển",
    },
    "tab_folders": {
        "en": "📁 Sync Folders",
        "vi": "📁 Thư mục đồng bộ",
    },
    "tab_logs": {
        "en": "📜 Activity Logs",
        "vi": "📜 Nhật ký hoạt động",
    },
    "tab_settings": {
        "en": "⚙️ Settings",
        "vi": "⚙️ Cài đặt",
    },

    # ------------------ Dashboard Tab ------------------
    "stats_header": {
        "en": "📊 ACTIVITY STATISTICS",
        "vi": "📊 THỐNG KÊ HOẠT ĐỘNG",
    },
    "btn_reset_stats_quick": {
        "en": "🔄 Reset Stats",
        "vi": "🔄 Đặt lại thống kê về 0",
    },
    "stat_backed_up": {
        "en": "🖼️ Backed Up",
        "vi": "🖼️ Đã sao lưu",
    },
    "stat_saved_storage": {
        "en": "💾 Storage Saved",
        "vi": "💾 Tiết kiệm dung lượng",
    },
    "stat_auto_sync": {
        "en": "⚡ Auto-Sync",
        "vi": "⚡ Tự động theo dõi",
    },
    "stat_emulated_device": {
        "en": "📱 Emulated Device",
        "vi": "📱 Thiết bị giả lập",
    },
    "status_monitoring": {
        "en": "Monitoring",
        "vi": "Đang theo dõi",
    },
    "status_paused": {
        "en": "Paused",
        "vi": "Tạm dừng",
    },
    "status_ready": {
        "en": "Ready",
        "vi": "Sẵn sàng",
    },

    # Action Bar
    "btn_select_files": {
        "en": "📁 Select Files",
        "vi": "📁 Chọn file",
    },
    "btn_upload_folder": {
        "en": "📂 Upload Folder",
        "vi": "📂 Tải thư mục",
    },
    "btn_pause": {
        "en": "⏸️ Pause",
        "vi": "⏸️ Tạm dừng",
    },
    "btn_resume": {
        "en": "▶️ Resume",
        "vi": "▶️ Tiếp tục",
    },
    "btn_cancel": {
        "en": "❌ Cancel",
        "vi": "❌ Huỷ",
    },
    "btn_reset_stats": {
        "en": "🔄 Reset Stats",
        "vi": "🔄 Reset thống kê",
    },
    "lbl_threads": {
        "en": "⚡ Upload Threads:",
        "vi": "⚡ Luồng tải:",
    },
    "thread_opt_1": {
        "en": "1 thread",
        "vi": "1 luồng",
    },
    "thread_opt_2": {
        "en": "2 threads",
        "vi": "2 luồng",
    },
    "thread_opt_4": {
        "en": "4 threads (Recommended)",
        "vi": "4 luồng (Khuyên dùng)",
    },
    "thread_opt_6": {
        "en": "6 threads (Ultra Speed)",
        "vi": "6 luồng (Siêu tốc)",
    },
    "thread_opt_8": {
        "en": "8 threads (Maximum)",
        "vi": "8 luồng (Tối đa)",
    },

    # Progress & Status Bar
    "queue_ready_empty": {
        "en": "Ready. No files in queue.",
        "vi": "Sẵn sàng. Chưa có file trong hàng đợi.",
    },
    "queue_cancelled": {
        "en": "Upload queue cancelled.",
        "vi": "Đã huỷ hàng đợi.",
    },
    "backup_mode_footer": {
        "en": "Backup Mode: Lifetime Free Unlimited Storage via Pixel XL Spoofing (Original Quality)",
        "vi": "Chế độ sao lưu: Miễn phí trọn đời không giới hạn dung lượng Pixel XL (Original Quality)",
    },

    # ------------------ Folders Tab ------------------
    "folders_guide": {
        "en": "💡 Monitored folders are watched in real time. Whenever new photos or videos are added, they are automatically backed up to Google Photos with zero storage quota impact.",
        "vi": "💡 Thư mục được chọn sẽ được giám sát tự động. Bất cứ khi nào có ảnh/video mới được thêm vào, app sẽ tự động sao lưu lên Google Photos mà không tốn dung lượng.",
    },
    "folders_empty": {
        "en": "No folders are currently being monitored. Click '+ Add Sync Folder' below.",
        "vi": "Chưa có thư mục nào được giám sát. Nhấn '+ Thêm thư mục' bên dưới.",
    },
    "btn_add_folder": {
        "en": "➕ Add Sync Folder",
        "vi": "➕ Thêm thư mục theo dõi",
    },
    "btn_scan_all": {
        "en": "🔄 Scan All Folders Now",
        "vi": "🔄 Quét toàn bộ thư mục ngay",
    },
    "switch_auto_album": {
        "en": "Auto-create Album by folder name (Auto-Album)",
        "vi": "Tự động tạo Album theo tên thư mục (Auto-Album)",
    },
    "btn_delete_folder": {
        "en": "Remove",
        "vi": "Xoá",
    },

    # ------------------ Logs Tab ------------------
    "logs_header": {
        "en": "Real-time backup activity and diagnostic logs:",
        "vi": "Nhật ký hoạt động sao lưu theo thời gian thực:",
    },
    "btn_clear_logs": {
        "en": "🗑️ Clear Logs",
        "vi": "🗑️ Xoá nhật ký",
    },

    # ------------------ Settings Tab ------------------
    "settings_header": {
        "en": "Backup & System Preferences",
        "vi": "Tuỳ chọn sao lưu & Hệ thống",
    },
    "lbl_language": {
        "en": "Interface Language:",
        "vi": "Ngôn ngữ giao diện:",
    },
    "lbl_quality": {
        "en": "Upload Quality:",
        "vi": "Chất lượng tải lên:",
    },
    "quality_original": {
        "en": "Original Quality (Pixel XL Free Unlimited)",
        "vi": "Original Quality (Chất lượng gốc - Miễn phí Pixel XL)",
    },
    "quality_saver": {
        "en": "Storage Saver (Compressed)",
        "vi": "Storage Saver (Tiết kiệm dung lượng)",
    },
    "lbl_threads_setting": {
        "en": "Concurrent Upload Threads:",
        "vi": "Số luồng tải lên đồng thời:",
    },
    "switch_tray": {
        "en": "Minimize to System Tray when window is closed",
        "vi": "Thu nhỏ về khay hệ thống (System Tray) khi đóng cửa sổ",
    },
    "btn_save_settings": {
        "en": "💾 Save Settings",
        "vi": "💾 Lưu cấu hình cài đặt",
    },

    # Settings: Data Management
    "data_mgmt_header": {
        "en": "Data Management & Backup History",
        "vi": "Quản lý dữ liệu & Lịch sử sao lưu",
    },
    "data_mgmt_desc": {
        "en": "Reset statistics (Backed up files & storage saved) back to zero. Photos and albums on Google Photos remain 100% intact.",
        "vi": "Đặt lại số liệu thống kê (Số ảnh đã sao lưu & Dung lượng tiết kiệm) về 0. Ảnh trên Google Photos vẫn được bảo toàn nguyên vẹn 100%.",
    },
    "btn_reset_data": {
        "en": "🗑️ Clear History & Reset Stats to 0",
        "vi": "🗑️ Xoá lịch sử & Đặt lại thống kê về 0",
    },

    # ------------------ Footer ------------------
    "app_footer": {
        "en": "Google Photos ReVanced for Windows • Emulated as Google Pixel XL • Multi-Threaded Engine",
        "vi": "Google Photos ReVanced for Windows • Emulated as Google Pixel XL • Multi-Threaded Engine",
    },

    # ------------------ Upload Tray & Card ------------------
    "card_thread": {
        "en": "Thread",
        "vi": "Luồng",
    },
    "card_waiting": {
        "en": "Waiting...",
        "vi": "Đang chờ...",
    },
    "card_uploaded": {
        "en": "Uploaded ✓",
        "vi": "Đã tải lên ✓",
    },
    "card_exists": {
        "en": "Already on Cloud ✓",
        "vi": "Đã có sẵn ✓",
    },
    "card_done": {
        "en": "✓ Done",
        "vi": "✓ Xong",
    },

    # ------------------ Dialogs & Alerts ------------------
    "alert_login_first": {
        "en": "Please connect a Google account first!",
        "vi": "Vui lòng kết nối tài khoản trước!",
    },
    "alert_warning": {
        "en": "Warning",
        "vi": "Cảnh báo",
    },
    "alert_info": {
        "en": "Information",
        "vi": "Thông báo",
    },
    "alert_error": {
        "en": "Error",
        "vi": "Lỗi",
    },
    "alert_success": {
        "en": "Success",
        "vi": "Thành công",
    },
    "dialog_scan_existing_title": {
        "en": "Scan Existing Media",
        "vi": "Quét ảnh có sẵn",
    },
    "dialog_scan_existing_msg": {
        "en": "Would you like to scan and back up existing photos/videos in folder '{folder}' right now?",
        "vi": "Bạn có muốn quét và sao lưu các ảnh/video hiện có sẵn trong thư mục '{folder}' ngay bây giờ không?",
    },
    "dialog_reset_confirm_title": {
        "en": "Confirm Statistics Reset",
        "vi": "Xác nhận đặt lại thống kê",
    },
    "dialog_reset_confirm_msg": {
        "en": "Are you sure you want to reset backup statistics (files and saved storage) back to zero?\n\n• This will clear local tracking history on this computer.\n• Photos and albums already backed up to Google Photos will remain 100% intact.",
        "vi": "Bạn có chắc chắn muốn đặt lại số liệu thống kê (Số file đã sao lưu & Dung lượng tiết kiệm) về 0 không?\n\n• Thao tác này sẽ xoá lịch sử theo dõi cục bộ trên máy tính.\n• Ảnh và Album đã tải lên Google Photos vẫn được bảo toàn nguyên vẹn 100%.",
    },
    "dialog_reset_success": {
        "en": "Statistics successfully reset to 0 files / 0.00 GB!",
        "vi": "Đã đặt lại số liệu thống kê về 0 thành công!",
    },
    "dialog_settings_saved": {
        "en": "Settings saved successfully!",
        "vi": "Đã lưu cài đặt thành công!",
    },
    "dialog_no_monitored_folders": {
        "en": "No folders are currently being monitored.",
        "vi": "Chưa có thư mục nào được giám sát.",
    },
    "dialog_no_media_found": {
        "en": "No photos or videos found in the selected folders.",
        "vi": "Không tìm thấy ảnh hoặc video trong các thư mục đã chọn.",
    },
    "dialog_select_folder_title": {
        "en": "Select folder containing photos/videos for automatic backup",
        "vi": "Chọn thư mục chứa ảnh/video cần tự động sao lưu",
    },
    "dialog_select_files_title": {
        "en": "Select photos or videos to upload to Google Photos",
        "vi": "Chọn ảnh hoặc video tải lên Google Photos",
    },

    # ------------------ Login Dialog ------------------
    "login_window_title": {
        "en": "Google Photos ReVanced - Account Sign In",
        "vi": "Đăng nhập tài khoản Google Photos ReVanced",
    },
    "login_header": {
        "en": "Connect Google Photos Account",
        "vi": "Kết nối tài khoản Google Photos",
    },
    "login_header_desc": {
        "en": "The application emulates a Google Pixel XL to enable lifetime unlimited cloud storage.",
        "vi": "Ứng dụng sẽ giả lập Google Pixel XL để kích hoạt sao lưu không giới hạn dung lượng.",
    },
    "tab_login_auto": {
        "en": "⚡ 1-Click Auto Login (Recommended)",
        "vi": "⚡ Đăng nhập tự động 1-Click (Khuyên dùng)",
    },
    "tab_login_manual": {
        "en": "✍️ Manual Paste (Token / Auth Data)",
        "vi": "✍️ Dán thủ công (Token / Auth Data)",
    },
    "login_auto_guide": {
        "en": "🚀 AUTOMATIC TOKEN CAPTURE UPON SIGN-IN:\n\n"
              "1. Click the 'Open Google Sign-in Window' button below.\n"
              "2. Sign in with your Google account in the browser window.\n"
              "3. Click 'I agree' when prompted.\n"
              "✨ The app will AUTOMATICALLY capture oauth_token without needing F12 or DevTools!",
        "vi": "🚀 TỰ ĐỘNG LẤY TOKEN SAU KHI ĐĂNG NHẬP:\n\n"
              "1. Nhấn nút 'Mở cửa sổ đăng nhập Google' bên dưới.\n"
              "2. Đăng nhập tài khoản Google của bạn tại cửa sổ vừa hiện ra.\n"
              "3. Nhấn 'I agree' (Tôi đồng ý) khi được hỏi.\n"
              "✨ Ứng dụng sẽ TỰ ĐỘNG BẮT MÃ oauth_token mà bạn không cần mở F12 hay làm gì thêm!",
    },
    "btn_open_browser": {
        "en": "🌐 Open Google Sign-in Window (Auto-Capture)",
        "vi": "🌐 Mở cửa sổ đăng nhập Google (Tự bắt Token)",
    },
    "login_auto_status_ready": {
        "en": "Ready. Click the button above to begin sign-in.",
        "vi": "Sẵn sàng. Nhấn nút phía trên để bắt đầu đăng nhập.",
    },
    "login_manual_guide": {
        "en": "📋 MANUAL TOKEN INSTRUCTIONS:\n"
              "If automatic capture is unavailable or you prefer manual entry:\n"
              "1. Open Edge or Chrome DevTools (F12) while accessing Google Embedded Setup.\n"
              "2. Filter Network tab for 'oauth_token' or 'auth/embedded/setup'.\n"
              "3. Copy and paste the oauth_token value or full response JSON below.",
        "vi": "📋 HƯỚNG DẪN LẤY TOKEN THỦ CÔNG:\n"
              "Nếu bạn muốn đăng nhập thủ công hoặc cơ chế tự động không khả dụng:\n"
              "1. Mở trang đăng nhập trong Edge/Chrome với DevTools (F12).\n"
              "2. Lọc thẻ Network tìm 'oauth_token' hoặc 'auth/embedded/setup'.\n"
              "3. Sao chép giá trị oauth_token hoặc toàn bộ nội dung phản hồi dán vào ô bên dưới.",
    },
    "btn_submit_manual": {
        "en": "🔐 Connect Account with Token",
        "vi": "🔐 Kết nối tài khoản",
    },
}


def set_language(lang: str) -> None:
    """Set the active language ('en' or 'vi')."""
    global _CURRENT_LANGUAGE
    if lang in ("en", "vi"):
        _CURRENT_LANGUAGE = lang


def get_language() -> str:
    """Get current active language code ('en' or 'vi')."""
    return _CURRENT_LANGUAGE


def t(key: str, default: str = None, **kwargs) -> str:
    """Retrieve localized string for given key. Supports optional keyword formatting."""
    entry = STRINGS.get(key)
    if entry is None:
        return default or key
    text = entry.get(_CURRENT_LANGUAGE) or entry.get("en") or default or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
