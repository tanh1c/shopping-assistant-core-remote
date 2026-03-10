# Agentic OCR

A high-performance OCR pipeline built on [Kreuzberg](https://kreuzberg-dev.github.io/kreuzberg/) with PaddleOCR backend, designed for real-time price tag extraction in a YOLO → OCR → LLM architecture.

---

## Architecture

```
Camera → YOLO (detect price tags) → OCR Queue → LLM (extract content)
```

- **YOLO**: Detects and crops price tag regions from images
- **OCR (Kreuzberg + PaddleOCR)**: Extracts text from cropped regions
- **Queue**: Each image is processed as it arrives — no batching delay
- **LLM**: Parses raw OCR text to extract structured price information

---

## Features

- **Singleton Pattern** — OCR framework loads models once, reused across requests
- **Async Processing** — `asyncio.gather` handles multiple crops concurrently per image
- **Multi-processing ready** — Designed to scale across CPU cores with `ProcessPoolExecutor`
- **Dockerized** — Consistent environment with Kreuzberg, PaddleOCR, and ONNX Runtime pre-configured

---

## Project Structure

```
agentic_ocr/
├── kreuzberg_extractor.py   # Core OCR framework (Singleton + async extraction)
├── yolo_integration.py      # Pipeline skeleton: multi-processing + async OCR workers
├── Dockerfile               # Container setup with all system dependencies
├── docker-compose.yml       # Service config (persistent container)
├── requirements.txt         # Python dependencies
└── sample_docs/             # Place test images/PDFs here
```

---

## Quick Start

### 1. Build and run the container

```bash
docker-compose up -d --build
```

### 2. Run OCR on a sample file

Place your image in `sample_docs/` (e.g., `invoice_1.jpg`), then:

```bash
docker-compose exec agent_ocr bash
python3 kreuzberg_extractor.py
```

---

## Configuration

Edit `KreuzbergFramework` initialization in `kreuzberg_extractor.py`:

```python
framework = KreuzbergFramework(backend="paddleocr", language="en")
```

| Parameter  | Options                   | Description             |
|------------|---------------------------|-------------------------|
| `backend`  | `paddleocr`, `tesseract`  | OCR engine to use       |
| `language` | `en`, `vi`, `vie+eng`     | Target language(s)      |

---

## Dependencies

| Package          | Purpose                               |
|------------------|---------------------------------------|
| `kreuzberg`      | Core document intelligence library    |
| `paddleocr`      | Deep-learning OCR engine              |
| `paddlepaddle`   | PaddleOCR's underlying framework      |
| `onnxruntime`    | ONNX inference runtime for Kreuzberg  |

> **Note:** Kreuzberg uses ONNX Runtime internally for PaddleOCR inference (CPU mode).
