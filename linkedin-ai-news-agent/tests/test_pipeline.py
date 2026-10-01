import pytest
from PIL import Image

from agent import pipeline, store

VIDEO = {"id": "vid00001", "title": "Big AI news", "url": "https://y/1", "channel": "Chan",
         "channel_url": "https://www.youtube.com/channel/UC123"}


@pytest.fixture
def fake_net(monkeypatch):
    monkeypatch.setattr(pipeline, "latest_videos", lambda ch, n: [dict(VIDEO)])
    monkeypatch.setattr(pipeline, "get_transcript", lambda vid: "some transcript")
    monkeypatch.setattr(pipeline, "write_post", lambda v, t, c: "Post body #AI")
    monkeypatch.setattr(pipeline, "write_card_text", lambda v, p: ("Card title", "Card description"))
    monkeypatch.setattr(pipeline, "write_image_prompt", lambda v: "a prompt")


def test_create_drafts_makes_post_card_and_image(fake_net, cfg):
    assert pipeline.create_drafts(cfg, log=lambda m: None) == 1
    folder = pipeline.draft_dir("vid00001")
    assert (folder / "post.txt").read_text().startswith("Post body #AI")
    assert pipeline.read_card("vid00001")["title"] == "Card title"
    assert Image.open(folder / "image.png").size == (1200, 627)
    assert store.list_all(store.connect())[0]["status"] == "drafted"


def test_same_video_is_never_drafted_twice(fake_net, cfg):
    pipeline.create_drafts(cfg, log=lambda m: None)
    assert pipeline.create_drafts(cfg, log=lambda m: None) == 0


def test_video_without_transcript_is_skipped(fake_net, cfg, monkeypatch):
    monkeypatch.setattr(pipeline, "get_transcript", lambda vid: None)
    assert pipeline.create_drafts(cfg, log=lambda m: None) == 0
    assert store.list_all(store.connect())[0]["status"] == "skipped"


def test_posts_per_day_limit(monkeypatch, fake_net, cfg):
    vids = [dict(VIDEO, id=f"vid0000{i}") for i in range(3)]
    monkeypatch.setattr(pipeline, "latest_videos", lambda ch, n: vids)
    cfg["posts_per_day"] = 2
    assert pipeline.create_drafts(cfg, log=lambda m: None) == 2


def test_image_still_made_when_prompt_step_fails(fake_net, cfg, monkeypatch):
    def boom(v):
        raise RuntimeError("llm down")
    monkeypatch.setattr(pipeline, "write_image_prompt", boom)
    pipeline.create_drafts(cfg, log=lambda m: None)
    assert (pipeline.draft_dir("vid00001") / "image.png").exists()


def test_demo_draft_needs_no_keys(cfg):
    vid = pipeline.create_demo_draft(cfg)
    assert (pipeline.draft_dir(vid) / "image.png").exists()
    assert "#AI" in pipeline.read_text(vid)


def test_edit_text_and_regenerate_image(cfg):
    vid = pipeline.create_demo_draft(cfg)
    pipeline.save_text(vid, "edited")
    pipeline.save_card(vid, "New title", "New description")
    pipeline.render_image(vid, cfg, use_ai=False)
    assert pipeline.read_text(vid) == "edited"
    assert pipeline.read_card(vid)["title"] == "New title"


@pytest.mark.parametrize("bad", ["../etc", "a/b", "", "x" * 40, "a b", ".."])
def test_path_traversal_ids_rejected(bad):
    with pytest.raises(ValueError):
        pipeline.draft_dir(bad)


def test_approve_publishes_and_marks_status(cfg, monkeypatch, mark_ai):
    vid = pipeline.create_demo_draft(cfg); mark_ai(vid)
    seen = {}
    monkeypatch.setattr(pipeline, "publish", lambda text, img: seen.update(text=text, img=img) or "urn:li:share:1")
    assert pipeline.approve(vid) == "urn:li:share:1"
    assert seen["img"].endswith("image.png")
    assert store.list_all(store.connect())[0]["status"] == "published"


def test_failed_publish_keeps_draft_status(cfg, monkeypatch, mark_ai):
    vid = pipeline.create_demo_draft(cfg); mark_ai(vid)
    def boom(text, img):
        raise RuntimeError("401")
    monkeypatch.setattr(pipeline, "publish", boom)
    with pytest.raises(RuntimeError):
        pipeline.approve(vid)
    assert store.list_all(store.connect())[0]["status"] == "drafted"


def test_post_always_names_channel_and_links_even_if_llm_forgets(fake_net, cfg):
    pipeline.create_drafts(cfg, log=lambda m: None)
    text = pipeline.read_text("vid00001")
    assert "Source: Chan" in text and "https://y/1" in text
    assert pipeline.read_card("vid00001")["source"] == "Chan"


def test_publish_refused_when_image_is_only_a_gradient(cfg, monkeypatch):
    vid = pipeline.create_demo_draft(cfg)
    monkeypatch.setattr(pipeline, "publish", lambda t, i: "urn:never")
    with pytest.raises(RuntimeError, match="AI-generated image"):
        pipeline.approve(vid)


def test_publish_allowed_without_ai_image_if_user_turns_requirement_off(cfg, monkeypatch):
    vid = pipeline.create_demo_draft(cfg)
    monkeypatch.setattr(pipeline, "publish", lambda t, i: "urn:ok")
    assert pipeline.approve(vid, require_ai_image=False) == "urn:ok"


def test_render_image_records_which_provider_made_it(cfg, monkeypatch):
    vid = pipeline.create_demo_draft(cfg)
    monkeypatch.setattr(pipeline, "render_card", lambda *a, **k: "pollinations")
    assert pipeline.render_image(vid, cfg) == "pollinations"
    assert pipeline.read_card(vid)["bg"] == "pollinations"
