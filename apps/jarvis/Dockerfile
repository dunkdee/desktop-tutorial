FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir redis qdrant-client httpx pydantic
COPY . .
CMD ["python","worker.py"]