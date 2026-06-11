"""
Higgins video generation integration.

Higgins is the AI video generation backend used by this pipeline.
Set HIGGINS_API_KEY and HIGGINS_API_URL in your environment to connect.
"""
import os
import time
import httpx
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class VideoJob:
    job_id: str
    status: str  # queued | processing | completed | failed
    video_url: Optional[str] = None
    error: Optional[str] = None


class VideoGenerator(ABC):
    @abstractmethod
    def create_video(self, visual_prompt: str, duration_seconds: int, voiceover_text: str = "") -> VideoJob:
        pass

    @abstractmethod
    def get_status(self, job_id: str) -> VideoJob:
        pass

    def wait_for_completion(self, job_id: str, timeout: int = 600, poll_interval: int = 10) -> VideoJob:
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = self.get_status(job_id)
            if job.status in ("completed", "failed"):
                return job
            time.sleep(poll_interval)
        raise TimeoutError(f"Video job {job_id} did not complete within {timeout}s")


class HigginsVideoGenerator(VideoGenerator):
    """
    Higgins AI video generation client.

    Higgins generates cinematic AI video clips from text prompts.
    Each call to create_video submits a job; poll get_status until
    status == 'completed' and video_url is populated.
    """

    def __init__(self):
        self.api_key = os.environ["HIGGINS_API_KEY"]
        self.base_url = os.getenv("HIGGINS_API_URL", "https://api.higgins.ai/v1")
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=30,
        )

    def create_video(self, visual_prompt: str, duration_seconds: int, voiceover_text: str = "") -> VideoJob:
        payload = {
            "prompt": visual_prompt,
            "duration": duration_seconds,
            "aspect_ratio": "16:9",
            "quality": "high",
        }
        if voiceover_text:
            payload["voiceover"] = voiceover_text

        r = self.client.post("/videos", json=payload)
        r.raise_for_status()
        data = r.json()
        return VideoJob(job_id=data["id"], status=data.get("status", "queued"))

    def get_status(self, job_id: str) -> VideoJob:
        r = self.client.get(f"/videos/{job_id}")
        r.raise_for_status()
        data = r.json()
        return VideoJob(
            job_id=job_id,
            status=data["status"],
            video_url=data.get("video_url"),
            error=data.get("error"),
        )


class StubVideoGenerator(VideoGenerator):
    """Local stub for testing without Higgins credentials."""

    def create_video(self, visual_prompt: str, duration_seconds: int, voiceover_text: str = "") -> VideoJob:
        print(f"[STUB] Would generate {duration_seconds}s video: {visual_prompt[:80]}...")
        return VideoJob(job_id="stub-001", status="completed", video_url="/tmp/stub_video.mp4")

    def get_status(self, job_id: str) -> VideoJob:
        return VideoJob(job_id=job_id, status="completed", video_url="/tmp/stub_video.mp4")


def get_video_generator() -> VideoGenerator:
    if os.getenv("HIGGINS_API_KEY"):
        return HigginsVideoGenerator()
    print("HIGGINS_API_KEY not set — using stub video generator")
    return StubVideoGenerator()
