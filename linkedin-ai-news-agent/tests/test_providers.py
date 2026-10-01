import base64
import io

import pytest
from PIL import Image

from agent import image


def png_bytes(color="red", size=(400, 300)):
    buf = io.BytesIO(); Image.new("RGB", size, color).save(buf, "PNG"); return buf.getvalue()


class Resp:
    def __init__(self, json_data=None, content=b"", ok=True):
        self._j, self.content, self.ok = json_data, content, ok
    def raise_for_status(self):
        if not self.ok: raise RuntimeError("HTTP 500")
    def json(self): return self._j


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acct")
    monkeypatch.setenv("CLOUDFLARE_API_TOKEN", "tok")
    monkeypatch.setenv("HF_TOKEN", "hf")


def cf_ok(url, **kw):
    cf_ok.called = (url, kw)
    return Resp({"result": {"image": base64.b64encode(png_bytes("blue")).decode()}})


def test_cloudflare_is_tried_first_and_request_is_correct(keys, monkeypatch):
    monkeypatch.setattr(image.requests, "post", cf_ok)
    img, provider = image.generate_background("a prompt")
    assert provider == "cloudflare" and img.size == image.SIZE
    url, kw = cf_ok.called
    assert "/accounts/acct/ai/run/@cf/black-forest-labs/flux-1-schnell" in url
    assert kw["headers"]["Authorization"] == "Bearer tok" and kw["json"]["prompt"] == "a prompt"


def test_falls_back_to_pollinations_when_cloudflare_fails(keys, monkeypatch):
    monkeypatch.setattr(image.requests, "post", lambda *a, **k: Resp(ok=False))
    monkeypatch.setattr(image.requests, "get", lambda url, **k: Resp(content=png_bytes("green")))
    assert image.generate_background("p")[1] == "pollinations"


def test_pollinations_works_with_no_keys_at_all(monkeypatch):
    seen = {}
    monkeypatch.setattr(image.requests, "get", lambda url, **k: seen.update(url=url) or Resp(content=png_bytes()))
    assert image.generate_background("a cat in space")[1] == "pollinations"
    assert "a%20cat%20in%20space" in seen["url"]


def test_falls_back_to_huggingface_last(keys, monkeypatch):
    monkeypatch.setattr(image.requests, "post", lambda *a, **k: Resp(ok=False))
    monkeypatch.setattr(image.requests, "get", lambda *a, **k: Resp(ok=False))

    class HF:
        def __init__(self, token): pass
        def text_to_image(self, prompt, model=None): return Image.new("RGB", (512, 512), "purple")
    monkeypatch.setattr(image, "InferenceClient", HF)
    assert image.generate_background("p")[1] == "huggingface"


def test_all_providers_fail_returns_none(keys, monkeypatch):
    monkeypatch.setattr(image.requests, "post", lambda *a, **k: Resp(ok=False))
    monkeypatch.setattr(image.requests, "get", lambda *a, **k: Resp(ok=False))
    monkeypatch.setattr(image, "InferenceClient", lambda token: (_ for _ in ()).throw(RuntimeError("down")))
    assert image.generate_background("p") == (None, None)


def test_provider_order_can_be_changed(keys, monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDERS", "pollinations")
    monkeypatch.setattr(image.requests, "post", lambda *a, **k: pytest.fail("cloudflare must not be called"))
    monkeypatch.setattr(image.requests, "get", lambda *a, **k: Resp(content=png_bytes()))
    assert image.generate_background("p")[1] == "pollinations"


def test_tiny_or_broken_images_are_rejected(monkeypatch):
    monkeypatch.setenv("IMAGE_PROVIDERS", "pollinations")
    monkeypatch.setattr(image.requests, "get", lambda *a, **k: Resp(content=png_bytes(size=(32, 32))))
    assert image.generate_background("p") == (None, None)
    monkeypatch.setattr(image.requests, "get", lambda *a, **k: Resp(content=b"<html>error</html>"))
    assert image.generate_background("p") == (None, None)


def test_render_card_reports_provider_and_uses_title_when_prompt_empty(tmp_path, monkeypatch):
    seen = {}
    def fake(prompt):
        seen["prompt"] = prompt
        return Image.new("RGB", image.SIZE, "teal"), "cloudflare"
    monkeypatch.setattr(image, "generate_background", fake)
    got = image.render_card("My title", "desc", "", "#0A66C2", "Co", tmp_path / "o.png")
    assert got == "cloudflare" and "My title" in seen["prompt"]


def test_render_card_reports_gradient_when_ai_unavailable(tmp_path, monkeypatch):
    monkeypatch.setattr(image, "generate_background", lambda p: (None, None))
    assert image.render_card("T", "d", "p", "#0A66C2", "Co", tmp_path / "o.png") == "gradient"
