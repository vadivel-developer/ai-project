import feedparser
from youtube_transcript_api import YouTubeTranscriptApi

RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={}"


def latest_videos(channel: dict, limit: int = 3) -> list[dict]:
    feed = feedparser.parse(RSS.format(channel["id"]))
    return [
        {
            "id": e.yt_videoid,
            "title": e.title,
            "url": e.link,
            "channel": channel["name"],
        }
        for e in feed.entries[:limit]
    ]


def get_transcript(video_id: str) -> str | None:
    """Return transcript text, or None if captions are unavailable."""
    try:
        parts = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "en-US"])
    except Exception:
        return None
    return " ".join(p["text"] for p in parts)
