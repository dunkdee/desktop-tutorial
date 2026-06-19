FROM pytorch/pytorch:2.4.0-cuda12.4-cudnn9-runtime

RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DVG_OUTPUT_DIR=/data/videos
ENV PYTHONUNBUFFERED=1

VOLUME ["/data/videos"]

EXPOSE 8002
