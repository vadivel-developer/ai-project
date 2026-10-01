"""Shared logic used by both the CLI and the web UI."""
import json
import re

from . import store
from .config import DRAFTS_DIR
from .image import make_card
from .linkedin import publish
from .writer import with_credit, write_card_text, write_image_prompt, write_post
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
            post = with_credit(write_post(video, transcript, cfg), video)
            (folder / "post.txt").write_text(post, encoding="utf-8")
            title, desc = write_card_text(video, post)
            try:
                prompt = write_image_prompt(video)
            except Exception:
                prompt = ""
            save_card(video["id"], title, desc, prompt, source=video["channel"])
            render_image(video["id"], cfg)
            made += 1
            log(f"draft ready: {video['title']}")
    return made


def read_card(video_id: str) -> dict:
    f = draft_dir(video_id) / "card.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"title": "", "description": "", "prompt": ""}


def save_card(video_id: str, title: str, description: str, prompt: str | None = None,
              source: str | None = None) -> None:
    card = read_card(video_id)
    card.update(title=title.strip(), description=description.strip())
    if source is not None:
        card["source"] = source
    if prompt is not None:
        card["prompt"] = prompt
    (draft_dir(video_id) / "card.json").write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")


def render_image(video_id: str, cfg: dict, use_ai: bool = True) -> None:
    """(Re)make image.png from the saved title, description and prompt. Always succeeds."""
    card = read_card(video_id)
    make_card(card["title"], card["description"], card["prompt"], cfg["brand_color"],
              cfg["company_name"], draft_dir(video_id) / "image.png", use_ai=use_ai,
              source=card.get("source", ""))


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
        "Source: Demo Channel\nChannel: https://www.youtube.com/channel/UCdemo\n"
        "Watch the full video: https://youtube.com/\n\n" + " ".join(cfg["hashtags"]),
        encoding="utf-8")
    save_card(video["id"], "Five AI breakthroughs for this week",
              "Smaller models, smarter agents and free tiers make AI easier to use than ever.", "",
              source="Demo Channel")
    render_image(video["id"], cfg, use_ai=False)
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
