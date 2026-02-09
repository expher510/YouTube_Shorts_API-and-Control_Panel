import requests
import re
import json
import os
import time
import traceback
from typing import List, Optional
from fastapi import FastAPI, Query, File, UploadFile
import uvicorn
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
from concurrent.futures import ThreadPoolExecutor
from pytubefix import Playlist
import random
import yt_dlp
from proxy_utils import proxy_manager

session = requests.Session()

app = FastAPI(title="YouTube Shorts Smart Fetcher", version="2.6.3")

# Robust headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Connection": "keep-alive"
}

# Instantiate singly? Not thread-safe per docs. 
# We'll create per-thread in get_transcript_safe.

# --- INTERNAL HELPERS ---

# --- GLOBAL CONFIG STORAGE ---
COOKIES_FILE = "cookies.txt"

def get_active_cookies():
    """Finds the best available cookies file."""
    possible = ["cookies.txt", "www.youtube.com_cookies.txt"]
    for p in possible:
        if os.path.exists(p):
            return p
    return None

def get_transcript_ytdlp(v_id: str, proxy_url=None) -> str:
    """Fallback transcript extraction using yt-dlp with client rotation."""
    clients = ['ios', 'android', 'mweb', 'web']
    random.shuffle(clients)
    
    for client in clients:
        print(f"SCRAPE: Trying yt-dlp with client {client} for {v_id}...")
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsubs': True,
            'subtitleslangs': ['ar', 'en', '.*'],
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': [f'player-client={client}']},
            'cookiefile': COOKIES_FILE if os.path.exists(COOKIES_FILE) else None,
        }
        if proxy_url:
            ydl_opts['proxy'] = proxy_url

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={v_id}", download=False)
                # Look for the first automatic or manual transcript
                subtitles = info.get('requested_subtitles')
                if subtitles:
                    # Fetch first available lang
                    lang = next(iter(subtitles))
                    sub_url = subtitles[lang]['url']
                    res = session.get(sub_url, timeout=10)
                    if res.status_code == 200:
                        # Simple cleanup of VTT/SRT tags if needed
                        subs = res.text
                        # Very crude cleanup for now
                        clean_subs = re.sub(r'<[^>]+>', '', subs)
                        clean_subs = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', '', clean_subs)
                        return " ".join(clean_subs.split())
        except: continue
    return None

def get_transcript_safe(v_id: str) -> str:
    """Tries to get transcript using high-level methods with Cookie/Proxy/yt-dlp support."""
    
    # Check for cookies file
    cookie_path = get_active_cookies()
    if cookie_path:
        print(f"SCRAPE: Using {cookie_path} for extraction.")

    def fetch_attempt(proxy_cfg=None):
        api = YouTubeTranscriptApi(proxy_config=proxy_cfg)
        # Pass cookies if available
        t_list = api.list_transcripts(v_id, cookies=cookie_path) if cookie_path else api.list(v_id)
        try:
            return t_list.find_transcript(['ar', 'en']).fetch()
        except:
            return next(iter(t_list)).fetch()

    try:
        # 1. Try local IP first (with jitter)
        time.sleep(random.uniform(0.5, 1.5))
        try:
            t_obj = fetch_attempt()
            return " ".join([t['text'] for t in t_obj])
        except Exception as e:
            err_msg = str(e)
            
            # 2. Try with a rotating proxy
            print(f"SCRAPE: Fallback to Proxies for {v_id}...")
            max_retries = 2
            for i in range(max_retries):
                p_dict = proxy_manager.get_proxy()
                if not p_dict: break
                proxy_url = list(p_dict.values())[0]
                try:
                    p_config = GenericProxyConfig(http_url=proxy_url)
                    t_obj = fetch_attempt(p_config)
                    return " ".join([t['text'] for t in t_obj])
                except Exception:
                    proxy_manager.mark_dead(p_dict)
            
            # 3. Last Resort: yt-dlp with client rotation
            print(f"SCRAPE: Final fallback to yt-dlp for {v_id}...")
            ytdlp_res = get_transcript_ytdlp(v_id)
            if ytdlp_res: return ytdlp_res
            
            return f"TRANSCRIPT ERROR: All free methods exhausted (Blocked or Unavailable)."

    except Exception:
        return f"No speech or disabled by owner."

