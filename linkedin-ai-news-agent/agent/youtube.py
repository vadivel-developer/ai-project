import feedparser
from youtube_transcript_api import YouTubeTranscriptApi

RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={}"


def latest_videos(channel: dict, limit: int = 3) -> list[dict]:
    feed = feedparser.parse(RSS.format(channel["id"]))
    if not feed.entries and getattr(feed, "bozo", 0):
        raise RuntimeError(
            f"Could not read the YouTube feed for '{channel['name']}'. "
            "Check the channel ID in config.yaml and your internet connection."
        )
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
    """Return transcript text, or None if captions are unavailable.

    Works with youtube-transcript-api 1.x (.fetch) and the older 0.x (.get_transcript).
    """
    langs = ["en", "en-US", "en-GB"]
    try:
        if hasattr(YouTubeTranscriptApi, "fetch"):
            parts = YouTubeTranscriptApi().fetch(video_id, languages=langs)
            texts = [getattr(p, "text", None) or p["text"] for p in parts]
        else:
            texts = [p["text"] for p in YouTubeTranscriptApi.get_transcript(video_id, languages=langs)]
    except Exception:
        return None
    return " ".join(texts) or None
