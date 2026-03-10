FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN ln -s \
$(find /usr/local/lib -name "libonnxruntime.so.*" | head -n1) \
/usr/lib/libonnxruntime.so

COPY . .

