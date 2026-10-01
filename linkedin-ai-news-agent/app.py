"""Web UI:  python app.py   ->  http://localhost:5000"""
import hmac
import os

from flask import Flask, Response, jsonify, request, send_file

from agent import pipeline, store
from agent.config import ROOT, load_config

app = Flask(__name__, static_folder=str(ROOT / "web" / "static"), static_url_path="/static")


@app.before_request
def require_password():
    """If APP_PASSWORD is set (do this when hosting online), every page needs it."""
    pw = os.getenv("APP_PASSWORD")
    if not pw:
        return None
    auth = request.authorization
    if auth and hmac.compare_digest((auth.password or "").encode(), pw.encode()):
        return None
    return Response("Login required", 401, {"WWW-Authenticate": 'Basic realm="AI News Studio"'})


@app.get("/")
def index():
    return send_file(ROOT / "web" / "index.html")


@app.get("/api/config")
def config():
    cfg = load_config()
    return jsonify(company=cfg["company_name"])


@app.get("/api/drafts")
def drafts():
    out = []
    for r in store.list_all(store.connect()):
        folder = pipeline.draft_dir(r["video_id"])
        out.append({
            "id": r["video_id"], "title": r["title"], "channel": r["channel"],
            "url": r["url"], "status": r["status"],
            "text": pipeline.read_text(r["video_id"]) if (folder / "post.txt").exists() else "",
            "has_image": (folder / "image.png").exists(),
            "card": pipeline.read_card(r["video_id"]),
        })
    return jsonify(out)


@app.get("/api/drafts/<vid>/image")
def image(vid):
    return send_file(pipeline.draft_dir(vid) / "image.png", mimetype="image/png")


@app.post("/api/drafts/<vid>")
def save(vid):
    pipeline.save_text(vid, request.json.get("text", ""))
    return jsonify(ok=True)


@app.post("/api/drafts/<vid>/image")
def regenerate_image(vid):
    """Rebuild the image from edited title/description (new AI background if `new_background`)."""
    body = request.json or {}
    card = pipeline.read_card(vid)
    pipeline.save_card(vid, body.get("title", card["title"]), body.get("description", card["description"]))
    pipeline.render_image(vid, load_config(), use_ai=bool(body.get("new_background", True)))
    return jsonify(ok=True)


@app.post("/api/drafts/<vid>/skip")
def skip(vid):
    store.set_status(store.connect(), vid, "skipped")
    return jsonify(ok=True)


@app.post("/api/drafts/<vid>/approve")
def approve(vid):
    try:
        return jsonify(ok=True, urn=pipeline.approve(vid))
    except Exception as e:  # show a friendly message in the UI
        return jsonify(ok=False, error=str(e)), 400


@app.post("/api/run")
def run():
    try:
        return jsonify(ok=True, made=pipeline.create_drafts(load_config(), log=lambda m: None))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 400


@app.post("/api/demo")
def demo():
    return jsonify(ok=True, id=pipeline.create_demo_draft(load_config()))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
