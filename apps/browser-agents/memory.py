"""
Agent memory — reads past learnings from vault, writes new ones after each run.
Agents load this context before executing so they improve over time.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

BABY_API = os.getenv("BABY_API_URL", "http://baby-api:8080")
LEARNINGS_FILE = Path("/app/learnings.json")


def _load_local() -> dict:
    if LEARNINGS_FILE.exists():
        try:
            return json.loads(LEARNINGS_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_local(data: dict):
    LEARNINGS_FILE.write_text(json.dumps(data, indent=2))


def get_context(task_type: str) -> str:
    """Return past learnings for a task type as a context string for the agent."""
    data = _load_local()
    entries = data.get(task_type, [])
    if not entries:
        return ""
    recent = entries[-10:]
    lines = [f"## Past {task_type} runs (most recent last)"]
    for e in recent:
        status = "SUCCESS" if e.get("success") else "FAILED"
        lines.append(f"- [{status}] {e.get('date', '?')}: {e.get('summary', '')}")
    return "\n".join(lines)


def log_result(task_type: str, success: bool, summary: str, extra: Optional[dict] = None):
    """Persist a task result to local learnings file and vault."""
    data = _load_local()
    if task_type not in data:
        data[task_type] = []
    entry = {
        "date": datetime.utcnow().isoformat(),
        "success": success,
        "summary": summary[:500],
    }
    if extra:
        entry["extra"] = extra
    data[task_type].append(entry)
    data[task_type] = data[task_type][-50:]  # Keep last 50 per task type
    _save_local(data)

    # Also write to vault via baby-api (fire-and-forget)
    try:
        import asyncio
        asyncio.create_task(_post_vault(task_type, success, summary))
    except RuntimeError:
        pass  # No event loop in sync context — local file is enough


async def _post_vault(task_type: str, success: bool, summary: str):
    status_str = "success" if success else "failed"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{BABY_API}/vault/inbox",
                json={
                    "title": f"Agent {status_str}: {task_type}",
                    "content": summary,
                    "agent": "browser-agent",
                    "tags": ["agent-learning", task_type, status_str],
                },
            )
    except Exception:
        pass  # Non-fatal — local file already saved
