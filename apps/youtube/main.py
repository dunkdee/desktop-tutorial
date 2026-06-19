from fastapi import FastAPI, BackgroundTasks, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
import os
import uuid

from script_generator import generate_script, generate_scene_breakdown, generate_title_and_description
from pipeline import run_pipeline, PipelineResult
from youtube_uploader import get_oauth_url, exchange_code

app = FastAPI(title="Higgins Movie Generator", description="Claude Fable 5 → YouTube")

_api_key_header = APIKeyHeader(name="X-Higgins-Key", auto_error=True)
_jobs: dict[str, PipelineResult] = {}


def _require_key(key: str = Security(_api_key_header)):
    expected = os.environ.get("HIGGINS_API_KEY", "")
    if not expected or key != expected:
        raise HTTPException(status_code=403, detail="Invalid API key")


class ScriptRequest(BaseModel):
    prompt: str
    title: str


class PipelineRequest(BaseModel):
    prompt: str
    title: str
    description: str = ""
    privacy: str = "private"
    upload: bool = True


@app.get("/healthz")
def health():
    runway_set = bool(os.environ.get("RUNWAY_API_KEY"))
    anthropic_set = bool(os.environ.get("ANTHROPIC_API_KEY"))
    youtube_set = bool(os.environ.get("YOUTUBE_CLIENT_ID"))
    return {
        "status": "ok",
        "service": "higgins-movie-generator",
        "anthropic_key": anthropic_set,
        "runway_key": runway_set,
        "youtube_creds": youtube_set,
    }


@app.post("/script/generate")
def create_script(req: ScriptRequest, _=Security(_require_key)):
    """Generate script + scene breakdown + YouTube metadata. No video, no upload."""
    script = generate_script(req.prompt, req.title)
    scenes = generate_scene_breakdown(script)
    meta = generate_title_and_description(script, req.title)
    return {
        "title": req.title,
        "script": script,
        "scenes": scenes,
        "youtube_meta": meta,
    }


@app.post("/pipeline/start")
def start_pipeline(req: PipelineRequest, bg: BackgroundTasks, _=Security(_require_key)):
    """Start full pipeline: script → Runway video → YouTube. Poll /pipeline/status/{job_id}."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = PipelineResult(title=req.title, script="", scene_count=0, status="queued")

    def _run():
        try:
            _jobs[job_id] = run_pipeline(
                prompt=req.prompt,
                title=req.title,
                description=req.description,
                privacy=req.privacy,
                upload=req.upload,
            )
        except Exception as e:
            _jobs[job_id].status = "failed"
            _jobs[job_id].errors.append(str(e))

    bg.add_task(_run)
    return {"job_id": job_id, "status": "queued"}


@app.get("/pipeline/status/{job_id}")
def pipeline_status(job_id: str, _=Security(_require_key)):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    r = _jobs[job_id]
    return {
        "job_id": job_id,
        "status": r.status,
        "title": r.title,
        "scene_count": r.scene_count,
        "youtube_url": r.youtube_url,
        "errors": r.errors,
    }


@app.get("/youtube/auth")
def youtube_auth():
    return {"auth_url": get_oauth_url()}


@app.get("/youtube/callback")
def youtube_callback(code: str):
    tokens = exchange_code(code)
    return {"status": "authorized", "scope": tokens.get("scope", "")}

