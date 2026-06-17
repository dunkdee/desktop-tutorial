"""
Video generation via Runway ML Gen-3 Alpha.
Sign up at https://runwayml.com to get a RUNWAY_API_KEY.
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


class RunwayVideoGenerator:
    """
    Generates video clips using Runway Gen-3 Alpha Turbo.
    Set RUNWAY_API_KEY in your environment.
    """

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
        # Runway supports 5 or 10 second clips; round to nearest
        duration = 10 if duration_seconds >= 8 else 5

        payload = {
            "promptText": visual_prompt[:1000],
            "model": "gen3a_turbo",
            "duration": duration,
            "ratio": "1280:720",
            "watermark": False,
        }

        r = self.client.post("/image_to_video", json=payload)
        if r.status_code == 422:
            # Fall back to text-only generation
            r = self.client.post("/text_to_video", json=payload)
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
        return VideoJob(
            job_id=job_id,
            status=status,
            video_url=video_url,
            error=data.get("failure", None),
        )

    def wait_for_completion(self, job_id: str, timeout: int = 600, poll_interval: int = 10) -> VideoJob:
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.get_status(job_id)
            if job.status in ("completed", "failed"):
                return job
            time.sleep(poll_interval)
        raise TimeoutError(f"Runway job {job_id} did not complete within {timeout}s")


class StubVideoGenerator:
    """Used when RUNWAY_API_KEY is not set — for local testing only."""

    def create_video(self, visual_prompt: str, duration_seconds: int, voiceover_text: str = "") -> VideoJob:
        print(f"[STUB] Would generate {duration_seconds}s video: {visual_prompt[:80]}...")
        return VideoJob(job_id="stub-001", status="completed", video_url=None)

    def get_status(self, job_id: str) -> VideoJob:
        return VideoJob(job_id=job_id, status="completed", video_url=None)

    def wait_for_completion(self, job_id: str, timeout: int = 600, poll_interval: int = 10) -> VideoJob:
        return self.get_status(job_id)


def get_video_generator():
    if os.getenv("RUNWAY_API_KEY"):
        return RunwayVideoGenerator()
    print("WARNING: RUNWAY_API_KEY not set — using stub. Get a key at runwayml.com")
    return StubVideoGenerator()
