import asyncio
import os
from datetime import datetime
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Dominion Browser Agents")

# In-memory task tracker
_tasks: Dict[str, dict] = {}


class RunRequest(BaseModel):
    task: str
    params: Optional[Dict[str, Any]] = {}


async def _execute(task_id: str, task: str, params: dict):
    _tasks[task_id] = {"status": "running", "started": datetime.utcnow().isoformat()}
    try:
        from agents import run_task
        result = await run_task(task, params)
        _tasks[task_id].update({"status": "done", "result": result, "finished": datetime.utcnow().isoformat()})
    except Exception as e:
        _tasks[task_id].update({"status": "error", "error": str(e), "finished": datetime.utcnow().isoformat()})


@app.post("/run")
async def run(req: RunRequest, background_tasks: BackgroundTasks):
    task_id = f"{req.task}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    background_tasks.add_task(_execute, task_id, req.task, req.params or {})
    return {"task_id": task_id, "status": "queued"}


@app.get("/status/{task_id}")
def status(task_id: str):
    return _tasks.get(task_id, {"status": "not_found"})


@app.get("/status")
def all_status():
    return {"tasks": _tasks, "count": len(_tasks)}


@app.get("/health")
def health():
    return {"status": "ok", "agent": "browser-agents", "tasks_in_memory": len(_tasks)}


@app.get("/")
def root():
    return {
        "service": "Dominion Browser Agents",
        "endpoints": [
            "POST /run — { task, params }",
            "GET /status/{task_id}",
            "GET /health",
        ],
        "tasks": [
            "browse_test",
            "tiktok_post",
            "instagram_post",
            "twitter_post",
            "pph_submit",
            "scrape_leads",
            "refresh_token",
        ],
    }
