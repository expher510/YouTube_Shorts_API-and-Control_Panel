# 🎬 YouTube Shorts Fetcher API & Control Panel

A powerful, local-first API to scrape YouTube Shorts metadata (Hashtag or Search) with a built-in GUI Dashboard for easy management and internet tunneling.

## ✨ Features
- **FastAPI Backend**: Optimized for scraping YouTube Shorts metadata (Video ID, Title, Views, Thumbnails).
- **GUI Control Panel**: Manage the API and Tunnel without touching the command line.
- **Auto-Tunneling**: Uses `localhost.run` to expose your local API to the internet (perfect for n8n/webhooks) without a permanent account.
- **Vertical-Only Logic**: Specifically extracts 9:16 Shorts data.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+
- Git

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd firstproject

# Create a virtual environment
python -m venv .venv

# Activate environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Usage
Run the Dashboard to start the API and the Tunnel:
```bash
python short_gui.py
```
- Click **"START ALL"** to launch the API and create a public URL.
- Copy the **Public URL** for your webhooks or n8n workflows.

### 2. Available Endpoints
- `GET /search?query=...&limit=20`: Search for shorts. Returns **full metadata and transcripts** by default.
- `GET /fetch?hashtag=...&limit=20`: Fetch by hashtag. Returns **full metadata and transcripts** by default.

## 🛠 Project Structure
- `short_gui.py`: The main GUI application.
- `short_api.py`: The FastAPI core logic.
- `requirements.txt`: Project dependencies.
- `.gitignore`: Files excluded from GitHub.

## ⚠️ Disclaimer
This tool is for educational purposes. Please respect YouTube's Terms of Service and use it responsibly.
