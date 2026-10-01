from agent import store


def test_add_seen_and_status(tmp_path):
    conn = store.connect(tmp_path / "t.db")
    video = {"id": "abc", "title": "T", "channel": "C", "url": "u"}
    assert not store.seen(conn, "abc")
    store.add(conn, video)
    store.add(conn, video)  # duplicate is ignored
    assert store.seen(conn, "abc")
    store.set_status(conn, "abc", "published")
    assert store.list_all(conn)[0]["status"] == "published"
