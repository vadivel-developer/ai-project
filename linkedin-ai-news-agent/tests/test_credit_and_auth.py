import app as webapp
from agent import image, writer
from PIL import Image

V = {"title": "T", "url": "https://y/1", "channel": "Two Minute Papers",
     "channel_url": "https://www.youtube.com/channel/UC1"}


def test_credit_added_when_missing():
    out = writer.with_credit("Great post #AI", V)
    assert "Source: Two Minute Papers" in out
    assert "Channel: https://www.youtube.com/channel/UC1" in out
    assert "Watch the full video: https://y/1" in out


def test_credit_not_duplicated_when_llm_already_wrote_it():
    post = "Thanks to Two Minute Papers! https://y/1 https://www.youtube.com/channel/UC1"
    assert writer.with_credit(post, V) == post


def test_credit_only_adds_what_is_missing():
    out = writer.with_credit("From Two Minute Papers - https://y/1", V)
    assert out.count("https://y/1") == 1 and "Channel: " in out and "Source:" not in out


def test_image_with_source_line_renders(tmp_path):
    out = image.make_card("Title", "Desc", "", "#0A66C2", "Acme", tmp_path / "a.png",
                          use_ai=False, source="A very very very long channel name " * 4)
    assert Image.open(out).size == image.SIZE


def test_no_password_means_open(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert webapp.app.test_client().get("/api/config").status_code == 200


def test_password_blocks_everything_without_login(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "s3cret")
    c = webapp.app.test_client()
    for path in ("/", "/api/drafts", "/static/fonts/poppins-latin-400-normal.woff2"):
        r = c.get(path)
        assert r.status_code == 401 and "Basic" in r.headers["WWW-Authenticate"]
    assert c.post("/api/demo").status_code == 401  # cannot publish/modify either


def test_password_wrong_and_right(monkeypatch):
    import base64
    monkeypatch.setenv("APP_PASSWORD", "s3cret")
    c = webapp.app.test_client()
    h = lambda pw: {"Authorization": "Basic " + base64.b64encode(f"me:{pw}".encode()).decode()}
    assert c.get("/api/config", headers=h("wrong")).status_code == 401
    assert c.get("/api/config", headers=h("s3cret")).status_code == 200
