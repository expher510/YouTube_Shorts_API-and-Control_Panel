import requests
import json
import time
import sys

# Ensure UTF-8 output even on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:7861"

def test_rich_metadata():
    print(f"--- Testing Rich Metadata Extraction v2.6.1 ---")
    try:
        # Request 1 video for a quick check
        print("Searching for 'cats' shorts...")
        # Using hashtag fetch for variety
        res = requests.get(f"{BASE_URL}/fetch?hashtag=cats&limit=1", timeout=45)
        
        if res.status_code == 200:
            data = res.json()
            videos = data.get("videos", [])
            if videos:
                v = videos[0]
                print(f"\n--- Result for Video: {v['video_id']} ---")
                print(f"  Title:        {v.get('title')}")
                print(f"  Channel:      {v.get('channel_name')}")
                print(f"  Views:        {v.get('views')}")
                print(f"  Published:    {v.get('publish_date')}")
                print(f"  Url:          {v.get('url')}")
                description = v.get('full_description', 'N/A')
                print(f"  Description:  {description[:100].replace('\n', ' ')}...")
                transcript = v.get('transcript', '')
                print(f"  Transcript:   {'OK' if len(transcript) > 100 else 'Partial/Fail'}")
            else:
                print("No videos returned.")
        else:
            print(f"Server error: {res.status_code}")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    test_rich_metadata()
