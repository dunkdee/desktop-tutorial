from flask import Flask, jsonify
import os, requests

app = Flask(__name__)

def flag(v):
    return "present" if (v and str(v).strip()) else "missing"

def gumroad_get(path, token, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    return requests.get(
        f"https://api.gumroad.com/v2/{path}",
        headers=headers,
        params=params or {},
        timeout=20,
    )

@app.route("/")
def root():
    return {
        "status": "● Dominion Empire API — LIVE",
        "integrations": {
            "YouTube_API_KEY":    flag(os.getenv("YOUTUBE_API_KEY")),
            "Gumroad_Token":      flag(os.getenv("GUMROAD_TOKEN")),
            "OANDA_Account":      flag(os.getenv("OANDA_ACCOUNT_ID")),
            "BinanceUS_API":      flag(os.getenv("BINANCE_API_KEY")),
            "Brevo_API":          flag(os.getenv("BREVO_API_KEY")),
            "Gemini_API":         flag(os.getenv("GEMINI_API_KEY")),
            "Google_Drive":       flag(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")),
            "Google_Analytics":   flag(os.getenv("GA4_MEASUREMENT_ID")),
        }
    }

@app.route("/gemini")
def gemini_status():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return jsonify(error="GEMINI_API_KEY not set"), 400
    try:
        from google import genai
        c = genai.Client(api_key=key)
        r = c.models.generate_content(model="gemini-2.5-flash", contents="Reply with one word: ONLINE")
        return jsonify({"status": "connected", "response": r.text.strip()})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 500

@app.route("/youtube")
def youtube():
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return jsonify(error="Missing YOUTUBE_API_KEY"), 400
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "snippet", "chart": "mostPopular", "maxResults": 1, "key": key},
        timeout=20,
    )
    return jsonify(r.json()), r.status_code

@app.route("/gumroad")
def gumroad():
    token = os.getenv("GUMROAD_TOKEN")
    if not token:
        return jsonify(error="GUMROAD_TOKEN not set"), 400
    r = gumroad_get("products", token)
    data = r.json()
    if not data.get("success"):
        return jsonify(error="Gumroad rejected the token", detail=data.get("message", "unknown")), r.status_code
    products = data.get("products", [])
    return jsonify({
        "success": True,
        "product_count": len(products),
        "products": [
            {
                "name": p.get("name"),
                "published": p.get("published"),
                "price_cents": p.get("price"),
                "sales_count": p.get("sales_count"),
                "url": p.get("short_url"),
            }
            for p in products
        ],
    })

@app.route("/gumroad/sales")
def gumroad_sales():
    token = os.getenv("GUMROAD_TOKEN")
    if not token:
        return jsonify(error="GUMROAD_TOKEN not set"), 400
    r = gumroad_get("sales", token)
    data = r.json()
    if not data.get("success"):
        return jsonify(error="Gumroad rejected the token", detail=data.get("message", "unknown")), r.status_code
    sales = data.get("sales", [])
    total = sum(s.get("price", 0) for s in sales) / 100
    return jsonify({
        "success": True,
        "sale_count": len(sales),
        "total_revenue_usd": round(total, 2),
        "recent_sales": [
            {
                "product": s.get("product_name"),
                "amount_usd": s.get("price", 0) / 100,
                "email": s.get("email"),
                "created_at": s.get("created_at"),
                "refunded": s.get("refunded"),
            }
            for s in sales[:10]
        ],
    })

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
