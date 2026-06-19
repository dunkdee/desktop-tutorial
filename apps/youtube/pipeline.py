"""Full movie pipeline: script → scene breakdown → Runway video clips → concat → YouTube upload."""
import os
import subprocess
import tempfile
import httpx
from dataclasses import dataclass, field

from script_generator import (
    generate_script,
    generate_scene_breakdown,
    generate_scene_visuals,
    generate_voiceover,
    generate_title_and_description,
)
from video_generator import get_video_generator
from youtube_uploader import upload_video


@dataclass
class PipelineResult:
    title: str
    script: str
    scene_count: int
    youtube_video_id: str = ""
    youtube_url: str = ""
    errors: list[str] = field(default_factory=list)
    status: str = "pending"


def _download_video(url: str, dest_path: str):
    with httpx.stream("GET", url, follow_redirects=True, timeout=180) as r:
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in r.iter_bytes(chunk_size=65536):
                f.write(chunk)


def _concat_clips(clip_paths: list[str], output_path: str):
    list_file = output_path + ".txt"
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p}'\n")
    proc = subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path],
        capture_output=True,
    )
    os.unlink(list_file)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr.decode()[-500:]}")


def run_pipeline(
    prompt: str,
    title: str,
    description: str = "",
    privacy: str = "private",
    upload: bool = True,
) -> PipelineResult:
    result = PipelineResult(title=title, script="", scene_count=0, status="running")
    generator = get_video_generator()

    # 1. Generate script
    print(f"[pipeline] Writing script for '{title}'...")
    result.script = generate_script(prompt, title)
    print(f"[pipeline] Script done ({len(result.script)} chars)")

    # 2. Break into scenes (separate Claude call — returns clean JSON)
    print("[pipeline] Breaking script into scenes...")
    scenes = generate_scene_breakdown(result.script)
    result.scene_count = len(scenes)
    print(f"[pipeline] {result.scene_count} scenes")

    # 3. Voiceover
    voiceover = generate_voiceover(result.script)

    with tempfile.TemporaryDirectory() as tmpdir:
        # 4. Submit all scenes to Runway in sequence
        clip_paths: list[str] = []
        for i, scene in enumerate(scenes):
            scene_num = scene.get("scene_number", i + 1)
            print(f"[pipeline] Generating scene {scene_num}/{result.scene_count}...")
            try:
                visual_prompt = generate_scene_visuals(scene.get("description", ""))
                duration = max(5, min(30, int(scene.get("duration_seconds", 10))))
                job = generator.create_video(visual_prompt, duration, voiceover)
                completed = generator.wait_for_completion(job.job_id)

                if completed.status == "failed":
                    result.errors.append(f"Scene {scene_num} failed: {completed.error}")
                    continue

                if not completed.video_url:
                    result.errors.append(f"Scene {scene_num}: no video URL returned (stub mode?)")
                    continue

                clip_path = os.path.join(tmpdir, f"clip_{i:03d}.mp4")
                _download_video(completed.video_url, clip_path)
                clip_paths.append(clip_path)
                print(f"[pipeline] Scene {scene_num} done → {clip_path}")

            except Exception as e:
                result.errors.append(f"Scene {scene_num} error: {e}")

        if not clip_paths:
            result.status = "failed"
            result.errors.append("No video clips were generated successfully")
            return result

        # 5. Concatenate
        if len(clip_paths) == 1:
            final_video = clip_paths[0]
        else:
            final_video = os.path.join(tmpdir, "final_movie.mp4")
            print(f"[pipeline] Concatenating {len(clip_paths)} clips...")
            _concat_clips(clip_paths, final_video)

        # 6. YouTube metadata + upload
        meta = generate_title_and_description(result.script, title)
        yt_title = meta.get("title", title)
        yt_description = meta.get("description", description or prompt)
        yt_tags = meta.get("tags", [])

        if upload:
            print(f"[pipeline] Uploading to YouTube as '{yt_title}' ({privacy})...")
            yt_response = upload_video(final_video, yt_title, yt_description, yt_tags, privacy=privacy)
            result.youtube_video_id = yt_response.get("id", "")
            result.youtube_url = f"https://www.youtube.com/watch?v={result.youtube_video_id}"
            print(f"[pipeline] Done: {result.youtube_url}")
        else:
            print("[pipeline] Skipping YouTube upload (upload=False)")

    result.status = "completed" if not result.errors else "completed_with_errors"
    return result
