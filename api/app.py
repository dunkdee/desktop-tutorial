from flask import Flask, jsonify
import os, requests

app = Flask(__name__)

def flag(v): 
    return "present" if (v and str(v).strip()) else "missing"

@app.route("/")
def root():
    return {
        "status": "👑 Baby is LIVE",
        "integrations": {
            "YouTube_API_KEY": flag(os.getenv("YOUTUBE_API_KEY")),
            "Gumroad_Token": flag(os.getenv("GUMROAD_TOKEN")),
            "OANDA_Account": flag(os.getenv("OANDA_ACCOUNT_ID")),
            "BinanceUS_API": flag(os.getenv("BINANCE_API_KEY")),
            "Brevo_API": flag(os.getenv("BREVO_API_KEY"))
        }
    }

@app.route("/youtube")
def youtube():
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return jsonify(error="Missing YOUTUBE_API_KEY"), 400
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part":"snippet","chart":"mostPopular","maxResults":1,"key":key},
        timeout=20
    )
    return (r.json(), r.status_code)

@app.route("/gumroad")
def gumroad():
    token = os.getenv("GUMROAD_TOKEN")
    if not token:
        return jsonify(error="Missing GUMROAD_TOKEN"), 400
    r = requests.get(
        "https://api.gumroad.com/v2/products",
        params={"access_token": token},
        timeout=20
    )
    return (r.json(), r.status_code)

@app.route("/oanda")
def oanda():
    key  = os.getenv("OANDA_API_KEY")
    acct = os.getenv("OANDA_ACCOUNT_ID")
    if not key or not acct:
        return jsonify(error="Missing OANDA keys"), 400
    url = f"https://api-fxpractice.oanda.com/v3/accounts/{acct}/summary"
    r = requests.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=20)
    return (r.json(), r.status_code)

@app.route("/binance")
def binance():
    r = requests.get("https://api.binance.us/api/v3/time", timeout=20)
    return (r.json(), r.status_code)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
