import os
import json
import httpx
from pathlib import Path


TOKEN_FILE = os.path.expanduser("~/.config/youtube_tokens.json")


def _load_tokens() -> dict:
    if Path(TOKEN_FILE).exists():
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return {}


def _save_tokens(tokens: dict):
    Path(TOKEN_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)


def _refresh_access_token() -> str:
    tokens = _load_tokens()
    if not tokens.get("refresh_token"):
        raise RuntimeError("No YouTube refresh_token. Complete OAuth2 flow first via /youtube/auth.")

    r = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["YOUTUBE_CLIENT_ID"],
            "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
            "refresh_token": tokens["refresh_token"],
            "grant_type": "refresh_token",
        },
    )
    r.raise_for_status()
    data = r.json()
    tokens["access_token"] = data["access_token"]
    _save_tokens(tokens)
    return data["access_token"]


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = "1",
    privacy: str = "private",
) -> dict:
    """
    Upload a video to YouTube using the Data API v3 resumable upload.
    Returns the YouTube video resource dict (includes 'id').
    privacy: 'private' | 'unlisted' | 'public'
    """
    access_token = _refresh_access_token()

    metadata = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags[:500],
            "categoryId": category_id,
        },
        "status": {"privacyStatus": privacy},
    }

    # Initiate resumable upload session
    init_r = httpx.post(
        "https://www.googleapis.com/upload/youtube/v3/videos",
        params={"uploadType": "resumable", "part": "snippet,status"},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
        },
        json=metadata,
        timeout=30,
    )
    init_r.raise_for_status()
    upload_url = init_r.headers["Location"]

    video_bytes = Path(video_path).read_bytes()
    upload_r = httpx.put(
        upload_url,
        content=video_bytes,
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(len(video_bytes)),
        },
        timeout=600,
    )
    upload_r.raise_for_status()
    return upload_r.json()


def get_oauth_url() -> str:
    """Return the URL to send the user to for YouTube OAuth2 consent."""
    params = httpx.QueryParams(
        {
            "client_id": os.environ["YOUTUBE_CLIENT_ID"],
            "redirect_uri": os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:8000/youtube/callback"),
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/youtube.upload",
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"


def exchange_code(code: str) -> dict:
    """Exchange OAuth2 authorization code for tokens and persist them."""
    r = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["YOUTUBE_CLIENT_ID"],
            "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": os.getenv("YOUTUBE_REDIRECT_URI", "http://localhost:8000/youtube/callback"),
        },
    )
    r.raise_for_status()
    tokens = r.json()
    _save_tokens(tokens)
    return tokens
