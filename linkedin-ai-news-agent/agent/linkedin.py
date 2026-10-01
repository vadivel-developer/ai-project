import requests

from .config import env

API = "https://api.linkedin.com/rest"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {env('LINKEDIN_ACCESS_TOKEN')}",
        "LinkedIn-Version": "202401",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def _upload_image(owner: str, image_path: str) -> str:
    r = requests.post(
        f"{API}/images?action=initializeUpload",
        headers=_headers(),
        json={"initializeUploadRequest": {"owner": owner}},
        timeout=30,
    )
    r.raise_for_status()
    value = r.json()["value"]
    with open(image_path, "rb") as f:
        requests.put(value["uploadUrl"], data=f, timeout=60).raise_for_status()
    return value["image"]


def publish(text: str, image_path: str) -> str:
    """Publish to the company page. Returns the post URN."""
    owner = f"urn:li:organization:{env('LINKEDIN_ORG_ID')}"
    image_urn = _upload_image(owner, image_path)
    body = {
        "author": owner,
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {"feedDistribution": "MAIN_FEED"},
        "content": {"media": {"id": image_urn}},
        "lifecycleState": "PUBLISHED",
    }
    r = requests.post(f"{API}/posts", headers=_headers(), json=body, timeout=30)
    r.raise_for_status()
    return r.headers.get("x-restli-id", "")
