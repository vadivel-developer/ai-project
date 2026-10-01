from openai import OpenAI

from .config import env

PROMPT = """You write LinkedIn posts for the company "{company}".
Source: YouTube video "{title}" by {channel} ({url}).
Transcript (may be truncated):
{transcript}

Write an ORIGINAL LinkedIn post (120-180 words) in your own words:
- Strong first line hook
- 3 short key takeaways as bullet points
- One closing question to invite comments
- Credit the creator and include the video link
- Do not copy sentences from the transcript
- End with these hashtags: {hashtags}
Return only the post text."""

IMAGE_PROMPT = (
    "Write a short (max 25 words) visual description for an abstract, clean, modern "
    "illustration, no text in the image, that represents this AI news: {title}"
)


def _client() -> OpenAI:
    return OpenAI(api_key=env("LLM_API_KEY"), base_url=env("LLM_BASE_URL"))


def _chat(prompt: str) -> str:
    resp = _client().chat.completions.create(
        model=env("LLM_MODEL"),
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def write_post(video: dict, transcript: str, cfg: dict) -> str:
    return _chat(
        PROMPT.format(
            company=cfg["company_name"],
            title=video["title"],
            channel=video["channel"],
            url=video["url"],
            transcript=transcript[:12000],
            hashtags=" ".join(cfg["hashtags"]),
        )
    )


def write_image_prompt(video: dict) -> str:
    return _chat(IMAGE_PROMPT.format(title=video["title"]))
