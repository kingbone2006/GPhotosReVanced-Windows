# 📸 Google Photos ReVanced (Windows Edition)

> **Lifetime Free Unlimited Cloud Storage Backup for Windows 10/11 by Emulating Google Pixel XL.**  
> Back up photos & videos at Original Quality without consuming your 15GB Google Drive quota.

---

<p align="center">
  <a href="README_VI.md"><strong>🇻🇳 Xem bản Tiếng Việt (Vietnamese Version)</strong></a> &nbsp;|&nbsp; 
  <a href="README.md"><strong>🇺🇸 English (Current)</strong></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 10/11" />
  <img src="https://img.shields.io/badge/Storage-Pixel%20XL%20Unlimited-22c55e?style=for-the-badge&logo=googlephotos&logoColor=white" alt="Pixel XL Unlimited" />
  <img src="https://img.shields.io/badge/Network-1Gbps%20Fiber%20Ready-f59e0b?style=for-the-badge&logo=speedtest&logoColor=white" alt="1Gbps Ready" />
  <img src="https://img.shields.io/badge/Multi--Threading-Up%20to%2016%20Threads-38bdf8?style=for-the-badge&logo=speedtest&logoColor=white" alt="Multi-Threaded" />
  <img src="https://img.shields.io/badge/Python-3.10%20--%203.14-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10 - 3.14" />
  <img src="https://img.shields.io/badge/License-MIT-purple?style=for-the-badge" alt="MIT License" />
</p>

---

## ⚡ 1-Step Quick Start (Zero Configuration)

You only need **Git** and **Python** (or let the launcher auto-install Python for you).

```cmd
git clone https://github.com/kingbone2006/GPhotosReVanced-Windows.git
cd GPhotosReVanced-Windows
run.bat
```

> [!TIP]
> **That's it!** Simply double-click **`run.bat`**:
> 1. Detects Python automatically (or installs Python 3.11 quietly if missing).
> 2. Sets up an isolated virtual environment (`venv`).
> 3. Installs all required libraries from `requirements.txt`.
> 4. Launches the application immediately. On subsequent launches, it opens in under 1 second!

---

