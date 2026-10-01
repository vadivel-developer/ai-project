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
python -m pytest              # tests
```

## Web UI
```bash
python app.py        # open http://localhost:5000
```
Review drafts, edit text, preview the LinkedIn card, then Approve, Skip, Copy text or Download image.
Click **Try demo** to see it without any API keys.

## Notes
- Posting needs LinkedIn **Community Management API** approval. Until then, copy `post.txt` and `image.png` and post by hand.
- Posts are written in the LLM's own words and credit the creator with a link. Always review before approving.
- If image generation fails, a branded colour card with the title is used.
- Never commit `.env`.
