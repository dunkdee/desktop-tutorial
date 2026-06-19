#!/usr/bin/env python3
"""
Stand Ten Toes — Video Clip Generator
Uses fal.ai → Kling AI v1.6 (official API, pay-per-use, ~$2.80 for all 8 clips)
Idempotent: re-running skips already-completed clips.

Usage:
  FAL_KEY=your_key python generate.py
  FAL_KEY=your_key python generate.py --dry-run   # show what would run, no API calls
  FAL_KEY=your_key python generate.py --segment intro  # run one segment only
"""
import os
import sys
import json
import time
import httpx
import argparse
from pathlib import Path
from datetime import datetime, timezone

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
PROMPTS     = SCRIPT_DIR / "prompts.json"
MANIFEST    = SCRIPT_DIR / "manifest.json"
CLIPS_DIR   = Path("~/dominion_media/stand_ten_toes/raw_clips").expanduser()
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

# ── fal.ai Kling endpoint ───────────────────────────────────────────────────
# Official API — no TOS violation, pay-per-use
# Pricing: ~$0.28 per 5s clip, ~$0.56 per 10s clip (as of 2025)
# Free $5 credit on signup at fal.ai — covers all 8 clips
FAL_QUEUE_URL = "https://queue.fal.run"
FAL_KEY = os.environ.get("FAL_KEY", "")


def load_prompts() -> dict:
    with open(PROMPTS) as f:
        return json.load(f)


def load_manifest() -> dict:
    if MANIFEST.exists():
        with open(MANIFEST) as f:
            return json.load(f)
    return {"runs": {}, "cost_usd": 0.0}


def save_manifest(manifest: dict):
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=2)


def estimate_cost(duration: int) -> float:
    return round(duration * 0.056, 3)  # ~$0.056/second for Kling Standard


def submit_clip(segment: dict, dry_run: bool = False) -> dict:
    """Submit one segment to fal.ai Kling. Returns job record."""
    seg_id   = segment["id"]
    prompt   = segment["prompt"]
    duration = str(segment["duration"])
    cost_est = estimate_cost(int(duration))

    if dry_run:
        print(f"  [DRY RUN] {seg_id}: would submit {duration}s clip (~${cost_est})")
        return {"status": "dry_run", "cost_usd": cost_est}

    headers = {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "16:9",
        "negative_prompt": "blurry, low quality, watermark, text overlay, distorted",
        "cfg_scale": 0.5,
    }

    project = load_prompts()
    model = project.get("model", "fal-ai/kling-video/v1.6/standard/text-to-video")

    print(f"  → Submitting {seg_id} ({duration}s, est. ${cost_est})...")
    with httpx.Client(timeout=30) as client:
        r = client.post(
            f"{FAL_QUEUE_URL}/{model}",
            headers=headers,
            json=payload,
        )
        r.raise_for_status()
        result = r.json()

    request_id = result.get("request_id")
    return {
        "request_id": request_id,
        "status": "submitted",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "cost_usd": cost_est,
        "prompt": prompt,
        "duration": int(duration),
    }


def poll_clip(seg_id: str, request_id: str, model: str, timeout: int = 600) -> dict:
    """Poll fal.ai queue until clip is ready. Returns updated job record."""
    headers = {"Authorization": f"Key {FAL_KEY}"}
    status_url = f"{FAL_QUEUE_URL}/{model}/requests/{request_id}/status"
    result_url = f"{FAL_QUEUE_URL}/{model}/requests/{request_id}"

    deadline = time.time() + timeout
    print(f"  ⏳ Polling {seg_id} (request {request_id[:8]}...)...")

    while time.time() < deadline:
        with httpx.Client(timeout=30) as client:
            r = client.get(status_url, headers=headers)
            r.raise_for_status()
            status_data = r.json()

        status = status_data.get("status", "")
        if status == "COMPLETED":
            with httpx.Client(timeout=30) as client:
                r = client.get(result_url, headers=headers)
                r.raise_for_status()
                result = r.json()
            video_url = result.get("video", {}).get("url") or result.get("url")
            return {"status": "completed", "video_url": video_url}
        elif status in ("FAILED", "CANCELLED"):
            error = status_data.get("error", "unknown error")
            return {"status": "failed", "error": error}

        print(f"     {seg_id}: {status} — waiting 15s...")
        time.sleep(15)

    return {"status": "timeout", "error": f"Exceeded {timeout}s"}


