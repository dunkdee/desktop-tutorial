"""
Dominion Video Generator — GPU Worker
Runs separately from the API so the GPU process is isolated.
Pulls jobs from Redis, generates video, posts result back.
"""
import os
import json
import time
import signal
import traceback
import redis
from pathlib import Path
from models.hunyuan import generate
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
    print("[worker] Shutdown signal received")
    _running = False


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


def process_job(job: dict):
    job_id = job["job_id"]
    print(f"[worker] Processing job {job_id}: {job['prompt'][:60]}...")

    r.hset(JOBS_KEY, job_id, json.dumps({**job, "status": "processing"}))

    try:
        raw_path = str(OUTPUT_DIR / f"{job_id}_raw.mp4")
        final_path = str(OUTPUT_DIR / f"{job_id}.mp4")

        generate(
            prompt=job["prompt"],
            duration_seconds=job.get("duration_seconds", 5),
            width=job.get("width", 1280),
            height=job.get("height", 720),
            fps=24,
            guidance_scale=job.get("guidance_scale", 6.0),
            seed=job.get("seed", -1),
            output_path=raw_path,
        )

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
            "path": final_path,
        }))
        print(f"[worker] Job {job_id} complete → {video_url}")

    except Exception as e:
        err = traceback.format_exc()
        print(f"[worker] Job {job_id} FAILED:\n{err}")
        r.hset(JOBS_KEY, job_id, json.dumps({
            **job,
            "status": "failed",
            "error": str(e),
        }))


def run():
    print("[worker] Dominion Video Generator worker online.")
    print(f"[worker] Redis: {REDIS_URL} | Output: {OUTPUT_DIR}")

    while _running:
        try:
            item = r.blpop(QUEUE_KEY, timeout=5)
            if item:
                _, raw = item
                job = json.loads(raw)
                process_job(job)
        except redis.exceptions.ConnectionError:
            print("[worker] Redis connection lost, retrying in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"[worker] Unexpected error: {e}")
            time.sleep(2)

    print("[worker] Shutdown complete.")


if __name__ == "__main__":
    run()
