from flask import Flask
import os, requests

app = Flask(__name__)

@app.route("/")
def index():
    # Pull secrets from env
    youtube = os.getenv("YOUTUBE_CLIENT_ID", "not set")
    gumroad = os.getenv("GUMROAD_TOKEN", "not set")
    oanda = os.getenv("OANDA_ACCOUNT_ID", "not set")

    # Placeholder external calls (can be extended later)
    # Example: call YouTube API with the API key if available
    yt_status = "no api key"
    yt_key = os.getenv("YOUTUBE_API_KEY")
    if yt_key:
        yt_status = "ready"

    return {
        "status": "👑 Baby is live",
        "youtube_client_id": youtube,
        "youtube_status": yt_status,
        "gumroad_token_present": bool(gumroad),
        "oanda_account_id": oanda
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
