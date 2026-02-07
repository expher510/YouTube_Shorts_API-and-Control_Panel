import youtube_transcript_api
import sys

print(f"Python version: {sys.version}")
print(f"Library path: {youtube_transcript_api.__file__}")
print(f"Module attributes: {dir(youtube_transcript_api)}")

from youtube_transcript_api import YouTubeTranscriptApi
print(f"Class attributes: {dir(YouTubeTranscriptApi)}")

try:
    # Attempt most common usage
    print("\nAttempting YouTubeTranscriptApi.get_transcript...")
    t = YouTubeTranscriptApi.get_transcript("2PwjsrDCtZI")
    print("✅ Success with get_transcript")
except Exception as e:
    print(f"❌ Failed get_transcript: {e}")

try:
    print("\nAttempting YouTubeTranscriptApi.list_transcripts...")
    t = YouTubeTranscriptApi.list_transcripts("2PwjsrDCtZI")
    print("✅ Success with list_transcripts")
except Exception as e:
    print(f"❌ Failed list_transcripts: {e}")
