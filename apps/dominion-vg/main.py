"""
Dominion Video Generator — REST API
POST /generate  →  { job_id, status, video_url }
GET  /status/{job_id}  →  { job_id, status, video_url, error }
GET  /healthz
"""
import os
import uuid
import threading
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from generator import generate_video, OUTPUT_DIR

app = FastAPI(title="Dominion Video Generator", version="1.0.0")

_jobs: dict[str, dict] = {}
_lock = threading.Lock()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(OUTPUT_DIR)), name="videos")


class GenerateRequest(BaseModel):
    prompt: str
    duration_seconds: int = 6


def _run_job(job_id: str, prompt: str, duration_seconds: int):
    with _lock:
        _jobs[job_id]["status"] = "processing"
    try:
        path = generate_video(prompt, duration_seconds, job_id)
        host = os.getenv("DVG_PUBLIC_URL", "http://localhost:8002")
        video_url = f"{host}/videos/{Path(path).name}"
        with _lock:
            _jobs[job_id].update({"status": "completed", "video_url": video_url, "path": path})
    except Exception as e:
        with _lock:
            _jobs[job_id].update({"status": "failed", "error": str(e)})


@app.get("/healthz")
def health():
    import torch
    return {
        "status": "ok",
        "service": "dominion-video-generator",
        "gpu": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none",
    }


@app.post("/generate")
def generate(req: GenerateRequest):
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {"status": "queued", "video_url": None, "error": None}
    t = threading.Thread(target=_run_job, args=(job_id, req.prompt, req.duration_seconds), daemon=True)
    t.start()
    return {"job_id": job_id, "status": "queued"}


@app.get("/status/{job_id}")
def status(job_id: str):
    with _lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **job}


@app.get("/videos/{filename}")
def get_video(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(str(path), media_type="video/mp4")
