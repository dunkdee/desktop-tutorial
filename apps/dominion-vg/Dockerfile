FROM pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime

RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Pre-download model at build time so first request is instant
ARG PRELOAD_MODEL=THUDM/CogVideoX-2b
RUN python -c "from diffusers import CogVideoXPipeline; CogVideoXPipeline.from_pretrained('${PRELOAD_MODEL}', torch_dtype=__import__('torch').float16)" || true

ENV DVG_OUTPUT_DIR=/data/videos
VOLUME ["/data/videos"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
