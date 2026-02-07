import requests
import re
import json
import os
import time
import traceback
from typing import List, Optional
from fastapi import FastAPI, Query
import uvicorn
from youtube_transcript_api import YouTubeTranscriptApi

app = FastAPI(title="YouTube Shorts Smart Fetcher", version="2.6.3")

# Robust headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Connection": "keep-alive"
}

# Instantiate sekali (Singleton-like) for the whole app
transcript_api = YouTubeTranscriptApi()

# --- INTERNAL HELPERS ---

def get_transcript_safe(v_id: str) -> str:
    """Tries to get transcript using high-level methods or raw list access."""
    try:
        # Use instance-based 'list' method (required by some versions)
        t_list = transcript_api.list(v_id)
        # Find and fetch
        t_obj = t_list.find_transcript(['ar', 'en']).fetch()
        
        # Use to_raw_data() for compatibility with dataclass objects
        raw_data = t_obj.to_raw_data() if hasattr(t_obj, 'to_raw_data') else t_obj
        
        return " ".join([t['text'] for t in raw_data])
    except Exception as e:
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
        res = requests.get(url, headers=HEADERS, timeout=12)
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
        res = requests.get(url, headers=HEADERS, timeout=15)
        video_ids = re.findall(r'"videoId":"([^"]{11})"', res.text)
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
#   YOUTUBE-SEARCH-PYTHON LIBRARY INTEGRATION
# ==========================================
# [MONKEY PATCH] Fix for unmaintained library crash (NoneType concatenation)
from youtubesearchpython.handlers.componenthandler import ComponentHandler
from youtubesearchpython.core.constants import videoElementKey

def _getVideoComponent_safe(self, element: dict, shelfTitle: str = None) -> dict:
    video = element[videoElementKey]
    component = {
        'type':                           'video',
        'id':                              self._getValue(video, ['videoId']),
        'title':                           self._getValue(video, ['title', 'runs', 0, 'text']),
        'publishedTime':                   self._getValue(video, ['publishedTimeText', 'simpleText']),
        'duration':                        self._getValue(video, ['lengthText', 'simpleText']),
        'viewCount': {
            'text':                        self._getValue(video, ['viewCountText', 'simpleText']),
            'short':                       self._getValue(video, ['shortViewCountText', 'simpleText']),
        },
        'thumbnails':                      self._getValue(video, ['thumbnail', 'thumbnails']),
        'richThumbnail':                   self._getValue(video, ['richThumbnail', 'movingThumbnailRenderer', 'movingThumbnailDetails', 'thumbnails', 0]),
        'descriptionSnippet':              self._getValue(video, ['detailedMetadataSnippets', 0, 'snippetText', 'runs']),
        'channel': {
            'name':                        self._getValue(video, ['ownerText', 'runs', 0, 'text']),
            'id':                          self._getValue(video, ['ownerText', 'runs', 0, 'navigationEndpoint', 'browseEndpoint', 'browseId']),
            'thumbnails':                  self._getValue(video, ['channelThumbnailSupportedRenderers', 'channelThumbnailWithLinkRenderer', 'thumbnail', 'thumbnails']),
        },
        'accessibility': {
            'title':                       self._getValue(video, ['title', 'accessibility', 'accessibilityData', 'label']),
            'duration':                    self._getValue(video, ['lengthText', 'accessibility', 'accessibilityData', 'label']),
        },
    }
    # SAFELY handle IDs
    v_id = component['id']
    component['link'] = ('https://www.youtube.com/watch?v=' + v_id) if v_id else None
    
    c_id = component['channel']['id']
    component['channel']['link'] = ('https://www.youtube.com/channel/' + c_id) if c_id else None
    
    component['shelfTitle'] = shelfTitle
    return component

ComponentHandler._getVideoComponent = _getVideoComponent_safe

from youtubesearchpython import (
    VideosSearch, ChannelsSearch, PlaylistsSearch, Search, CustomSearch, 
    VideoSortOrder, Suggestions, Hashtag, Video, Playlist, Channel, 
    Comments, Transcript, StreamURLFetcher
)

