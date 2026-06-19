"""
Dominion Video Generator
Open-source text-to-video using CogVideoX-2b.
Runs free on any GPU (14GB+ VRAM) or CPU (slow but works).
Model auto-downloads on first run from HuggingFace — no account needed.
"""
import os
import time
import torch
import imageio
import numpy as np
from pathlib import Path
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video

MODEL_ID = os.getenv("DVG_MODEL", "THUDM/CogVideoX-2b")
OUTPUT_DIR = Path(os.getenv("DVG_OUTPUT_DIR", "/tmp/dominion-vg"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_pipe = None


def _load_pipeline():
    global _pipe
    if _pipe is not None:
        return _pipe

    print(f"[DVG] Loading {MODEL_ID}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    _pipe = CogVideoXPipeline.from_pretrained(
        MODEL_ID,
        torch_dtype=dtype,
    )

    if device == "cuda":
        _pipe.enable_model_cpu_offload()
        _pipe.vae.enable_tiling()
    else:
        print("[DVG] No GPU detected — running on CPU (slower)")
        _pipe = _pipe.to(device)

    print(f"[DVG] Model ready on {device}")
    return _pipe


def generate_video(prompt: str, duration_seconds: int = 6, job_id: str = "") -> str:
    """
    Generate a video from a text prompt.
    Returns the path to the output .mp4 file.
    CogVideoX generates 6-second clips at 8fps by default.
    """
    pipe = _load_pipeline()

    # CogVideoX uses num_frames — 49 frames = ~6s at 8fps
    num_frames = min(49, max(17, int(duration_seconds * 8)))

    print(f"[DVG] Generating: {prompt[:80]}...")
    start = time.time()

    result = pipe(
        prompt=prompt,
        num_videos_per_prompt=1,
        num_inference_steps=50,
        num_frames=num_frames,
        guidance_scale=6.0,
        generator=torch.Generator().manual_seed(42),
    )

    frames = result.frames[0]
    out_path = str(OUTPUT_DIR / f"{job_id or int(time.time())}.mp4")
    export_to_video(frames, out_path, fps=8)

    elapsed = time.time() - start
    print(f"[DVG] Done in {elapsed:.1f}s → {out_path}")
    return out_path
