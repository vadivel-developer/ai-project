from agent import linkedin


class Resp:
    def __init__(self, data=None, headers=None):
        self._d, self.headers = data or {}, headers or {}
    def raise_for_status(self): pass
    def json(self): return self._d


def test_publish_uploads_image_then_posts(tmp_path, monkeypatch):
    monkeypatch.setenv("LINKEDIN_ORG_ID", "999")
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "tok")
    img = tmp_path / "i.png"; img.write_bytes(b"png")
    calls = []

    def post(url, **kw):
        calls.append(("POST", url, kw))
        if "initializeUpload" in url:
            return Resp({"value": {"uploadUrl": "https://up", "image": "urn:li:image:1"}})
        return Resp(headers={"x-restli-id": "urn:li:share:7"})

    monkeypatch.setattr(linkedin.requests, "post", post)
    monkeypatch.setattr(linkedin.requests, "put", lambda url, **kw: calls.append(("PUT", url, kw)) or Resp())
    assert linkedin.publish("hello", str(img)) == "urn:li:share:7"
    assert [c[0] for c in calls] == ["POST", "PUT", "POST"]
    body = calls[-1][2]["json"]
    assert body["author"] == "urn:li:organization:999" and body["commentary"] == "hello"
    assert body["content"]["media"]["id"] == "urn:li:image:1"
    assert calls[0][2]["headers"]["Authorization"] == "Bearer tok"
