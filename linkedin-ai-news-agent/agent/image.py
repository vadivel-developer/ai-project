"""Post image: ALWAYS produced, with a title and a short description on it.

Background = AI image (Hugging Face) if available, otherwise a brand gradient.
The text is drawn by us, so it is always sharp and spelled correctly.
"""
from pathlib import Path

import base64
import io
import urllib.parse

import requests
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFont

from .config import ROOT, env

SIZE = (1200, 627)  # LinkedIn landscape
FONT_DIR = ROOT / "web" / "static" / "fonts"
PAD = 72


def _font(size: int, weight: int = 700):
    """Poppins if it can be read, else any bold system font, else Pillow's default."""
    for name in (f"poppins-latin-{weight}-normal.woff2", f"poppins-latin-{weight}-normal.woff"):
        try:
            return ImageFont.truetype(str(FONT_DIR / name), size)
        except Exception:
            continue
    for name in ("DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text: str, font, max_w: int, max_lines: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(" .,;:") + "..."
    return lines


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def gradient_background(brand_color: str) -> Image.Image:
    """Diagonal gradient from the brand colour to a deep purple."""
    a, b = _hex(brand_color), (60, 30, 140)
    img = Image.new("RGB", SIZE)
    px = img.load()
    w, h = SIZE
    for y in range(h):
        for x in range(w):
            t = (x / w * 0.7) + (y / h * 0.3)
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return img


def _cloudflare(prompt: str) -> Image.Image:
    acct, token = env("CLOUDFLARE_ACCOUNT_ID"), env("CLOUDFLARE_API_TOKEN")
    if not (acct and token):
        raise RuntimeError("Cloudflare keys not set")
    r = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/@cf/black-forest-labs/flux-1-schnell",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": prompt, "steps": 4}, timeout=90)
    r.raise_for_status()
    return Image.open(io.BytesIO(base64.b64decode(r.json()["result"]["image"])))


def _pollinations(prompt: str) -> Image.Image:
    url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"
           f"?width={SIZE[0]}&height={SIZE[1]}&model=flux&nologo=true")
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content))


def _huggingface(prompt: str) -> Image.Image:
    if not env("HF_TOKEN"):
        raise RuntimeError("HF_TOKEN not set")
    return InferenceClient(token=env("HF_TOKEN")).text_to_image(prompt, model=env("IMAGE_MODEL"))


PROVIDERS = {"cloudflare": _cloudflare, "pollinations": _pollinations, "huggingface": _huggingface}


def generate_background(prompt: str) -> tuple[Image.Image | None, str | None]:
    """Try each free provider in order (IMAGE_PROVIDERS). Returns (image, provider) or (None, None)."""
    order = [n.strip() for n in env("IMAGE_PROVIDERS", "cloudflare,pollinations,huggingface").split(",")]
    for name in order:
        fn = PROVIDERS.get(name)
        if not fn:
            continue
        try:
            img = fn(prompt).convert("RGB")
            if img.size[0] >= 256:
                return img.resize(SIZE), name
        except Exception:
            continue
    return None, None


def make_card(*args, **kwargs) -> Path:
    """Same as render_card but returns just the path."""
    render_card(*args, **kwargs)
    return args[5] if len(args) > 5 else kwargs["out"]


def render_card(title: str, description: str, prompt: str, brand_color: str,
                company: str, out: Path, use_ai: bool = True, source: str = "") -> str:
    """Always writes an image to `out`. Returns which background was used:
    'cloudflare' | 'pollinations' | 'huggingface' | 'gradient'."""
    bg, provider = (None, None)
    if use_ai:
        bg, provider = generate_background(prompt or f"Abstract modern illustration, no text, about: {title}")
    if bg is None:
        bg, provider = gradient_background(brand_color), "gradient"
    img = bg.convert("RGBA")

    # dark fade on the left so white text stays readable on any background
    fade = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fade)
    for x in range(SIZE[0]):
        fd.line([(x, 0), (x, SIZE[1])], fill=(8, 10, 30, int(200 * max(0.25, 1 - x / (SIZE[0] * 0.95)))))
    img = Image.alpha_composite(img, fade)

    d = ImageDraw.Draw(img)
    max_w = SIZE[0] - PAD * 2 - 80
    t_font, d_font, c_font = _font(60, 700), _font(30, 400), _font(26, 600)

    t_lines = _wrap(d, title, t_font, max_w, 3)
    d_lines = _wrap(d, description, d_font, max_w, 3)
    block = len(t_lines) * 78 + (14 + len(d_lines) * 44 if d_lines else 0)
    y = max(120, (SIZE[1] - 90 - block) // 2 + 30)  # centre the text block
    d.rounded_rectangle((PAD, y - 40, PAD + 74, y - 32), radius=4, fill="white")  # accent bar
    for line in t_lines:
        d.text((PAD, y), line, font=t_font, fill="white")
        y += 78
    y += 14
    for line in d_lines:
        d.text((PAD, y), line, font=d_font, fill=(226, 230, 245))
        y += 44
    d.text((PAD, SIZE[1] - 70), company, font=c_font, fill="white")
    if source:  # channel credit, bottom right
        label = f"Source: {source}"
        s_font = _font(24, 400)
        while d.textlength(label, font=s_font) > SIZE[0] // 2 and len(label) > 12:
            label = label[:-4].rstrip() + "..."
        d.text((SIZE[0] - PAD - d.textlength(label, font=s_font), SIZE[1] - 66), label, font=s_font, fill=(226, 230, 245))

    img.convert("RGB").save(out)
    return provider
