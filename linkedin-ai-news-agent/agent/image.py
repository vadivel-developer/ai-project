import textwrap
from pathlib import Path

from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFont

from .config import env

SIZE = (1200, 627)  # LinkedIn landscape


def _font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def generate_background(prompt: str) -> Image.Image | None:
    """Ask the free HF model for a background; return None on any failure."""
    try:
        client = InferenceClient(token=env("HF_TOKEN"))
        img = client.text_to_image(prompt, model=env("IMAGE_MODEL"))
        return img.convert("RGB").resize(SIZE)
    except Exception:
        return None


def make_card(title: str, prompt: str, brand_color: str, company: str, out: Path) -> Path:
    """Background (AI or solid brand colour) + our own crisp title text."""
    bg = generate_background(prompt) or Image.new("RGB", SIZE, brand_color)
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 120))
    img = Image.alpha_composite(bg.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)
    y = 180
    for line in textwrap.wrap(title, width=28)[:4]:
        draw.text((70, y), line, font=_font(64), fill="white")
        y += 80
    draw.text((70, SIZE[1] - 80), company, font=_font(34), fill="white")
    img.convert("RGB").save(out)
    return out
