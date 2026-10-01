from PIL import Image

from agent import image


def test_card_is_always_made_without_ai(tmp_path, monkeypatch):
    monkeypatch.setattr(image, "generate_background", lambda prompt: None)
    out = image.make_card("Five AI breakthroughs for this week",
                          "Smaller models and smarter agents make AI easier to use.",
                          "p", "#0A66C2", "Co", tmp_path / "c.png")
    assert Image.open(out).size == image.SIZE


def test_card_survives_ai_crash_and_empty_description(tmp_path, monkeypatch):
    def boom(prompt):
        raise RuntimeError("api down")
    monkeypatch.setattr(image, "InferenceClient", boom)
    monkeypatch.setenv("HF_TOKEN", "x")
    out = image.make_card("T", "", "prompt", "#0A66C2", "Co", tmp_path / "c.png")
    assert out.exists()


def test_long_text_is_trimmed_to_max_lines():
    from PIL import ImageDraw
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    lines = image._wrap(d, "word " * 200, image._font(30, 400), 600, 3)
    assert len(lines) == 3 and lines[-1].endswith("...")
