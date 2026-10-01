from types import SimpleNamespace

from agent import youtube


def test_latest_videos_parses_feed_and_respects_limit(monkeypatch):
    entries = [SimpleNamespace(yt_videoid=f"vid{i}", title=f"T{i}", link=f"https://y/{i}") for i in range(5)]
    monkeypatch.setattr(youtube.feedparser, "parse", lambda url: SimpleNamespace(entries=entries))
    vids = youtube.latest_videos({"name": "Chan", "id": "UC1"}, limit=2)
    assert [v["id"] for v in vids] == ["vid0", "vid1"]
    assert vids[0] == {"id": "vid0", "title": "T0", "url": "https://y/0", "channel": "Chan"}


def test_transcript_joined_with_real_library_api(monkeypatch):
    """Uses the installed library's real .fetch() shape (snippet objects with .text)."""
    calls = {}

    def fetch(self, video_id, languages=("en",), preserve_formatting=False):
        calls["args"] = (video_id, list(languages))
        return [SimpleNamespace(text="hello"), SimpleNamespace(text="world")]

    monkeypatch.setattr(youtube.YouTubeTranscriptApi, "fetch", fetch)
    assert youtube.get_transcript("abc") == "hello world"
    assert calls["args"][0] == "abc" and "en" in calls["args"][1]


def test_transcript_none_when_unavailable(monkeypatch):
    def fetch(self, *a, **k):
        raise RuntimeError("no captions")
    monkeypatch.setattr(youtube.YouTubeTranscriptApi, "fetch", fetch)
    assert youtube.get_transcript("x") is None


def test_real_library_has_the_method_we_call():
    """Guards against the library renaming its API again."""
    assert hasattr(youtube.YouTubeTranscriptApi, "fetch") or hasattr(youtube.YouTubeTranscriptApi, "get_transcript")


def test_real_youtube_rss_shape_is_parsed(monkeypatch):
    """Parses a YouTube-style Atom feed with the real feedparser (no mock of the parser)."""
    xml = """<?xml version="1.0"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
 <entry><yt:videoId>AbC123xyz_-</yt:videoId><title>A new AI paper</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=AbC123xyz_-"/></entry></feed>"""
    real_parse = youtube.feedparser.parse
    monkeypatch.setattr(youtube.feedparser, "parse", lambda url: real_parse(xml))
    v = youtube.latest_videos({"name": "TMP", "id": "UC1"})[0]
    assert v == {"id": "AbC123xyz_-", "title": "A new AI paper",
                 "url": "https://www.youtube.com/watch?v=AbC123xyz_-", "channel": "TMP"}


def test_unreadable_feed_raises_clear_error(monkeypatch):
    import pytest
    monkeypatch.setattr(youtube.feedparser, "parse", lambda url: SimpleNamespace(entries=[], bozo=1))
    with pytest.raises(RuntimeError, match="channel ID"):
        youtube.latest_videos({"name": "Chan", "id": "bad"})


def test_channel_with_no_videos_is_not_an_error(monkeypatch):
    monkeypatch.setattr(youtube.feedparser, "parse", lambda url: SimpleNamespace(entries=[], bozo=0))
    assert youtube.latest_videos({"name": "Chan", "id": "UC1"}) == []
