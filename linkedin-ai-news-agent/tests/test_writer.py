from agent import writer


def test_card_text_parsed(monkeypatch):
    monkeypatch.setattr(writer, "_chat", lambda p: 'TITLE: "Agents Get Smarter"\nDESCRIPTION: Short and clear.')
    assert writer.write_card_text({"title": "x"}, "post") == ("Agents Get Smarter", "Short and clear.")


def test_card_text_falls_back_when_llm_fails(monkeypatch):
    def boom(p):
        raise RuntimeError("down")
    monkeypatch.setattr(writer, "_chat", boom)
    title, desc = writer.write_card_text({"title": "Video title"}, "First line of post\nsecond")
    assert title == "Video title" and desc == "First line of post"
