"""
Post-processing pipeline for Dominion Video Generator.
Applies cinematic color grading, frame interpolation, and upscaling.
"""
import os
import subprocess
import tempfile
from pathlib import Path


def _ffmpeg(args: list, check=True) -> subprocess.CompletedProcess:
    cmd = ["ffmpeg", "-y"] + args
    result = subprocess.run(cmd, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr.decode()[-800:]}")
    return result


def color_grade(input_path: str, output_path: str, preset: str = "cinematic") -> str:
    """
    Apply cinematic color grading via ffmpeg curves.
    preset: cinematic | noir | golden_hour | cold
    """
    presets = {
        "cinematic": (
            "curves=r='0/0 0.2/0.18 0.5/0.48 0.8/0.82 1/1':"
            "g='0/0 0.2/0.19 0.5/0.5 0.8/0.81 1/1':"
            "b='0/0 0.2/0.22 0.5/0.52 0.8/0.83 1/1',"
            "eq=contrast=1.05:saturation=1.1:brightness=-0.02,"
            "unsharp=5:5:0.5"
        ),
        "noir": (
            "hue=s=0.2,"
            "curves=all='0/0 0.3/0.2 0.7/0.8 1/1',"
            "eq=contrast=1.3:brightness=-0.05"
        ),
        "golden_hour": (
            "curves=r='0/0 0.5/0.58 1/1':b='0/0 0.5/0.42 1/0.9',"
            "eq=saturation=1.3:contrast=1.05"
        ),
        "cold": (
            "curves=b='0/0.05 0.5/0.55 1/1':r='0/0 0.5/0.45 1/0.95',"
            "eq=saturation=0.85:contrast=1.1"
        ),
    }
    grade = presets.get(preset, presets["cinematic"])
    _ffmpeg(["-i", input_path, "-vf", grade, "-c:v", "libx264", "-crf", "17", "-preset", "slow", output_path])
    return output_path


def interpolate_frames(input_path: str, output_path: str, target_fps: int = 60) -> str:
    """Boost frame rate using motion interpolation (MINTERPOLATE)."""
    _ffmpeg([
        "-i", input_path,
        "-vf", f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
        "-c:v", "libx264", "-crf", "17", "-preset", "slow",
        output_path
    ])
    return output_path


def upscale(input_path: str, output_path: str, target_width: int = 1920, target_height: int = 1080) -> str:
    """Upscale video using Lanczos with sharpening."""
    _ffmpeg([
        "-i", input_path,
        "-vf", f"scale={target_width}:{target_height}:flags=lanczos,unsharp=5:5:0.8",
        "-c:v", "libx264", "-crf", "16", "-preset", "slow",
        output_path
    ])
    return output_path


def full_pipeline(
    input_path: str,
    output_path: str,
    grade_preset: str = "cinematic",
    target_fps: int = 60,
    upscale_1080p: bool = True,
) -> str:
    """
    Run the full post-processing chain:
    raw clip → color grade → frame interpolation → 1080p upscale
    """
    tmp_dir = tempfile.mkdtemp()
    stage1 = os.path.join(tmp_dir, "graded.mp4")
    stage2 = os.path.join(tmp_dir, "interpolated.mp4")

    print("[DVG:post] Color grading...")
    color_grade(input_path, stage1, grade_preset)

    print(f"[DVG:post] Interpolating to {target_fps}fps...")
    interpolate_frames(stage1, stage2, target_fps)

    if upscale_1080p:
        print("[DVG:post] Upscaling to 1080p...")
        upscale(stage2, output_path)
    else:
        import shutil
        shutil.copy(stage2, output_path)

    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"[DVG:post] Complete → {output_path}")
    return output_path