def download_clip(seg_id: str, video_url: str) -> str:
    """Download generated clip to raw_clips/. Returns local path."""
    out_path = CLIPS_DIR / f"{seg_id}.mp4"
    print(f"  ⬇ Downloading {seg_id} → {out_path}")
    with httpx.stream("GET", video_url, follow_redirects=True, timeout=180) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_bytes(65536):
                f.write(chunk)
    size_mb = out_path.stat().st_size / 1_000_000
    print(f"  ✓ {seg_id} saved ({size_mb:.1f}MB)")
    return str(out_path)


def validate_prompts(segments: list) -> bool:
    """Check all prompts are filled in."""
    missing = [s["id"] for s in segments if "PASTE_PROMPT" in s.get("prompt", "")]
    if missing:
        print(f"\n⚠ Fill in prompts.json first. Missing: {missing}")
        return False
    return True


def run(target_segment: str = None, dry_run: bool = False):
    if not FAL_KEY and not dry_run:
        print("ERROR: Set FAL_KEY environment variable.")
        print("  Get free $5 credits at: https://fal.ai")
        sys.exit(1)

    project  = load_prompts()
    manifest = load_manifest()
    segments = sorted(project["segments"], key=lambda s: s["order"])
    model    = project.get("model", "fal-ai/kling-video/v1.6/standard/text-to-video")

    if target_segment:
        segments = [s for s in segments if s["id"] == target_segment]
        if not segments:
            print(f"ERROR: segment '{target_segment}' not found in prompts.json")
            sys.exit(1)

    if not validate_prompts(segments):
        sys.exit(1)

    print(f"\n{'='*55}")
    print(f"  Stand Ten Toes — Video Generation")
    print(f"  {len(segments)} segment(s) | Model: Kling v1.6 via fal.ai")
    total_cost = sum(estimate_cost(s["duration"]) for s in segments)
    print(f"  Estimated cost: ${total_cost:.2f}")
    print(f"  Dry run: {dry_run}")
    print(f"{'='*55}\n")

    # Phase 1: submit all jobs
    jobs = {}
    for seg in segments:
        seg_id = seg["id"]
        run_rec = manifest["runs"].get(seg_id, {})

        if run_rec.get("status") == "completed" and Path(run_rec.get("local_path", "")).exists():
            print(f"  ✓ {seg_id}: already done — skipping")
            continue

        job = submit_clip(seg, dry_run=dry_run)
        jobs[seg_id] = job
        manifest["runs"][seg_id] = {**run_rec, **job, "segment": seg_id}
        save_manifest(manifest)
        time.sleep(1)  # avoid rate limiting

    if dry_run:
        print("\nDry run complete. No API calls made.")
        return

    # Phase 2: poll + download
    for seg_id, job in jobs.items():
        if job.get("status") != "submitted":
            continue

        request_id = job["request_id"]
        poll_result = poll_clip(seg_id, request_id, model)
        manifest["runs"][seg_id].update(poll_result)

        if poll_result["status"] == "completed":
            local_path = download_clip(seg_id, poll_result["video_url"])
            manifest["runs"][seg_id]["local_path"] = local_path
            manifest["cost_usd"] = round(manifest.get("cost_usd", 0) + job["cost_usd"], 3)
        else:
            print(f"  ✗ {seg_id} FAILED: {poll_result.get('error')}")

        save_manifest(manifest)

    # Summary
    completed = [s for s, r in manifest["runs"].items() if r.get("status") == "completed"]
    failed    = [s for s, r in manifest["runs"].items() if r.get("status") == "failed"]
    print(f"\n{'='*55}")
    print(f"  Done. Completed: {len(completed)} | Failed: {len(failed)}")
    print(f"  Total spent: ${manifest['cost_usd']:.3f}")
    print(f"  Manifest: {MANIFEST}")
    print(f"  Clips: {CLIPS_DIR}")
    if failed:
        print(f"  ⚠ Failed segments: {failed} — re-run to retry")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Stand Ten Toes video clips")
    parser.add_argument("--segment", help="Run a single segment by id")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without API calls")
    args = parser.parse_args()
    run(target_segment=args.segment, dry_run=args.dry_run)
