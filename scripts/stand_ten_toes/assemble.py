#!/usr/bin/env python3
"""
Stand Ten Toes — Assembly Script
Concatenates generated clips in order, overlays the audio track,
outputs a single rough-cut MP4.

Usage:
  python assemble.py
  python assemble.py --audio /path/to/stand_ten_toes.mp3
  python assemble.py --no-audio   # concat only, no audio overlay
"""
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent
PROMPTS    = SCRIPT_DIR / "prompts.json"
MANIFEST   = SCRIPT_DIR / "manifest.json"
CLIPS_DIR  = Path("~/dominion_media/stand_ten_toes/raw_clips").expanduser()
OUTPUT_DIR = Path("~/dominion_media/stand_ten_toes/output").expanduser()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def check_ffmpeg():
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode != 0:
        print("ERROR: ffmpeg not found.")
        print("  Install: sudo apt-get install -y ffmpeg")
        sys.exit(1)


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def get_ordered_clips(manifest: dict, segments: list) -> list[Path]:
    """Return clip paths in segment order. Abort if any are missing."""
    clips = []
    missing = []

    for seg in sorted(segments, key=lambda s: s["order"]):
        seg_id = seg["id"]
        run    = manifest.get("runs", {}).get(seg_id, {})

        if run.get("status") != "completed":
            missing.append(f"{seg_id} (status: {run.get('status', 'not started')})")
            continue

        path = Path(run.get("local_path", ""))
        if not path.exists():
            missing.append(f"{seg_id} (file missing: {path})")
            continue

        clips.append(path)

    if missing:
        print(f"\n⚠ Cannot assemble — missing clips:")
        for m in missing:
            print(f"   • {m}")
        print("\nRun generate.py first, then retry.")
        sys.exit(1)

    return clips


def concat_clips(clips: list[Path], output_path: Path) -> Path:
    """Concatenate clips using ffmpeg concat demuxer."""
    list_file = OUTPUT_DIR / "concat_list.txt"
    with open(list_file, "w") as f:
        for clip in clips:
            f.write(f"file '{clip.resolve()}'\n")

    print(f"\n▶ Concatenating {len(clips)} clips...")
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True)
    list_file.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"ERROR: ffmpeg concat failed:\n{result.stderr.decode()[-500:]}")
        sys.exit(1)

    print(f"  ✓ Concatenated → {output_path}")
    return output_path


def overlay_audio(video_path: Path, audio_path: Path, output_path: Path) -> Path:
    """Overlay audio track on video. Audio is trimmed/looped to match video length."""
    print(f"\n▶ Overlaying audio: {audio_path.name}...")

    # Get video duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video_path)],
        capture_output=True
    )
    duration = json.loads(probe.stdout).get("format", {}).get("duration", "0")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", duration,          # trim to video length
        "-shortest",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode != 0:
        print(f"ERROR: audio overlay failed:\n{result.stderr.decode()[-500:]}")
        sys.exit(1)

    print(f"  ✓ Audio overlaid → {output_path}")
    return output_path


def run(audio_override: str = None, no_audio: bool = False):
    check_ffmpeg()

    project   = load_json(PROMPTS)
    manifest  = load_json(MANIFEST) if MANIFEST.exists() else {"runs": {}}
    segments  = project["segments"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n{'='*55}")
    print(f"  Stand Ten Toes — Assembly")
    print(f"  {len(segments)} segments")
    print(f"{'='*55}")

    clips = get_ordered_clips(manifest, segments)
    print(f"  ✓ All {len(clips)} clips found")

    concat_path = OUTPUT_DIR / f"concat_{timestamp}.mp4"
    concat_clips(clips, concat_path)

    if no_audio:
        final = concat_path
        print(f"\n  Skipping audio overlay (--no-audio)")
    else:
        audio_path = Path(audio_override).expanduser() if audio_override \
                     else Path(project.get("audio_track", "")).expanduser()

        if not audio_path.exists():
            print(f"\n⚠ Audio file not found: {audio_path}")
            print(f"  Place your audio at: {audio_path}")
            print(f"  Or run: python assemble.py --audio /path/to/file.mp3")
            print(f"\n  Saving video-only rough cut instead...")
            final = concat_path
        else:
            final = OUTPUT_DIR / f"rough_cut_{timestamp}.mp4"
            overlay_audio(concat_path, audio_path, final)
            concat_path.unlink(missing_ok=True)

    size_mb = final.stat().st_size / 1_000_000
    print(f"\n{'='*55}")
    print(f"  ✓ Rough cut complete")
    print(f"  Output: {final}")
    print(f"  Size: {size_mb:.1f}MB")
    print(f"{'='*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Assemble Stand Ten Toes rough cut")
    parser.add_argument("--audio", help="Path to audio track (overrides prompts.json)")
    parser.add_argument("--no-audio", action="store_true", help="Skip audio overlay")
    args = parser.parse_args()
    run(audio_override=args.audio, no_audio=args.no_audio)
