FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    libatlas-base-dev \
    ffmpeg \
    libsndfile1 \
    build-essential \
    gcc \
    g++ \
    cmake \
    ninja-build \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Kreuzberg dependencies
RUN pip install --no-cache-dir \
    kreuzberg \
    paddlepaddle \
    onnxruntime

# Install optional Vietnamese TTS provider
RUN pip install --no-cache-dir vieneu \
    --extra-index-url https://pnnbao97.github.io/llama-cpp-python-v0.3.16/cpu/

# Copy AI pipeline code
COPY . .

# Create directories for weights and cache
RUN mkdir -p /weights /app/tts/voices

# Expose port
EXPOSE 8001

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV YOLO_WEIGHTS_PATH=/weights/best.pt

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD python -c "print('AI Pipeline OK')"

# Run the pipeline
CMD ["python", "pipeline.py"]
