"""
NVIDIA Cosmos — elite video generation via NVIDIA NIM API.
Free credits at build.nvidia.com — sign up, grab API key, done.
No GPU needed on your side. NVIDIA runs it on their H100s.
"""
import os
import time
import base64
import httpx
from pathlib import Path

NIM_API_KEY = os.environ["NVIDIA_NIM_API_KEY"]
NIM_BASE_URL = "https://ai.api.nvidia.com/v1"

# NVIDIA Cosmos models — pick based on use case
MODELS = {
    "fast":     "nvidia/cosmos-1-0-diffusion-7b-text2world",   # 7B — fast, great quality
    "elite":    "nvidia/cosmos-1-0-diffusion-14b-text2world",  # 14B — cinematic, best quality
    "predict":  "nvidia/cosmos-1-0-predict-world",             # future-frame prediction
}


def generate(
    prompt: str,
    duration_seconds: int = 5,
    width: int = 1280,
    height: int = 720,
    quality: str = "elite",
    output_path: str = None,
) -> str:
    """
    Generate a video clip via NVIDIA Cosmos NIM API.
    Returns path to saved .mp4 file.
    """
    model = MODELS.get(quality, MODELS["elite"])
    if not output_path:
        output_path = f"/tmp/cosmos_{int(time.time())}.mp4"

    print(f"[Cosmos] Model: {model}")
    print(f"[Cosmos] Generating: {prompt[:80]}...")

    headers = {
        "Authorization": f"Bearer {NIM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "num_frames": min(121, max(25, duration_seconds * 24)),
        "fps": 24,
        "width": width,
        "height": height,
        "guidance_scale": 7.0,
        "num_inference_steps": 35,
    }

    t0 = time.time()
    with httpx.Client(timeout=300) as client:
        r = client.post(f"{NIM_BASE_URL}/cosmos/generation", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    # NIM returns base64-encoded video or a URL
    if "video_b64" in data:
        video_bytes = base64.b64decode(data["video_b64"])
        Path(output_path).write_bytes(video_bytes)
    elif "video_url" in data:
        vid = httpx.get(data["video_url"], follow_redirects=True, timeout=120)
        Path(output_path).write_bytes(vid.content)
    else:
        raise RuntimeError(f"Unexpected Cosmos response: {list(data.keys())}")

    print(f"[Cosmos] Done in {time.time() - t0:.1f}s → {output_path}")
    return output_path


def list_models() -> list[str]:
    headers = {"Authorization": f"Bearer {NIM_API_KEY}"}
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{NIM_BASE_URL}/models", headers=headers)
        r.raise_for_status()
    return [m["id"] for m in r.json().get("data", []) if "cosmos" in m["id"].lower()]
