"""LinkedIn AI news agent.

  python main.py run            # find new videos -> make drafts (post + image)
  python main.py list           # show all videos and their status
  python main.py approve <id>   # publish an approved draft to LinkedIn
  python main.py skip <id>      # reject a draft
"""
import argparse

from agent import store
from agent.config import DRAFTS_DIR, load_config
from agent.image import make_card
from agent.linkedin import publish
from agent.writer import write_image_prompt, write_post
from agent.youtube import get_transcript, latest_videos


def cmd_run(cfg: dict) -> None:
    conn = store.connect()
    made = 0
    for channel in cfg["channels"]:
        for video in latest_videos(channel, cfg["max_videos_per_run"]):
            if made >= cfg["posts_per_day"]:
                return
            if store.seen(conn, video["id"]):
                continue
            transcript = get_transcript(video["id"])
            store.add(conn, video)
            if not transcript:
                store.set_status(conn, video["id"], "skipped")
                print(f"skip (no transcript): {video['title']}")
                continue
            folder = DRAFTS_DIR / video["id"]
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "post.txt").write_text(write_post(video, transcript, cfg), encoding="utf-8")
            make_card(
                video["title"],
                write_image_prompt(video),
                cfg["brand_color"],
                cfg["company_name"],
                folder / "image.png",
            )
            made += 1
            print(f"draft ready: {folder}  ({video['title']})")


def cmd_list() -> None:
    for row in store.connect().execute("SELECT * FROM videos ORDER BY rowid DESC"):
        print(f"{row['video_id']}  [{row['status']}]  {row['title']}")


def cmd_approve(video_id: str) -> None:
    conn = store.connect()
    folder = DRAFTS_DIR / video_id
    text = (folder / "post.txt").read_text(encoding="utf-8")
    urn = publish(text, str(folder / "image.png"))
    store.set_status(conn, video_id, "published")
    print(f"published: {urn}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["run", "list", "approve", "skip"])
    p.add_argument("video_id", nargs="?")
    args = p.parse_args()
    if args.command == "run":
        cmd_run(load_config())
    elif args.command == "list":
        cmd_list()
    elif args.command == "approve":
        cmd_approve(args.video_id)
    elif args.command == "skip":
        store.set_status(store.connect(), args.video_id, "skipped")


if __name__ == "__main__":
    main()
