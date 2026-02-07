from fastapi.testclient import TestClient
from short_api import app
import json

client = TestClient(app, raise_server_exceptions=False)

def print_res(name, res):
    print(f"\n--- {name} ---")
    if res.status_code == 200:
        try:
            data = res.json()
            # unique truncation for display
            print(json.dumps(data, indent=2)[:500] + "...") 
        except:
            print(res.text[:500])
    else:
        print(f"FAILED: {res.status_code}")
        print(res.text)

print("=== STARTING YSP TESTS ===")

# 1. Search Videos
res = client.get("/ysp/search/videos?query=cats&limit=1")
print_res("Search Videos", res)

# 2. Search Channels
res = client.get("/ysp/search/channels?query=MrBeast&limit=1")
print_res("Search Channels", res)

# 3. Video Info (using a known short ID or video ID)
# using the one from previous tests: ZbGkwtCibbM
res = client.get("/ysp/video/info?url_or_id=ZbGkwtCibbM")
print_res("Video Info", res)

# 4. Transcript
res = client.get("/ysp/transcript?video_url=https://www.youtube.com/watch?v=ZbGkwtCibbM")
print_res("Transcript", res)

# 5. Stream URL
# stream url might fail if yt-dlp has issues or geo-blocks, but we test logic
res = client.get("/ysp/stream_url?video_url=https://www.youtube.com/watch?v=ZbGkwtCibbM")
print_res("Stream URL", res)

# 6. Comments
res = client.get("/ysp/comments?video_id=ZbGkwtCibbM")
print_res("Comments", res)

print("\n=== TESTS FINISHED ===")
