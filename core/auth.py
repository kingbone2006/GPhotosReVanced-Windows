"""Authentication and configuration manager for Google Photos ReVanced Windows.
Handles OAuth token exchange from Google Embedded Setup, credential generation,
and persistent configuration storage.
"""

import os
import json
import secrets
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List
import gpsoauth
from gpmc.api import Api
from gpmc import utils as gpmc_utils

CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "GPhotosReVanced"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "accounts": [],
    "active_email": "",
    "sync_folders": [
        str(Path.home() / "Pictures"),
    ],
    "quality": "original",        # "original" (Pixel XL Unlimited) or "saver"
    "threads": 4,                 # Multi-threaded concurrent uploads (default 4 threads)
    "auto_sync": True,            # Auto watch folders
    "auto_album": False,          # Create albums by parent folder name
    "minimize_to_tray": True,
    "run_at_startup": False,
    "timeout": 60,
    "skip_existing_filenames": False,
    "language": "en",             # "en" (English - default) or "vi" (Vietnamese)
}

GOOGLE_PHOTOS_PACKAGE = "com.google.android.apps.photos"
GOOGLE_PHOTOS_SIG = "24bb24c05e47e0aefa68a58a766179d9b613a600"
GOOGLE_PHOTOS_SERVICE = (
    "oauth2:openid https://www.googleapis.com/auth/mobileapps.native https://www.googleapis.com/auth/photos.native"
)


class ConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from disk, filling in any missing defaults."""
        if not CONFIG_FILE.exists():
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Merge with defaults for any missing keys
            config = DEFAULT_CONFIG.copy()
            config.update(data)
            return config
        except Exception:
            return DEFAULT_CONFIG.copy()

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Persist configuration to disk."""
        if config is not None:
            self.config = config
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def get_active_account(self) -> Optional[Dict[str, str]]:
        """Get the currently active account dict."""
        active_email = self.config.get("active_email")
        for acc in self.config.get("accounts", []):
            if acc.get("email") == active_email:
                return acc
        if self.config.get("accounts"):
            return self.config["accounts"][0]
        return None

    def add_or_update_account(self, email: str, auth_data: str) -> None:
        """Add a new account or update an existing one, setting it as active."""
        email = email.strip()
        auth_data = auth_data.strip()
        accounts: List[Dict[str, str]] = self.config.get("accounts", [])
        
        found = False
        for acc in accounts:
            if acc.get("email", "").lower() == email.lower():
                acc["auth_data"] = auth_data
                found = True
                break
        if not found:
            accounts.append({"email": email, "auth_data": auth_data})

        self.config["accounts"] = accounts
        self.config["active_email"] = email
        self.save_config()

    def remove_account(self, email: str) -> None:
        """Remove an account by email."""
        accounts = [acc for acc in self.config.get("accounts", []) if acc.get("email") != email]
        self.config["accounts"] = accounts
        if self.config.get("active_email") == email:
            self.config["active_email"] = accounts[0]["email"] if accounts else ""
        self.save_config()

    def set_active_account(self, email: str) -> None:
        """Set the active account email."""
        self.config["active_email"] = email
        self.save_config()


def generate_android_id() -> str:
    """Generate a random 16-character hexadecimal Android ID."""
    return secrets.token_hex(8)


def build_google_photos_credential(email: str, master_token: str, android_id: str) -> str:
    """
    Construct the full auth_data URL query string required by gpmc / Google Photos Mobile API.
    Emulates an Android Pixel XL device with the official Google Photos package signature.
    """
    params = {
        "androidId": android_id,
        "app": GOOGLE_PHOTOS_PACKAGE,
        "callerPkg": GOOGLE_PHOTOS_PACKAGE,
        "callerSig": GOOGLE_PHOTOS_SIG,
        "client_sig": GOOGLE_PHOTOS_SIG,
        "device_country": "us",
        "Email": email,
        "google_play_services_version": "240913000",
        "lang": "en_US",
        "oauth2_foreground": "1",
        "operatorCountry": "us",
        "sdk_version": "33",
        "service": GOOGLE_PHOTOS_SERVICE,
        "source": "android",
        "Token": master_token,
    }
    return urllib.parse.urlencode(params)


def exchange_oauth_token(oauth_token: str, android_id: Optional[str] = None) -> Dict[str, str]:
    """
    Exchange an oauth_token cookie obtained from https://accounts.google.com/EmbeddedSetup
    into a master token and full Google Photos credential string.

    Returns:
        Dict with keys: 'email', 'master_token', 'android_id', 'auth_data'
    """
    oauth_token = oauth_token.strip()
    if oauth_token.startswith("oauth_token="):
        oauth_token = oauth_token[len("oauth_token="):]

    if not oauth_token:
        raise ValueError("Mã oauth_token không được để trống!")

    android_id = android_id or generate_android_id()

    # Call Google Play Services OAuth exchange endpoint
    response = gpsoauth.exchange_token(
        email="oauth-token@example.com",
        token=oauth_token,
        android_id=android_id,
    )

    if "Error" in response:
        error_code = response.get("Error", "Unknown")
        if error_code == "BadAuthentication":
            raise ValueError("Token không hợp lệ hoặc đã hết hạn. Vui lòng lấy lại oauth_token mới.")
        elif error_code == "NeedsBrowser":
            raise ValueError("Google yêu cầu xác minh bảo mật bổ sung qua trình duyệt.")
        else:
            raise ValueError(f"Lỗi xác thực từ Google: {error_code}")

    master_token = response.get("Token")
    email = response.get("Email")

    if not master_token or not email:
        raise ValueError("Google không trả về Master Token hoặc Email hợp lệ.")

    auth_data = build_google_photos_credential(email, master_token, android_id)

    return {
        "email": email,
        "master_token": master_token,
        "android_id": android_id,
        "auth_data": auth_data,
    }


def validate_auth_data(auth_data: str) -> Dict[str, Any]:
    """
    Validate an auth_data string by querying Google Photos API for bearer token.
    Raises an exception if the credentials are invalid or rejected.
    """
    auth_data = auth_data.strip()
    if not auth_data:
        raise ValueError("Chuỗi auth_data không được để trống.")

    # Parse email from auth_data
    parsed = dict(urllib.parse.parse_qsl(auth_data))
    email = parsed.get("Email") or gpmc_utils.parse_email(auth_data)
    if not email:
        raise ValueError("Không tìm thấy thông tin Email trong auth_data.")

    api = Api(auth_data=auth_data, timeout=30)
    token = api.bearer_token
    if not token:
        raise ValueError("Không thể lấy Bearer Token từ Google. Tài khoản có thể đã đăng xuất.")

    return {
        "valid": True,
        "email": email,
        "bearer_token_preview": token[:10] + "...",
    }
