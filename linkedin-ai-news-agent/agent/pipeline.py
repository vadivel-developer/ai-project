"""Shared logic used by both the CLI and the web UI."""
import re

from . import store
from .config import DRAFTS_DIR
from .image import make_card
from .linkedin import publish
from .writer import write_image_prompt, write_post
from .youtube import get_transcript, latest_videos

ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def draft_dir(video_id: str):
    if not ID_RE.match(video_id):
        raise ValueError("bad video id")
    return DRAFTS_DIR / video_id


def create_drafts(cfg: dict, log=print) -> int:
    conn = store.connect()
    made = 0
    for channel in cfg["channels"]:
        for video in latest_videos(channel, cfg["max_videos_per_run"]):
            if made >= cfg["posts_per_day"]:
                return made
            if store.seen(conn, video["id"]):
                continue
            transcript = get_transcript(video["id"])
            store.add(conn, video)
            if not transcript:
                store.set_status(conn, video["id"], "skipped")
                log(f"skip (no transcript): {video['title']}")
                continue
            folder = draft_dir(video["id"])
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "post.txt").write_text(write_post(video, transcript, cfg), encoding="utf-8")
            make_card(video["title"], write_image_prompt(video), cfg["brand_color"],
                      cfg["company_name"], folder / "image.png")
            made += 1
            log(f"draft ready: {video['title']}")
    return made


def create_demo_draft(cfg: dict) -> str:
    """A sample draft that needs no API keys, for trying the UI."""
    conn = store.connect()
    video = {"id": "demo0001", "channel": "Demo Channel", "url": "https://youtube.com/",
             "title": "Five AI breakthroughs you can use this week"}
    store.add(conn, video)
    folder = draft_dir(video["id"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "post.txt").write_text(
        "AI moves fast. Here is what mattered this week.\n\n"
        "- Smaller models now match last year's giants\n"
        "- Agents can finally finish multi-step tasks\n"
        "- Free tiers make prototyping almost zero cost\n\n"
        "Which of these would help your team most?\n\n"
        "Credit: Demo Channel - https://youtube.com/\n\n" + " ".join(cfg["hashtags"]),
        encoding="utf-8")
    make_card(video["title"], "", cfg["brand_color"], cfg["company_name"], folder / "image.png")
    return video["id"]


def read_text(video_id: str) -> str:
    return (draft_dir(video_id) / "post.txt").read_text(encoding="utf-8")


def save_text(video_id: str, text: str) -> None:
    (draft_dir(video_id) / "post.txt").write_text(text, encoding="utf-8")


def approve(video_id: str) -> str:
    folder = draft_dir(video_id)
    urn = publish(read_text(video_id), str(folder / "image.png"))
    store.set_status(store.connect(), video_id, "published")
    return urn
