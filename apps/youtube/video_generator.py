"""
Video generation backend for the Higgins movie pipeline.

Priority order:
  1. Dominion Video Generator (self-hosted, free) — set DVG_URL
  2. Runway ML (paid fallback)                   — set RUNWAY_API_KEY
  3. Stub (local testing only)
"""
import os
import time
import httpx
from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoJob:
    job_id: str
    status: str  # queued | processing | completed | failed
    video_url: Optional[str] = None
    error: Optional[str] = None


class DominionVideoGenerator:
    """
    Calls the self-hosted Dominion Video Generator service.
    Set DVG_URL to the service address (e.g. http://dominion-vg:8002).
    Zero cost per video — runs on open-source CogVideoX model.
    """

    def __init__(self):
        self.base_url = os.environ["DVG_URL"].rstrip("/")
        self.client = httpx.Client(base_url=self.base_url, timeout=30)

    def create_video(self, visual_prompt: str, duration_seconds: int, voiceover_text: str = "") -> VideoJob:
        r = self.client.post("/generate", json={
            "prompt": visual_prompt[:500],
            "duration_seconds": max(6, min(30, duration_seconds)),
        })
        r.raise_for_status()
        data = r.json()
        return VideoJob(job_id=data["job_id"], status=data["status"])

    def get_status(self, job_id: str) -> VideoJob:
        r = self.client.get(f"/status/{job_id}")
        r.raise_for_status()
        data = r.json()
        return VideoJob(
            job_id=job_id,
            status=data["status"],
            video_url=data.get("video_url"),
            error=data.get("error"),
        )

    def wait_for_completion(self, job_id: str, timeout: int = 900, poll_interval: int = 10) -> VideoJob:
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.get_status(job_id)
            if job.status in ("completed", "failed"):
                return job
            time.sleep(poll_interval)
        raise TimeoutError(f"DVG job {job_id} did not complete within {timeout}s")


class RunwayVideoGenerator:
    """Runway ML Gen-3 Alpha fallback. Set RUNWAY_API_KEY."""

    BASE_URL = "https://api.dev.runwayml.com/v1"

    def __init__(self):
        self.api_key = os.environ["RUNWAY_API_KEY"]
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Runway-Version": "2024-11-06",
            },
            timeout=60,
        )

    def create_video(self, visual_prompt: str, duration_seconds: int, voiceover_text: str = "") -> VideoJob:
        duration = 10 if duration_seconds >= 8 else 5
        r = self.client.post("/text_to_video", json={
            "promptText": visual_prompt[:1000],
            "model": "gen3a_turbo",
            "duration": duration,
            "ratio": "1280:720",
        })
        r.raise_for_status()
        data = r.json()
        return VideoJob(job_id=data["id"], status=data.get("status", "queued"))

    def get_status(self, job_id: str) -> VideoJob:
        r = self.client.get(f"/tasks/{job_id}")
        r.raise_for_status()
        data = r.json()
        status = data.get("status", "queued")
        video_url = None
        if status == "SUCCEEDED":
            output = data.get("output", [])
            video_url = output[0] if output else None
            status = "completed"
        elif status == "FAILED":
            status = "failed"
        else:
            status = "processing"
        return VideoJob(job_id=job_id, status=status, video_url=video_url, error=data.get("failure"))

    def wait_for_completion(self, job_id: str, timeout: int = 600, poll_interval: int = 10) -> VideoJob:
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.get_status(job_id)
            if job.status in ("completed", "failed"):
                return job
            time.sleep(poll_interval)
        raise TimeoutError(f"Runway job {job_id} did not complete within {timeout}s")


class StubVideoGenerator:
    """Testing only — returns nothing real."""

    def create_video(self, visual_prompt: str, duration_seconds: int, voiceover_text: str = "") -> VideoJob:
        print(f"[STUB] {duration_seconds}s video: {visual_prompt[:60]}...")
        return VideoJob(job_id="stub-001", status="completed", video_url=None)

    def get_status(self, job_id: str) -> VideoJob:
        return VideoJob(job_id=job_id, status="completed", video_url=None)

    def wait_for_completion(self, job_id: str, timeout: int = 600, poll_interval: int = 10) -> VideoJob:
        return self.get_status(job_id)


def get_video_generator():
    if os.getenv("DVG_URL"):
        print("[video] Using Dominion Video Generator (self-hosted)")
        return DominionVideoGenerator()
    if os.getenv("RUNWAY_API_KEY"):
        print("[video] Using Runway ML")
        return RunwayVideoGenerator()
    print("[video] WARNING: No video backend configured — using stub")
    return StubVideoGenerator()
