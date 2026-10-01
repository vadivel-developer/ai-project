# LinkedIn AI News Agent

Turns new AI YouTube videos into LinkedIn company-page posts.

**Flow:** YouTube RSS -> transcript -> LLM writes original post -> image card -> you approve -> LinkedIn.

## Setup
```bash
cd linkedin-ai-news-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # add your keys
```
Edit `config.yaml` with the YouTube channel IDs you want to follow.

## Use
```bash
python main.py run            # make drafts in ./drafts/<video_id>/ (post.txt + image.png)
python main.py list           # see status
python main.py approve <id>   # publish to LinkedIn after you review
python main.py skip <id>
python -m pytest              # 44 unit/API tests (no internet or keys needed)
python e2e/ui_check.py        # browser test of every UI button (app must be running)
```

## Web UI
```bash
python app.py        # open http://localhost:5000
```
Review drafts, edit text, preview the LinkedIn card, then Approve, Skip, Copy text or Download image.
Click **Try demo** to see it without any API keys.

## Post image
**An AI-generated image is required.** Free providers are tried in order (`IMAGE_PROVIDERS` in `.env`):
1. **Cloudflare Workers AI** (FLUX.1 schnell, ~230 free images/day): set `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`
2. **Pollinations** (no key needed, rate limited)
3. **Hugging Face** (small free credit): `HF_TOKEN`

The UI shows which one made the image. If none work, a gradient is used so a file always exists, but
**publishing is blocked** until you click **New AI background** and one succeeds
(turn this off with `require_ai_image: false` in `config.yaml`).

Every draft always gets an image with a **title** and a **short description**.
The background is an AI image (Hugging Face) if it works, otherwise a brand gradient, so image creation never fails.
In the UI you can edit the image title/description, click **Update image text**, or **New AI background**.

## Put it online (Render)
1. In Render: **New > Blueprint**, pick this repo and this branch (`render.yaml` is at the repo root).
2. Fill in the keys it asks for (`LLM_API_KEY`, `LLM_MODEL`, `HF_TOKEN`, ...). `APP_PASSWORD` is generated for you.
3. Render shows your live URL (like `https://ai-news-studio.onrender.com`). Log in with any username and the `APP_PASSWORD`.
- The site is password protected on purpose: it has an **Approve and publish** button for your company page.
- On Render's free plan the disk is wiped on restart, so drafts and history can be lost. Use a paid disk or a database for real use.

## Channel credit
Every post always ends with the channel name, the channel link and the video link, added by code (not left to the AI).
The image shows `Source: <channel>` in the corner.

## Notes
- Posting needs LinkedIn **Community Management API** approval. Until then, copy `post.txt` and `image.png` and post by hand.
- Posts are written in the LLM's own words and credit the creator with a link. Always review before approving.
- If image generation fails, a branded colour card with the title is used.
- Never commit `.env`.
