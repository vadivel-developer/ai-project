from agent import image


def test_card_falls_back_to_brand_colour(tmp_path, monkeypatch):
    monkeypatch.setattr(image, "generate_background", lambda prompt: None)
    out = image.make_card("A long AI news title for testing", "p", "#0A66C2", "Co", tmp_path / "c.png")
    assert out.exists()
