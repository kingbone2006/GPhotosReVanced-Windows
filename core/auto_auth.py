"""Auto-login service for Google Photos ReVanced Windows.
Launches a native Microsoft Edge or Chrome instance with Chrome DevTools Protocol (CDP)
to automatically capture the oauth_token cookie upon login, eliminating manual DevTools copy-pasting.
"""

import os
import time
import json
import socket
import asyncio
import threading
import subprocess
from pathlib import Path
from typing import Optional, Callable
import urllib.request
import websockets


def find_free_port() -> int:
    """Find an available TCP port for CDP."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def find_browser_path() -> Optional[str]:
    """Locate Microsoft Edge or Google Chrome executable on Windows."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


class AutoLoginService:
    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._is_running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._is_running

    def cancel(self):
        """Cancel ongoing auto-login session and terminate browser window."""
        self._stop_event.set()
        self._is_running = False
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=2.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

    def start(
        self,
        on_status: Callable[[str], None],
        on_token_captured: Callable[[str], None],
        on_error: Callable[[str], None]
    ):
        """Start auto-login in a background thread."""
        if self._is_running:
            return

        browser_path = find_browser_path()
        if not browser_path:
            on_error("Không tìm thấy Microsoft Edge hoặc Google Chrome trên máy tính!")
            return

        self._stop_event.clear()
        self._is_running = True

        self._thread = threading.Thread(
            target=self._run_session,
            args=(browser_path, on_status, on_token_captured, on_error),
            daemon=True
        )
        self._thread.start()

    def _run_session(
        self,
        browser_path: str,
        on_status: Callable[[str], None],
        on_token_captured: Callable[[str], None],
        on_error: Callable[[str], None]
    ):
        port = find_free_port()
        profile_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "GPhotosReVanced" / "AuthProfile"
        profile_dir.mkdir(parents=True, exist_ok=True)

        on_status("Đang mở cửa sổ đăng nhập Google chính chủ...")

        # Launch Edge/Chrome in app mode with remote debugging enabled
        cmd = [
            browser_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile_dir}",
            "--app=https://accounts.google.com/EmbeddedSetup",
            "--window-size=560,740",
            "--disable-background-networking",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        try:
            self._proc = subprocess.Popen(cmd)
        except Exception as e:
            self._is_running = False
            on_error(f"Không thể khởi động trình duyệt: {e}")
            return

        # Run async loop to monitor CDP
        try:
            asyncio.run(self._monitor_cdp(port, on_status, on_token_captured, on_error))
        except Exception as e:
            if not self._stop_event.is_set():
                on_error(f"Lỗi theo dõi quá trình đăng nhập: {e}")
        finally:
            self.cancel()

    async def _monitor_cdp(
        self,
        port: int,
        on_status: Callable[[str], None],
        on_token_captured: Callable[[str], None],
        on_error: Callable[[str], None]
    ):
        # 1. Wait for CDP endpoint to become available
        ws_url = None
        for _ in range(30):
            if self._stop_event.is_set() or (self._proc and self._proc.poll() is not None):
                break
            try:
                res = urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1.0)
                tabs = json.loads(res.read())
                for t in tabs:
                    if t.get("type") == "page" and "webSocketDebuggerUrl" in t:
                        ws_url = t["webSocketDebuggerUrl"]
                        break
                if ws_url:
                    break
            except Exception:
                pass
            await asyncio.sleep(0.5)

        if not ws_url:
            if not self._stop_event.is_set():
                on_error("Trình duyệt đã đóng hoặc không thể kết nối giao thức xác thực.")
            return

        on_status("Cửa sổ đăng nhập đã mở. Vui lòng đăng nhập và bấm 'I agree'...")

        # 2. Connect to WebSocket and monitor cookies
        async with websockets.connect(ws_url) as ws:
            req_id = 1
            while not self._stop_event.is_set():
                # Check if browser process is still alive
                if self._proc and self._proc.poll() is not None:
                    on_status("Cửa sổ đăng nhập đã bị đóng.")
                    break

                req_id += 1
                query = json.dumps({"id": req_id, "method": "Storage.getCookies"})
                await ws.send(query)

                try:
                    resp_str = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    data = json.loads(resp_str)
                    cookies = data.get("result", {}).get("cookies", [])
                    for c in cookies:
                        if c.get("name") == "oauth_token":
                            token_val = c.get("value", "").strip()
                            if token_val:
                                on_status("🎉 Đã bắt được mã oauth_token thành công!")
                                on_token_captured(token_val)
                                return
                except asyncio.TimeoutError:
                    pass
                except Exception:
                    pass

                await asyncio.sleep(1.0)
