FROM python:3.12-slim

WORKDIR /app

# System deps for OpenCV + InsightFace (g++ needed to compile insightface cython ext)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download InsightFace buffalo_l model (~1.2GB)
# This bakes the model into the image so containers start fast
RUN python -c "import insightface; app = insightface.app.FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider']); app.prepare(ctx_id=-1)"

COPY . .

# Pre-download MiniFASNet anti-spoofing ONNX models
RUN python anti_spoof/download_models.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
