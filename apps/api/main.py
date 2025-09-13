from fastapi import FastAPI, BackgroundTasks
import os, httpx

app = FastAPI()

@app.get("/healthz")
def health():
    return {"status": "ok", "env": os.getenv("APP_ENV","dev")}

def send_brevo_email(to_email: str, subject: str, html: str):
    key = os.environ["BREVO_API_KEY"]
    payload = {
        "sender": {"name": os.getenv("SENDER_NAME","Dominion Ark"),
                   "email": os.getenv("SENDER_EMAIL","noreply@dominionhealing.org")},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html
    }
    headers = {"api-key": key, "accept": "application/json", "content-type": "application/json"}
    with httpx.Client(timeout=15) as c:
        r = c.post("https://api.brevo.com/v3/smtp/email", json=payload, headers=headers)
        r.raise_for_status()

@app.post("/notify")
def notify(to: str, subject: str, body: str, bg: BackgroundTasks):
    bg.add_task(send_brevo_email, to, subject, f"<p>{body}</p>")
    return {"queued": True}