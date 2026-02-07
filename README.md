# 🎬 YouTube Shorts Smart Fetcher (v2.6.3)

A powerful, local-first API to scrape YouTube Shorts metadata and search results. Now featuring a professional GUI and seamless **ngrok** integration for external access (perfect for n8n/webhooks).

## ✨ New Features (v2.6.3)
- **Bundled Functionality**: Run as a single portable `.exe` (no Python required).
- **Library Integration**: Includes `youtube-search-python` for advanced search (Videos, Channels, Playlists).
- **Broken Link Fixes**: Custom patched logic to handle YouTube's latest UI changes.
- **Deep Fetch**: Automatically retrieves Title, Views, Channel, Thumbnails, and **Transcripts** for Shorts.

---

## 🚨 IMPORTANT: NGROK TOKEN REQUIRED 🚨
To use the **"Go Online"** feature, you **MUST** have a free ngrok Authtoken.
1.  **Sign Up**: Go to [dashboard.ngrok.com](https://dashboard.ngrok.com) and create a free account.
2.  **Get Token**: Copy your **Authtoken** from the dashboard (starts with `2...`).
3.  **Enter in App**: Paste it into the "Enter ngrok Authtoken" box in the GUI and click **Save Token**.
4.  **Connect**: Now you can click "Go Online" anytime!

> **Without this token, the "Go Online" button will fail with an authentication error.**

---

## 🚀 Quick Start (EXE Users)
1.  Download `YouTubeShortsGUI.exe` from the `dist` folder.
2.  Double-click to run.
3.  Click **"Start Local Server"**.
4.  (Optional) Add your ngrok token and click **"Go Online"** to get a public URL.

## 💻 Developer Installation (Source Code)
```bash
# Clone the repository
git clone https://github.com/expher510/YouTube_Shorts_API-and-Control_Panel.git
cd YouTube_Shorts_Tool

# Create environment & Install dependencies
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install youtube-search-python yt-dlp

# Run the App
python short_app.py
```

## 🔌 API Endpoints
### Core Shorts API
- `GET /search?query=cats&limit=10`: Scrapes Shorts with rich metadata.
- `GET /fetch?hashtag=funny&limit=10`: Scrapes Shorts by hashtag.

### Library Integration (`/ysp`)
- `GET /ysp/search/videos?query=...`: Search standard videos.
- `GET /ysp/search/channels?query=...`: Search channels.
- `GET /ysp/search/playlists?query=...`: Search playlists.
- `GET /ysp/comments?video_id=...`: specific video comments.
- *(Note: Some legacy info endpoints provided as-is)*.

## ⚠️ Disclaimer
This tool is for educational purposes. Please respect YouTube's Terms of Service and use it responsibly.
