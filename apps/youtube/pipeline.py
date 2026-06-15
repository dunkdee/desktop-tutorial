"""Full movie generation pipeline: script → video clips → assemble → upload."""
import json
import os
import re
import sys
import tempfile
import httpx
from pathlib import Path
from dataclasses import dataclass, field

# Use Gemini script generator if SCRIPT_ENGINE=gemini, else default to Claude Fable 5
if os.environ.get("SCRIPT_ENGINE", "").lower() == "gemini":
    from gemini_script import (
        generate_script,
        generate_scene_visuals,
        generate_voiceover,
        generate_title_and_description,
    )
else:
    from script_generator import (
        generate_script,
        generate_scene_visuals,
        generate_voiceover,
        generate_title_and_description,
    )

from video_generator import get_video_generator, VideoJob
from youtube_uploader import upload_video


@dataclass
class PipelineResult:
    title: str
    script: str
    scene_count: int
    youtube_video_id: str = ""
    youtube_url: str = ""
    drive_url: str = ""
    errors: list[str] = field(default_factory=list)
    status: str = "pending"


def _parse_scene_breakdown(script_text: str) -> list[dict]:
    """Extract the JSON scene breakdown block from the generated script."""
    match = re.search(r"\[.*?\]", script_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return [
        {
            "scene_number": 1,
            "location": "Various",
            "description": script_text[:500],
            "duration_seconds": 60,
        }
    ]


def _download_video(url: str, dest_path: str):
    with httpx.stream("GET", url, timeout=120) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=65536):
                f.write(chunk)


def _concatenate_clips(clip_paths: list[str], output_path: str):
    """Concatenate video clips using ffmpeg."""
    list_file = output_path + ".txt"
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")
    ret = os.system(f"ffmpeg -y -f concat -safe 0 -i '{list_file}' -c copy '{output_path}' 2>/dev/null")
    os.unlink(list_file)
    if ret != 0:
        raise RuntimeError("ffmpeg concat failed")


def _backup_to_drive(video_path: str) -> str:
    """Upload finished video to Google Drive. Returns webViewLink or empty string."""
    if not os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON"):
        return ""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "gemini"))
        from drive_upload import upload_file
        result = upload_file(video_path, "video/mp4")
        return result.get("webViewLink", "")
    except Exception as e:
        print(f"[pipeline] Drive backup skipped: {e}")
        return ""


def run_pipeline(
    prompt: str,
    title: str,
    description: str = "",
    privacy: str = "private",
    upload: bool = True,
) -> PipelineResult:
    result = PipelineResult(title=title, script="", scene_count=0, status="running")
    generator = get_video_generator()

    # Step 1: Generate script
    engine = os.environ.get("SCRIPT_ENGINE", "claude")
    print(f"[pipeline] Generating script for '{title}' using {engine}...")
    result.script = generate_script(prompt, title)
    scenes = _parse_scene_breakdown(result.script)
    result.scene_count = len(scenes)
    print(f"[pipeline] Script done — {result.scene_count} scenes")

    # Step 2: Generate voiceover text
    voiceover = generate_voiceover(result.script)

    # Step 3: Generate each scene video via Higgins
    clip_paths: list[str] = []
    jobs: list[VideoJob] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for scene in scenes:
            visual_prompt = generate_scene_visuals(scene.get("description", ""))
            duration = int(scene.get("duration_seconds", 30))
            print(f"[pipeline] Submitting scene {scene.get('scene_number', '?')} to Higgins...")
            job = generator.create_video(visual_prompt, duration, voiceover)
            jobs.append(job)

        for i, job in enumerate(jobs):
            print(f"[pipeline] Waiting for clip {i+1}/{len(jobs)}...")
            try:
                completed = generator.wait_for_completion(job.job_id)
                if completed.status == "failed":
                    result.errors.append(f"Scene {i+1} failed: {completed.error}")
                    continue
                clip_path = os.path.join(tmpdir, f"clip_{i:03d}.mp4")
                if completed.video_url and not completed.video_url.startswith("/tmp"):
                    _download_video(completed.video_url, clip_path)
                else:
                    clip_path = completed.video_url
                clip_paths.append(clip_path)
            except Exception as e:
                result.errors.append(f"Scene {i+1} error: {e}")

        if not clip_paths:
            result.status = "failed"
            result.errors.append("No video clips generated")
            return result

        # Step 4: Concatenate clips
        final_video = os.path.join(tmpdir, "final_movie.mp4")
        if len(clip_paths) == 1:
            final_video = clip_paths[0]
        else:
            print("[pipeline] Concatenating clips...")
            _concatenate_clips(clip_paths, final_video)

        # Step 5: Generate YouTube metadata
        meta = generate_title_and_description(result.script, title)
        yt_title = meta.get("title", title)
        yt_description = meta.get("description", description or prompt)
        yt_tags = meta.get("tags", [])

        # Step 6: Upload to YouTube
        if upload:
            print(f"[pipeline] Uploading '{yt_title}' to YouTube ({privacy})...")
            yt_response = upload_video(final_video, yt_title, yt_description, yt_tags, privacy=privacy)
            result.youtube_video_id = yt_response.get("id", "")
            result.youtube_url = f"https://www.youtube.com/watch?v={result.youtube_video_id}"
            print(f"[pipeline] Uploaded: {result.youtube_url}")

            # Step 7: Backup to Google Drive
            print("[pipeline] Backing up to Google Drive...")
            result.drive_url = _backup_to_drive(final_video)
            if result.drive_url:
                print(f"[pipeline] Drive backup: {result.drive_url}")
        else:
            print("[pipeline] Skipping upload (upload=False)")

    result.status = "completed" if not result.errors else "completed_with_errors"
    return result
