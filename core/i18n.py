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
    "btn_start": {
        "en": "▶️ Start",
        "vi": "▶️ Bắt đầu",
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
    "btn_retry_failed": {
        "en": "🔄 Retry Failed Files",
        "vi": "🔄 Tải lại file lỗi",
    },
    "btn_retry_failed_scanning": {
        "en": "⏳ Scanning failed files...",
        "vi": "⏳ Đang quét file lỗi...",
    },
    "btn_sync_missing_albums": {
        "en": "🔍 Reconcile & Fill Albums (Photos & Videos)",
        "vi": "🔍 Đồng bộ Album Server (Ảnh & Video)",
    },
    "btn_sync_missing_albums_scanning": {
        "en": "⏳ Reconciling server albums...",
        "vi": "⏳ Đang kiểm tra Album trên Server...",
    },
    "btn_sync_albums_server": {
        "en": "🔍 Reconcile Server Albums",
        "vi": "🔍 Đồng bộ Album với Server",
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

    # ------------------ Account Manager Dialog ------------------
    "account_manager_title": {
        "en": "Google Accounts Manager",
        "vi": "Quản lý tài khoản Google",
    },
    "account_manager_header": {
        "en": "Switch Google Account",
        "vi": "Chuyển đổi tài khoản Google",
    },
    "account_manager_desc": {
        "en": "1-Click switch between previously signed-in accounts or add a new one.",
        "vi": "Đổi nhanh 1-Click giữa các tài khoản đã đăng nhập hoặc kết nối thêm tài khoản mới.",
    },
    "account_active_badge": {
        "en": "✓ Active",
        "vi": "✓ Đang sử dụng",
    },
    "account_switch_to": {
        "en": "Switch",
        "vi": "Chuyển",
    },
    "account_btn_add": {
        "en": "➕ Add Another Google Account",
        "vi": "➕ Thêm tài khoản Google mới",
    },
    "account_no_saved": {
        "en": "No accounts saved yet.",
        "vi": "Chưa có tài khoản nào được lưu.",
    },
    "confirm_remove_account_title": {
        "en": "Confirm Account Removal",
        "vi": "Xác nhận xoá tài khoản",
    },
    "confirm_remove_account_msg": {
        "en": "Are you sure you want to remove '{email}' from saved accounts?\n\n• You will need to sign in again to use this account.\n• Files already uploaded to Google Photos will remain safe.",
        "vi": "Bạn có chắc chắn muốn xoá tài khoản '{email}' khỏi danh sách lưu không?\n\n• Bạn sẽ cần đăng nhập lại nếu muốn sử dụng tài khoản này.\n• Ảnh/video đã sao lưu lên Google Photos vẫn được giữ nguyên an toàn.",
    },
    "log_account_switched": {
        "en": "Active account switched to: {email}",
        "vi": "Đã đổi sang tài khoản: {email}",
    },
    "log_account_already_active": {
        "en": "Account '{email}' is already active.",
        "vi": "Tài khoản '{email}' hiện đang được sử dụng.",
    },

    # ------------------ Unbackup Cloud Feature ------------------
    "btn_unbackup_cloud": {
        "en": "🗑️ Unbackup Cloud",
        "vi": "🗑️ Huỷ sao lưu",
    },
    "unbackup_dialog_title": {
        "en": "Google Photos - Cloud Unbackup",
        "vi": "Huỷ sao lưu trên Google Photos",
    },
    "unbackup_header": {
        "en": "Unbackup Photos & Albums from Cloud",
        "vi": "Huỷ sao lưu & Xoá ảnh/album trên Cloud",
    },
    "unbackup_desc": {
        "en": "Automatically delete all backed-up photos and videos from Google Photos matching your computer files.",
        "vi": "Tự động dọn sạch toàn bộ ảnh và video đã tải lên Google Photos tương ứng với dữ liệu trên máy tính.",
    },
    "unbackup_stat_files": {
        "en": "🖼️ Found {count:,} backed-up photos/videos ({gb:.2f} GB)",
        "vi": "🖼️ Đã tìm thấy {count:,} ảnh/video đã sao lưu ({gb:.2f} GB)",
    },
    "unbackup_stat_albums": {
        "en": "📁 Found {count} album(s) created on Google Photos",
        "vi": "📁 Đã tìm thấy {count} album đã tạo trên Google Photos",
    },
    "unbackup_mode_trash": {
        "en": "Move to Google Photos Trash (Recommended - Recoverable for 60 days)",
        "vi": "Chuyển vào Thùng rác Google Photos (Khuyên dùng - An toàn 60 ngày)",
    },
    "unbackup_mode_trash_desc": {
        "en": "Photos will move safely into Google Photos Trash (indexed by photo capture date, recoverable for 60 days).",
        "vi": "Ảnh sẽ được chuyển an toàn vào Thùng rác Google Photos (sắp xếp theo ngày chụp ảnh, có thể khôi phục trong 60 ngày).",
    },
    "unbackup_mode_permanent": {
        "en": "Permanently delete from Google Photos",
        "vi": "Xoá vĩnh viễn khỏi Google Photos",
    },
    "unbackup_mode_permanent_desc": {
        "en": "Permanently deletes items from Google Photos cloud without moving to trash. Cannot be undone.",
        "vi": "Xoá hoàn toàn và vĩnh viễn trên Google Photos không qua thùng rác. Không thể khôi phục.",
    },
    "unbackup_safety_notice": {
        "en": "🛡️ 100% LOCAL DATA SAFETY GUARANTEE:\n"
              "Original photos and videos on your computer hard drive will NEVER be deleted or modified.",
        "vi": "🛡️ BẢO VỆ DỮ LIỆU CỤC BỘ 100%:\n"
        "Toàn bộ file ảnh và video GỐC trên ổ đĩa máy tính của bạn sẽ KHÔNG BỊ XOÁ và được bảo toàn nguyên vẹn.",
    },
    "unbackup_album_notice": {
        "en": "💡 Notice on Google Photos albums:\n"
              "All photos inside albums are deleted to free storage. Google Photos preserves empty album containers (0 photos) by design. You can delete empty album shells directly on photos.google.com (3 dots -> Delete album).",
        "vi": "💡 Lưu ý về Album trên Google Photos:\n"
              "Toàn bộ ảnh bên trong album sẽ bị xoá sạch để giải phóng dung lượng. Theo cơ chế của Google, vỏ album rỗng (0 ảnh) được giữ lại; bạn có thể xoá vỏ album rỗng này trực tiếp trên web photos.google.com (bấm 3 chấm -> Xoá album).",
    },
    "unbackup_btn_start": {
        "en": "🗑️ Start Cloud Unbackup",
        "vi": "🗑️ Bắt đầu Huỷ sao lưu",
    },
    "unbackup_in_progress": {
        "en": "Deleting from Google Photos: {current:,} / {total:,} ({percent}%)",
        "vi": "Đang xoá trên Google Photos: {current:,} / {total:,} ({percent}%)",
    },
    "unbackup_completed_msg": {
        "en": "Successfully unbacked {count:,} photos from Google Photos!\n\n"
              "• All photos & videos have been removed from Cloud (storage freed).\n"
              "• Google Photos keeps empty album containers (0 photos) by design. You can remove them anytime on photos.google.com (3 dots -> Delete album).\n"
              "• All original files on your computer remain 100% safe.",
        "vi": "Đã xoá thành công {count:,} ảnh/video trên Google Photos!\n\n"
              "• Toàn bộ ảnh/video đã được dọn sạch khỏi Cloud (giải phóng dung lượng).\n"
              "• Các vỏ album rỗng (0 ảnh) được Google bảo lưu theo quy tắc của họ; bạn có thể xoá vỏ album rỗng này trên photos.google.com (bấm 3 chấm -> Xoá album).\n"
              "• Toàn bộ file gốc trên máy tính của bạn vẫn được bảo toàn nguyên vẹn 100%.",
    },
    "unbackup_no_items": {
        "en": "No backed up files found for this account to unbackup.",
        "vi": "Không tìm thấy file nào đã sao lưu của tài khoản này để huỷ.",
    },
    "unbackup_error": {
        "en": "Error during cloud unbackup: {error}",
        "vi": "Lỗi trong quá trình huỷ sao lưu: {error}",
    },
    "unbackup_scan_machine": {
        "en": "Scanning computer folders: {folder}...",
        "vi": "Đang tự động quét thư mục trên máy: {folder}...",
    },
    "unbackup_found_folder_files": {
        "en": "📁 Found {count:,} photos/videos on computer ({folder})",
        "vi": "📁 Đã quét thấy: {count:,} ảnh/video trên máy ({folder})",
    },
    "unbackup_scope_folder": {
        "en": "Unbackup photos matching computer folders ({count:,} files)",
        "vi": "Xoá ảnh trên Cloud giống với thư mục trên máy ({count:,} file)",
    },
    "unbackup_scope_db": {
        "en": "Unbackup only files in database history ({count:,} files)",
        "vi": "Chỉ xoá các file đã ghi nhận trong lịch sử app ({count:,} file)",
    },
    "btn_choose_other_folder": {
        "en": "📂 Choose another folder to scan & unbackup...",
        "vi": "📂 Chọn thư mục khác để quét & xoá...",
    },
    "tab_albums": {
        "en": "🖼️ Albums & Photos",
        "vi": "🖼️ Album & Ảnh",
    },
    "albums_search_placeholder": {
        "en": "🔍 Search album by name...",
        "vi": "🔍 Tìm album theo tên...",
    },
    "albums_select_all": {
        "en": "Select All",
        "vi": "Chọn tất cả",
    },
    "albums_selected_count": {
        "en": "Selected: {count} / {total} albums",
        "vi": "Đã chọn: {count} / {total} album",
    },
    "btn_download_selected_albums": {
        "en": "📥 Download Selected ({count})",
        "vi": "📥 Tải {count} album đã chọn",
    },
    "btn_clean_empty_albums": {
        "en": "🧹 Clean Empty Albums",
        "vi": "🧹 Dọn Album Trống",
    },
    "filter_all_albums": {
        "en": "All Albums",
        "vi": "Tất cả",
    },
    "filter_with_photos": {
        "en": "With Photos",
        "vi": "Có ảnh",
    },
    "filter_empty_albums": {
        "en": "Empty (0)",
        "vi": "Trống (0)",
    },
    "btn_refresh_albums": {
        "en": "🔄 Refresh",
        "vi": "🔄 Làm mới",
    },
    "album_photos_count": {
        "en": "{count} photos",
        "vi": "{count} ảnh",
    },
    "btn_view_photos": {
        "en": "View Photos",
        "vi": "Xem ảnh",
    },
    "btn_download_album": {
        "en": "Download",
        "vi": "Tải về",
    },
    "btn_back_to_albums": {
        "en": "⬅️ Back to Albums",
        "vi": "⬅️ Quay lại danh sách Album",
    },
    "btn_download_this_album": {
        "en": "📥 Download this Album to PC",
        "vi": "📥 Tải album này về máy",
    },
    "dialog_select_download_dir": {
        "en": "Select Destination Folder on PC to Save Albums",
        "vi": "Chọn thư mục trên máy để tải album về",
    },
    "downloading_album_title": {
        "en": "Downloading Albums...",
        "vi": "Đang tải Album về máy...",
    },
    "download_complete_title": {
        "en": "Download Completed",
        "vi": "Tải về hoàn tất",
    },
    "download_complete_msg": {
        "en": "Successfully downloaded {albums_count} album(s) ({files_count} files) to:\n{folder}",
        "vi": "Đã tải xong {albums_count} album ({files_count} ảnh/video) về thư mục:\n{folder}",
    },
    "albums_empty": {
        "en": "No albums found yet.\nAlbums will appear here when you upload folders with Auto-Album enabled.",
        "vi": "Chưa có album nào.\nCác album sẽ xuất hiện tại đây khi bạn sao lưu thư mục với tính năng Gom Album tự động.",
    },
    "btn_delete_album_app": {
        "en": "Delete Album Record",
        "vi": "Xoá Album khỏi Ứng dụng",
    },
    "confirm_delete_album_title": {
        "en": "Delete Album",
        "vi": "Xoá Album",
    },
    "confirm_delete_album_msg": {
        "en": "Are you sure you want to remove album '{name}' from the app?\n\n"
              "• This clears the album index and tracking from this application.\n"
              "• To permanently remove the empty album container from Google Photos Cloud, visit photos.google.com -> open album -> 3 dots -> 'Delete album'.",
        "vi": "Bạn có chắc muốn xoá thông tin Album '{name}' khỏi ứng dụng?\n\n"
              "• Thao tác này sẽ xoá hiển thị và liên kết album trên ứng dụng máy tính.\n"
              "• Để xoá hoàn toàn vỏ album rỗng trên máy chủ Google Photos, bạn chỉ cần mở photos.google.com -> vào album -> bấm 3 chấm -> chọn 'Xoá album'.",
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
