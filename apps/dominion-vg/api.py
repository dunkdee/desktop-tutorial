"""
Dominion Video Generator — API
Accepts generation requests, queues them to Redis, returns job status.
"""
import os
import json
import uuid
import redis
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/2")
QUEUE_KEY = "dvg:queue"
JOBS_KEY = "dvg:jobs"
OUTPUT_DIR = Path(os.getenv("DVG_OUTPUT_DIR", "/data/videos"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

r = redis.from_url(REDIS_URL, decode_responses=True)

app = FastAPI(
    title="Dominion Video Generator",
    description="Elite AI video generation powered by HunyuanVideo",
    version="1.0.0",
)

app.mount("/videos", StaticFiles(directory=str(OUTPUT_DIR)), name="videos")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=1000)
    duration_seconds: int = Field(default=5, ge=3, le=30)
    width: int = Field(default=1280)
    height: int = Field(default=720)
    grade_preset: Literal["cinematic", "noir", "golden_hour", "cold"] = "cinematic"
    guidance_scale: float = Field(default=6.0, ge=1.0, le=20.0)
    upscale: bool = True
    seed: int = Field(default=-1)


@app.exception_handler(Exception)
async def error_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": type(exc).__name__, "detail": str(exc)})


@app.get("/healthz")
def health():
    try:
        r.ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    queue_depth = r.llen(QUEUE_KEY)
    return {
        "status": "ok",
        "service": "dominion-video-generator",
        "redis": redis_ok,
        "queue_depth": queue_depth,
        "model": "HunyuanVideo",
    }


@app.post("/generate", status_code=202)
def generate(req: GenerateRequest):
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "queued",
        "prompt": req.prompt,
        "duration_seconds": req.duration_seconds,
        "width": req.width,
        "height": req.height,
        "grade_preset": req.grade_preset,
        "guidance_scale": req.guidance_scale,
        "upscale": req.upscale,
        "seed": req.seed,
        "video_url": None,
        "error": None,
    }
    r.hset(JOBS_KEY, job_id, json.dumps(job))
    r.rpush(QUEUE_KEY, json.dumps(job))
    return {"job_id": job_id, "status": "queued"}


@app.get("/status/{job_id}")
def status(job_id: str):
    raw = r.hget(JOBS_KEY, job_id)
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(raw)


@app.get("/jobs")
def list_jobs(limit: int = 20):
    all_jobs = r.hvals(JOBS_KEY)
    jobs = [json.loads(j) for j in all_jobs]
    jobs.sort(key=lambda x: x.get("job_id", ""), reverse=True)
    return {"jobs": jobs[:limit], "total": len(jobs)}


@app.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    r.hdel(JOBS_KEY, job_id)
    video = OUTPUT_DIR / f"{job_id}.mp4"
    video.unlink(missing_ok=True)
    return {"deleted": job_id}


@app.get("/videos/{filename}")
def get_video(filename: str):
    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(str(path), media_type="video/mp4", filename=filename)