## 📑 Table of Contents
- [🌟 Highlights & Features](#-highlights--features)
- [⚡ 1-Step Quick Start](#-1-step-quick-start-zero-configuration)
- [🛠️ Manual Installation](#️-manual-installation)
- [🚀 Quick Start Guide](#-quick-start-guide)
- [⚙️ High-Performance Architecture & Threads](#️-high-performance-architecture--threads)
- [🗂️ Smart Auto-Album Feature](#️-smart-auto-album-feature)
- [🌐 Bilingual Interface](#-bilingual-interface)
- [🔒 Privacy & Security](#-privacy--security)
- [❓ Frequently Asked Questions (FAQ)](#-frequently-asked-questions-faq)
- [📄 Disclaimer & License](#-disclaimer--license)

---

## 🌟 Highlights & Features

- **📱 Pixel XL Hardware Spoofing**: Authenticates directly with Google Photos backend using Google Pixel XL device signatures (`marlin`), unlocking lifetime free unlimited backup at **Original Quality for both Photos and Videos** without consuming your 15GB Google Drive quota.
- **🚀 In-Memory RAM Cache Pipeline**: Pre-buffers files into RAM with throttled sequential disk reads, completely eliminating mechanical HDD head thrashing, reducing disk active time, and streaming uploads at wire speed (40 – 80+ MB/s).
- **⚡ Multi-Core CPU Hash Offloading**: Offloads SHA-1 hash computations across all CPU cores via a dedicated process pool, bypassing the Python GIL and calculating hashes at ~2,500 MB/s.
- **🌐 1Gbps Network & Socket Tuning**: Reuses persistent HTTP/TLS 1.3 Keep-Alive connections, configures `TCP_NODELAY`, 2MB socket buffers, and 1MB chunk transmission to saturate fiber bandwidth.
- **🔄 Real-Time Auto-Sync Watcher**: Continuously monitors local folders. Whenever new photos or videos are added, they are automatically queued and backed up in the background.
- **🗂️ Smart Auto-Album Creation**: Groups photos into cloud albums based on parent folder names, with deduplication and 404 auto-recreation.
- **🔐 1-Click Browser Auto-Capture Authentication**: Chrome DevTools Protocol (CDP) token extraction. Simply log in through the secure Google web window and the app captures your token automatically—no manual DevTools or F12 required.
- **🎨 Windows 11 Fluent Dark UI**: Built with CustomTkinter, featuring an Android Google Photos-style upload card carousel with real-time speed metrics and smooth completion animations.
- **🌐 Dual-Language Support**: English by default, with an instant 1-click toggle to Vietnamese in Settings without restarting.

---

## 🛠️ Manual Installation

If you prefer setting up manually without `run.bat`:

```cmd
# 1. Clone the repository
git clone https://github.com/kingbone2006/GPhotosReVanced-Windows.git
cd GPhotosReVanced-Windows

# 2. Create and activate a Python virtual environment
python -m venv venv
call venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Start the application
python main.py
```

---

## 🚀 Quick Start Guide

### Step 1: Connect Google Account
1. Click **"Connect Account"** in the top-right corner.
2. Select **"⚡ 1-Click Auto Login (Recommended)"** and click **"Open Google Sign-in Window"**.
3. Log in to your Google Account in the browser window and click **"I agree"**.
4. The application captures the token automatically, exchanges it with Google's OAuth endpoints, and activates the Pixel XL profile.

### Step 2: Configure Folders
1. Navigate to the **📁 Sync Folders** tab.
2. Click **➕ Add Sync Folder** to select directories containing photos and videos (e.g., `Pictures`, `DCIM`, phone backup folders).
3. Toggle **"Auto-create Album by folder name"** if you want your directory structure replicated on Google Photos.
4. Click **🔄 Scan All Folders Now** to queue all existing files for initial backup.

### Step 3: Sit Back and Monitor
- The **📊 Dashboard** displays live cards for active uploads with upload speed and progress.
- Once uploaded, cards smoothly vanish like in the native Android Google Photos app.

---

## ⚙️ High-Performance Architecture & Threads

| Thread Count | Recommended Use Case |
| :--- | :--- |
| **2 Threads** | Mechanical SATA HDDs or low-bandwidth connections. |
| **4 - 6 Threads (Recommended)** | Standard home broadband & fiber (100Mbps – 500Mbps); optimal balance preventing Google server rate limits. |
| **8 - 12 Threads** | Gigabit fiber connections (1Gbps) with SSDs or large RAM caches. |
| **16 Threads (Extreme)** | High-end multi-core CPUs with NVMe SSDs and high-capacity RAM pipelines. |

> [!TIP]
> **Why RAM Cache matters for HDD users**:
> Reading multiple files simultaneously on a mechanical HDD causes head thrashing, dropping disk speed to 2 MB/s. Our pipeline throttles physical disk reads to 2 sequential streams into an in-memory RAM buffer, allowing uploads to blast out of RAM at full wire speed (40 – 80+ MB/s).

---

## 🗂️ Smart Auto-Album Feature

When **Auto-Album** is enabled:
- Photos located in `D:\Photos\Japan Trip 2025\IMG_001.jpg` are automatically assigned to an album named `Japan Trip 2025` on Google Photos.
- The app automatically checks if the album already exists in your account to avoid duplicate albums.
- If an album was deleted on Google Photos, the app detects it (`404 Not Found`) and recreates it seamlessly.
- Multiple Google accounts are completely isolated with unique composite keys `(account_email, album_name)`.

---

## 🌐 Bilingual Interface

The application defaults to **English**. You can switch to **Tiếng Việt** at any time:
1. Open the **⚙️ Settings** tab.
2. Choose **Tiếng Việt** in the **Interface Language** dropdown.
3. The interface immediately translates all tabs, labels, buttons, and dialogs.

---

## 🔒 Privacy & Security

- **Direct Communication**: All network requests connect directly to Google's official endpoints (`photoslibrary.googleapis.com`, `play.googleapis.com`, `accounts.google.com`).
- **No Third-Party Relays**: Your credentials, photos, and personal data never pass through any external server.
- **Local Storage**: OAuth tokens and backup tracking databases are stored locally on your machine at `%LOCALAPPDATA%\GPhotosReVanced\`.
- **Intact Cloud Files**: Clearing local stats or history never deletes any photos or albums already uploaded to your cloud storage.

---

## ❓ Frequently Asked Questions (FAQ)

#### Q: Does this truly offer unlimited storage without counting toward Google Drive quota?
**A:** Yes. Google Photos provides lifetime unlimited original-quality backups to devices identified as the original Google Pixel (2016). This application accurately spoofs Google Pixel XL device characteristics and parameters, allowing all uploaded photos and videos to be backed up for free without reducing your 15GB Google One quota.

#### Q: Which media formats are supported?
**A:** All standard media types:
- **Images**: `.jpg`, `.jpeg`, `.png`, `.webp`, `.heic`, `.bmp`, `.gif`, `.tiff`
- **RAW Photos**: `.dng`, `.cr2`, `.nef`, `.arw`, `.rw2`, `.orf`
- **Videos**: `.mp4`, `.mov`, `.mkv`, `.avi`, `.webm`, `.3gp`, `.m4v`, `.mts`

#### Q: Can I run the application silently in the background on startup?
**A:** Yes, launch using `run_silent.vbs` or place a shortcut to `run_silent.vbs` in your Windows Startup folder (`shell:startup`).

---

## 📄 Disclaimer & License

- This open-source project is developed for personal, non-commercial backup purposes and educational research.
- Google Photos is a trademark of Google LLC. This project is not affiliated with or endorsed by Google LLC.
- Licensed under the **[MIT License](LICENSE)**.
