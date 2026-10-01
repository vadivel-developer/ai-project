import pytest

from agent import config, pipeline

CFG = {
    "channels": [{"name": "Chan", "id": "UC123"}],
    "max_videos_per_run": 3, "posts_per_day": 1,
    "company_name": "Acme AI", "brand_color": "#0A66C2",
    "hashtags": ["#AI", "#Tech"],
}


@pytest.fixture(autouse=True)
def sandbox(tmp_path, monkeypatch):
    """Every test gets its own database and drafts folder."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.db")
    monkeypatch.setattr(pipeline, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(pipeline, "load_config", lambda: CFG, raising=False)
    for k in ("HF_TOKEN", "LLM_API_KEY", "LINKEDIN_ACCESS_TOKEN", "LINKEDIN_ORG_ID"):
        monkeypatch.delenv(k, raising=False)
    return tmp_path


@pytest.fixture
def cfg():
    return dict(CFG)
