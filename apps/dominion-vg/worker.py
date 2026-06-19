"""
Dominion Video Generator — Worker
Pulls jobs from Redis, generates via NVIDIA Cosmos NIM, post-processes, saves.
No GPU required on your server — NVIDIA runs it on their H100s.
"""
import os
import json
import time
import signal
import traceback
import redis
from pathlib import Path
from models.cosmos import generate
from postprocess import full_pipeline

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/2")
QUEUE_KEY = "dvg:queue"
JOBS_KEY = "dvg:jobs"
OUTPUT_DIR = Path(os.getenv("DVG_OUTPUT_DIR", "/data/videos"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_URL = os.getenv("DVG_PUBLIC_URL", "http://localhost:8002")

r = redis.from_url(REDIS_URL, decode_responses=True)
_running = True


def _signal_handler(sig, frame):
    global _running
    print("[worker] Shutting down...")
    _running = False


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def process_job(job: dict):
    job_id = job["job_id"]
    print(f"[worker] Job {job_id}: {job['prompt'][:60]}...")
    r.hset(JOBS_KEY, job_id, json.dumps({**job, "status": "processing"}))

    try:
        raw_path = str(OUTPUT_DIR / f"{job_id}_raw.mp4")
        final_path = str(OUTPUT_DIR / f"{job_id}.mp4")

        # Generate via NVIDIA Cosmos
        generate(
            prompt=job["prompt"],
            duration_seconds=job.get("duration_seconds", 5),
            width=job.get("width", 1280),
            height=job.get("height", 720),
            quality=job.get("quality", "elite"),
            output_path=raw_path,
        )

        # Post-process: color grade → 60fps → 1080p
        full_pipeline(
            input_path=raw_path,
            output_path=final_path,
            grade_preset=job.get("grade_preset", "cinematic"),
            target_fps=60,
            upscale_1080p=job.get("upscale", True),
        )

        Path(raw_path).unlink(missing_ok=True)
        video_url = f"{PUBLIC_URL}/videos/{job_id}.mp4"

        r.hset(JOBS_KEY, job_id, json.dumps({
            **job,
            "status": "completed",
            "video_url": video_url,
        }))
        print(f"[worker] Done → {video_url}")

    except Exception as e:
        print(f"[worker] FAILED: {traceback.format_exc()}")
        r.hset(JOBS_KEY, job_id, json.dumps({
            **job,
            "status": "failed",
            "error": str(e),
        }))


def run():
    print("[worker] Dominion Video Generator worker online.")
    print(f"[worker] Model: NVIDIA Cosmos via NIM API")

    while _running:
        try:
            item = r.blpop(QUEUE_KEY, timeout=5)
            if item:
                _, raw = item
                process_job(json.loads(raw))
        except redis.exceptions.ConnectionError:
            print("[worker] Redis disconnected, retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"[worker] Error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    run()
