"""Entry point for Google Photos ReVanced Windows Edition.
Starts high-DPI aware Windows application with Pixel XL unlimited backup engine.
"""

import os
import sys
import ctypes
import logging
import traceback
from pathlib import Path

# Add current directory to path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Configure UTF-8 encoding for Windows Console / Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Windows DPI Awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def setup_console_logging():
    """Setup root logger to print clean messages to console."""
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)
        root.setLevel(logging.INFO)


def main():
    setup_console_logging()
    print("=" * 70, flush=True)
    print("   Google Photos ReVanced - Windows Edition (Console Debug)", flush=True)
    print("   Sao lưu ảnh/video chất lượng gốc không giới hạn (Pixel XL)", flush=True)
    print("   Toàn bộ nhật ký hoạt động & debug sẽ xuất hiện theo thời gian thực", flush=True)
    print("=" * 70, flush=True)
    print(f"[Debug] Python: {sys.version.split()[0]} | Cwd: {BASE_DIR}\n", flush=True)

    try:
        from ui.main_window import MainWindow
        app = MainWindow()
        app.mainloop()
    except KeyboardInterrupt:
        print("\n[INFO] Đã nhận tín hiệu dừng từ bàn phím (Ctrl+C). Đang thoát...", flush=True)
    except Exception:
        print("\n" + "!" * 70, flush=True)
        print("❌ [CRITICAL ERROR] Đã xảy ra lỗi nghiêm trọng:", flush=True)
        traceback.print_exc()
        print("!" * 70, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
