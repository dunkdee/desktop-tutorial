import os, json, requests
from fastapi import FastAPI, UploadFile, Form
from dotenv import load_dotenv

ROOT = os.path.expanduser("~/DominionsArk")
ENVF = os.path.join(ROOT, ".env")
TOK_FILE = os.path.join(ROOT, "data/tiktok_tokens.json")
USER_FILE = os.path.join(ROOT, "data/tiktok_user.json")

load_dotenv(ENVF)
CLIENT_ID = os.getenv("TIKTOK_CLIENT_ID")
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI")

app = FastAPI()

def save_tokens(data):
    os.makedirs(os.path.dirname(TOK_FILE), exist_ok=True)
    with open(TOK_FILE, "w") as f:
        json.dump(data, f)

def load_tokens():
    if os.path.exists(TOK_FILE):
        with open(TOK_FILE) as f:
            return json.load(f)
    return None

def save_user(user_info):
    with open(USER_FILE, "w") as f:
        json.dump(user_info, f)

def load_user():
    if os.path.exists(USER_FILE):
        with open(USER_FILE) as f:
            return json.load(f)
    return None

def get_access_token():
    tokens = load_tokens()
    if tokens and "access_token" in tokens.get("data", {}):
        return tokens["data"]["access_token"]
    return None

@app.get("/tiktok/callback")
async def tiktok_callback(code: str, state: str = None):
    url = "https://open-api.tiktok.com/oauth/access_token"
    payload = {
        "client_key": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }
    r = requests.post(url, data=payload)
    r.raise_for_status()
    data = r.json()
    save_tokens(data)

    access_token = data["data"]["access_token"]
    user_info = requests.get(
        "https://open-api.tiktok.com/user/info/",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()
    save_user(user_info)

    username = user_info.get("data", {}).get("user", {}).get("username")
    if username != "lawrence72":
        return {"status": "error", "message": "Unauthorized account", "user": user_info}

    return {"status": "ok", "message": "Account confirmed", "user": user_info}

@app.post("/tiktok/upload")
async def upload_video(video: UploadFile, caption: str = Form(...)):
    user_info = load_user()
    if not user_info:
        return {"error": "No user confirmed"}
    if user_info.get("data", {}).get("user", {}).get("username") != "lawrence72":
        return {"error": "Uploads locked to lawrence72 only"}

    access_token = get_access_token()
    if not access_token:
        return {"error": "No access token. Please authenticate first."}

    upload_url = "https://open-api.tiktokglobalshop.com/video/upload/"
    headers = {"Authorization": f"Bearer {access_token}"}
    files = {"video": (video.filename, await video.read(), "video/mp4")}
    data = {"caption": caption}

    r = requests.post(upload_url, headers=headers, files=files, data=data)
    try:
        r.raise_for_status()
    except Exception as e:
        return {"error": str(e), "response": r.text}

    return {"status": "success", "response": r.json()}
