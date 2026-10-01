"""LinkedIn AI news agent.

  python main.py run            # find new videos -> make drafts (post + image)
  python main.py list           # show all videos and their status
  python main.py approve <id>   # publish an approved draft to LinkedIn
  python main.py skip <id>      # reject a draft
  python main.py demo           # make a sample draft (no API keys needed)
  python app.py                 # open the web UI
"""
import argparse

from agent import pipeline, store
from agent.config import load_config


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["run", "list", "approve", "skip", "demo"])
    p.add_argument("video_id", nargs="?")
    args = p.parse_args()
    if args.command == "run":
        pipeline.create_drafts(load_config())
    elif args.command == "demo":
        print("demo draft:", pipeline.create_demo_draft(load_config()))
    elif args.command == "list":
        for r in store.list_all(store.connect()):
            print(f"{r['video_id']}  [{r['status']}]  {r['title']}")
    elif args.command == "approve":
        print("published:", pipeline.approve(args.video_id, load_config().get("require_ai_image", True)))
    elif args.command == "skip":
        store.set_status(store.connect(), args.video_id, "skipped")


if __name__ == "__main__":
    main()