def get_full_metadata(v_id: str) -> dict:
    url = f"https://www.youtube.com/shorts/{v_id}"
    res_data = {
        "title": "Unknown Title",
        "channel_name": "Unknown Channel",
        "views": "N/A",
        "publish_date": "N/A",
        "thumbnail": f"https://i.ytimg.com/vi/{v_id}/maxresdefault.jpg",
        "full_description": "N/A",
        "transcript": "N/A"
    }
    
    try:
        res = session.get(url, headers=HEADERS, timeout=12)
        html = res.text

        # 1. Title
        t_m = re.search(r'<meta name="title" content="(.*?)">', html)
        if not t_m: t_m = re.search(r'<title>(.*?)</title>', html)
        if t_m: res_data["title"] = t_m.group(1).replace(" - YouTube", "").strip()

        # 2. Channel
        c_m = re.search(r'"ownerName":"(.*?)"', html)
        if not c_m: c_m = re.search(r'"author":"(.*?)"', html)
        if not c_m: c_m = re.search(r'itemprop="name" content="(.*?)"', html)
        if c_m: res_data["channel_name"] = c_m.group(1)

        # 3. Views & Date
        v_m = re.search(r'"shortViewCountText":\{"simpleText":"(.*?)"\}', html)
        if not v_m: v_m = re.search(r'"viewCount":"(.*?)"', html)
        if v_m: res_data["views"] = v_m.group(1)

        d_m = re.search(r'"publishDate":"(.*?)"', html)
        if not d_m: d_m = re.search(r'itemprop="datePublished" content="(.*?)"', html)
        if d_m: res_data["publish_date"] = d_m.group(1)

        # 4. JSON Content (Description)
        j_m = re.search(r'ytInitialData\s*=\s*(\{.*?\});', html)
        if not j_m: j_m = re.search(r'ytInitialData\s*=\s*(\{.*?\})</script>', html)
        if j_m:
            try:
                data = json.loads(j_m.group(1))
                for panel in data.get("engagementPanels", []):
                    rend = panel.get("engagementPanelRenderer", {})
                    if rend.get("targetId") == "engagement-panel-structured-description":
                        items = rend.get("content", {}).get("structuredDescriptionContentRenderer", {}).get("items", [])
                        for item in items:
                            if "videoDescriptionHeaderRenderer" in item:
                                info = item["videoDescriptionHeaderRenderer"]
                                res_data["full_description"] = info.get("description", {}).get("runs", [{}])[0].get("text", "N/A")
            except: pass

        # Fallback for description
        if res_data["full_description"] == "N/A":
            res_data["full_description"] = res_data["title"]

        # 5. Transcript
        res_data["transcript"] = get_transcript_safe(v_id)
        
        return res_data
    except Exception as e:
        print(f"ERROR fetching metadata for {v_id}: {e}")
        return res_data

# --- EXTRACTORS ---

def extract_videos(query_or_hashtag: str, is_hashtag: bool, limit: int) -> List[dict]:
    url = f"https://www.youtube.com/hashtag/{query_or_hashtag}/shorts" if is_hashtag else f"https://www.youtube.com/results?search_query={query_or_hashtag}&sp=EgIQCQ=="
    try:
        print(f"SCRAPE: Visiting {url}")
        res = session.get(url, headers=HEADERS, timeout=15)
        video_ids = re.findall(r'"videoId":\s*"([^"]{11})"', res.text)
        seen = set()
        unique_ids = [vid for vid in video_ids if not (vid in seen or seen.add(vid))][:limit]
        
        results = []
        for v_id in unique_ids:
            print(f"ENRICH: Getting rich data for {v_id}...")
            results.append({
                "video_id": v_id,
                "url": f"https://www.youtube.com/shorts/{v_id}",
                **get_full_metadata(v_id)
            })
            time.sleep(0.3)
        return results
    except Exception as e:
        print(f"SCAN ERROR: {e}")
        return []