@app.get("/ysp/search/videos", tags=["YouTube Search Python Lib"])
def ysp_search_videos(query: str, limit: int = 5):
    """Search for videos only."""
    s = VideosSearch(query, limit=limit)
    return s.result()

@app.get("/ysp/search/channels", tags=["YouTube Search Python Lib"])
def ysp_search_channels(query: str, limit: int = 5):
    """Search for channels only."""
    s = ChannelsSearch(query, limit=limit)
    return s.result()

@app.get("/ysp/search/playlists", tags=["YouTube Search Python Lib"])
def ysp_search_playlists(query: str, limit: int = 5):
    """Search for playlists only."""
    s = PlaylistsSearch(query, limit=limit)
    return s.result()

@app.get("/ysp/search/all", tags=["YouTube Search Python Lib"])
def ysp_search_all(query: str, limit: int = 5):
    """Search for everything (mixed)."""
    s = Search(query, limit=limit)
    return s.result()

@app.get("/ysp/search/custom", tags=["YouTube Search Python Lib"])
def ysp_search_custom(query: str, limit: int = 5, upload_date: bool = False):
    """Custom search example (Upload Date sort)."""
    s = CustomSearch(query, VideoSortOrder.uploadDate, limit=limit)
    return s.result()

@app.get("/ysp/video/info", tags=["YouTube Search Python Lib"])
def ysp_video_info(url_or_id: str):
    """Get video info."""
    try:
        return Video.get(url_or_id, mode=0, get_upload_date=True)
    except Exception as e:
        return {"error": str(e)}

@app.get("/ysp/playlist/info", tags=["YouTube Search Python Lib"])
def ysp_playlist_info(url_or_id: str):
    """Get playlist info."""
    try:
        return Playlist.get(url_or_id, mode=0)
    except Exception as e:
        return {"error": str(e)}

@app.get("/ysp/channel/info", tags=["YouTube Search Python Lib"])
def ysp_channel_info(channel_id: str):
    """Get channel info."""
    try:
        return Channel.get(channel_id)
    except Exception as e:
        return {"error": str(e)}

@app.get("/ysp/suggestions", tags=["YouTube Search Python Lib"])
def ysp_suggestions(query: str):
    """Get search suggestions."""
    return Suggestions(language='en', region='US').get(query, mode=0)

@app.get("/ysp/hashtag", tags=["YouTube Search Python Lib"])
def ysp_hashtag(tag: str, limit: int = 5):
    """Get videos by hashtag."""
    return Hashtag(tag, limit=limit).result()

@app.get("/ysp/comments", tags=["YouTube Search Python Lib"])
def ysp_comments(video_id: str, limit: int = 20):
    """Get video comments."""
    # Note: Library may not support 'limit' directly in constructor for all versions, 
    # but has .get() method. Using simplest approach.
    try:
        c = Comments.get(video_id)
        return c
    except Exception as e:
        return {"error": str(e)}

@app.get("/ysp/transcript", tags=["YouTube Search Python Lib"])
def ysp_transcript(video_url: str):
    """Get video transcript using this library."""
    try:
        return Transcript.get(video_url)
    except Exception as e:
        return {"error": str(e)}

@app.get("/ysp/stream_url", tags=["YouTube Search Python Lib"])
def ysp_stream_url(video_url: str):
    """Get direct stream URL (requires yt-dlp installed)."""
    try:
        fetcher = StreamURLFetcher()
        video = Video.get(video_url)
        # Attempt to get stream for itag 22 (720p) or 18 (360p) or similar if specific extraction needed
        # Or just return all via the fetcher helper if library supports generic 'get all'
        # The user example: fetcher.get(video, 251) -> audio
        # We will try to get a common video format, e.g., 22 (720p mp4) or 18 (360p mp4)
        # However, listing all formats is safer.
        # But user asked for "get(video, 251)" example style.
        # Let's try to get a standard MP4 URL.
        url = fetcher.get(video, 22) # 720p
        if not url:
            url = fetcher.get(video, 18) # 360p fallback
        return {"stream_url": url, "itag": "22/18"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7861))
    print(f"STARTUP: API v2.6.3 listening on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")
