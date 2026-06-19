"""
HunyuanVideo — Tencent's elite open-source text-to-video model.
Best-in-class open source quality. Runs on 24GB+ GPU with fp8 quant.
"""
import os
import time
import torch
from pathlib import Path
from diffusers import HunyuanVideoPipeline, HunyuanVideoTransformer3DModel
from diffusers.utils import export_to_video

MODEL_ID = "hunyuanvideo-community/HunyuanVideo"
_pipe = None


def _load():
    global _pipe
    if _pipe is not None:
        return _pipe

    print("[DVG] Loading HunyuanVideo...")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    if device != "cuda":
        raise RuntimeError(
            "HunyuanVideo requires a CUDA GPU (24GB+ VRAM). "
            "Provision a GPU node to use Dominion Video Generator."
        )

    vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"[DVG] GPU: {torch.cuda.get_device_name(0)} ({vram_gb:.0f}GB VRAM)")

    # fp8 quantization for 24GB cards, fp16 for 40GB+
    use_fp8 = vram_gb < 38
    dtype = torch.float16

    if use_fp8:
        print("[DVG] Using fp8 quantization for 24GB GPU...")
        transformer = HunyuanVideoTransformer3DModel.from_pretrained(
            MODEL_ID,
            subfolder="transformer",
            torch_dtype=torch.float8_e4m3fn,
        )
        _pipe = HunyuanVideoPipeline.from_pretrained(
            MODEL_ID,
            transformer=transformer,
            torch_dtype=dtype,
        )
    else:
        print("[DVG] Loading full fp16 model...")
        _pipe = HunyuanVideoPipeline.from_pretrained(MODEL_ID, torch_dtype=dtype)

    _pipe.vae.enable_tiling()
    _pipe.enable_model_cpu_offload()
    print("[DVG] HunyuanVideo ready.")
    return _pipe


def generate(
    prompt: str,
    duration_seconds: int = 5,
    width: int = 1280,
    height: int = 720,
    fps: int = 24,
    guidance_scale: float = 6.0,
    seed: int = -1,
    output_path: str = None,
) -> str:
    pipe = _load()

    num_frames = duration_seconds * fps
    # HunyuanVideo requires num_frames = 4k+1
    num_frames = max(((num_frames - 1) // 4) * 4 + 1, 9)

    generator = torch.Generator("cuda")
    if seed >= 0:
        generator.manual_seed(seed)
    else:
        generator.manual_seed(int(time.time()) % 2**32)

    print(f"[DVG] Generating {width}x{height} @ {fps}fps, {num_frames} frames...")
    t0 = time.time()

    result = pipe(
        prompt=prompt,
        height=height,
        width=width,
        num_frames=num_frames,
        num_inference_steps=50,
        guidance_scale=guidance_scale,
        generator=generator,
    )

    frames = result.frames[0]
    if not output_path:
        output_path = f"/tmp/dvg_{int(time.time())}.mp4"

    export_to_video(frames, output_path, fps=fps)
    print(f"[DVG] Done in {time.time() - t0:.1f}s → {output_path}")
    return output_path