# --- API ENDPOINTS ---

@app.get("/fetch", tags=["Core"])
def fetch(hashtag: str, limit: int = 10):
    videos = extract_videos(hashtag, True, limit)
    return {"status": "success", "count": len(videos), "videos": videos}

@app.get("/search", tags=["Core"])
def search(query: str, limit: int = 10):
    videos = extract_videos(query, False, limit)
    return {"status": "success", "count": len(videos), "videos": videos}

# ==========================================
#   CHANNELS SHORTS INTEGRATION
# ==========================================

def extract_channel_shorts(channel: str, limit: int) -> List[dict]:
    url = f"https://www.youtube.com/{channel}/shorts"
    try:
        print(f"SCRAPE: Visiting {url}")
        res = session.get(url, headers=HEADERS, timeout=15)
        video_ids = re.findall(r'"videoId":\s*"([^"]{11})"', res.text)
        seen = set()
        unique_ids = [vid for vid in video_ids if not (vid in seen or seen.add(vid))][:limit]
        
        results = []
        for v_id in unique_ids:
            print(f"ENRICH: Getting rich data for {v_id}...")
            results.append({
                "video_id": v_id,
                "url": f"https://www.youtube.com/shorts/{v_id}",
                **get_full_metadata(v_id)
            })
            time.sleep(0.3)
        return results
    except Exception as e:
        print(f"CHANNEL SCAN ERROR: {e}")
        return []

@app.get("/channels", tags=["Core"])
def channels(channel: str, limit: int = 10):
    videos = extract_channel_shorts(channel, limit)
    return {"status": "success", "count": len(videos), "videos": videos}

# ==========================================
#   PLAYLIST INTEGRATION
# ==========================================

def extract_playlist_videos(playlist_id: str, limit: int) -> List[dict]:
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    try:
        print(f"SCRAPE: Visiting Playlist {url} using pytubefix")
        pl = Playlist(url)
        # Playlist.video_urls returns full urls
        video_urls = pl.video_urls[:limit]
        
        # Extract 11-char IDs from urls
        unique_ids = []
        for v_url in video_urls:
            # Match v=ID or shorts/ID
            match = re.search(r'(?:v=|shorts/|embed/|watch\?v=)([^"&?]{11})', v_url)
            if match:
                unique_ids.append(match.group(1))
        
        print(f"FOUND {len(unique_ids)} videos in playlist")
        
        results = []
        # Reduced max_workers to 5 to avoid IP blocks from aggressive concurrent hits
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Create a list of futures
            futures = {executor.submit(get_full_metadata, v_id): v_id for v_id in unique_ids}
            for future in futures:
                v_id = futures[future]
                try:
                    meta = future.result()
                    results.append({
                        "video_id": v_id,
                        "url": f"https://www.youtube.com/watch?v={v_id}",
                        **meta
                    })
                except Exception as e:
                    print(f"ERROR processing video {v_id} in playlist: {e}")
                    
        return results
    except Exception as e:
        print(f"PLAYLIST SCAN ERROR: {e}")
        return []

@app.post("/cookies")
async def upload_cookies(file: UploadFile = File(...)):
    """Upload a cookies.txt file to bypass blocks."""
    try:
        content = await file.read()
        with open("cookies.txt", "wb") as f:
            f.write(content)
        return {"status": "success", "message": "cookies.txt uploaded and activated."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/status")
async def get_api_status():
    """Verify cookie and IP status."""
    return {
        "cookies_active": get_active_cookies() is not None,
        "cookie_file": get_active_cookies(),
        "proxy_pool_size": len(proxy_manager.proxies)
    }

@app.get("/playlists", tags=["Core"])
def get_playlists(playlist_id: str, limit: int = 15):
    """
    Fetch rich metadata and transcripts for all videos in a playlist.
    """
    print(f"API: Fetching playlist {playlist_id} with limit {limit}")
    videos = extract_playlist_videos(playlist_id, limit)
    return {"status": "success", "count": len(videos), "videos": videos}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7861))
    print(f"STARTUP: API v2.6.3 listening on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
