# Shopping Assistant Core

Monorepo cho hệ thống hỗ trợ mua sắm dành cho người khiếm thị. Phiên bản hiện tại tập trung vào luồng xử lý local trên laptop:

- webcam hoặc ảnh mẫu
- YOLO phát hiện price tag
- OCR trích xuất văn bản
- LLM chọn đúng tag và chuẩn hóa thông tin sản phẩm
- TTS đọc kết quả bằng tiếng Việt
- FastAPI backend lưu log
- React dashboard cho guardian theo dõi, chỉnh sửa và debug

![Architecture](docs/architecture.png)

## Trạng thái hiện tại

Codebase hiện tại đã có các phần chính sau:

- `ai-pipeline` chạy được batch OCR từ thư mục `sample_docs`
- `ai-pipeline` có live webcam runner và tự push kết quả lên backend/dashboard
- `backend` nhận log từ pipeline, lưu SQLite, cung cấp API cho frontend
- `frontend` là web dashboard dùng `React + Vite`, có 4 trang:
  - `Dashboard`
  - `History`
  - `Analytics`
  - `Debugger`
- `Debugger` cho phép:
  - upload ảnh trực tiếp vào `ai-pipeline/sample_docs`
  - chạy `run_agentic_ocr.py` từ web
  - bật/tắt `YOLO`, `AI selection`, `TTS`
  - xem log chạy gần nhất
- LLM mặc định đang ưu tiên Alibaba DashScope compatible API
- TTS mặc định đang ưu tiên `vieneu`

## Kiến trúc triển khai hiện tại

Luồng chính trong repo hiện tại:

```text
Webcam / Sample Images
        |
        v
ai-pipeline
YOLO -> OCR -> LLM -> Category -> TTS
        |
        v
POST /api/scan
        |
        v
FastAPI backend + SQLite
        |
        v
React guardian dashboard
Dashboard / History / Analytics / Debugger
```

Lưu ý:

- Hiện tại `ai-pipeline` không vận hành như một HTTP inference service riêng cho frontend.
- Frontend làm việc với `backend`.
- Khi bấm chạy batch từ trang `Debugger`, backend sẽ spawn `python run_agentic_ocr.py` trong `ai-pipeline`.

## Cấu trúc monorepo

```text
shopping-assistant-core/
├── ai-pipeline/
│   ├── pipeline.py                 # Orchestrator YOLO -> OCR -> LLM -> TTS
│   ├── run_agentic_ocr.py         # Batch runner cho ảnh trong sample_docs
│   ├── run_live_webcam.py         # Live webcam runner
│   ├── backfill_categories.py     # Backfill category cho log cũ
│   ├── backend_client.py          # Sync kết quả lên backend
│   ├── yolo/
│   │   ├── model.py
│   │   └── weights/best.pt
│   ├── ocr/
│   ├── llm/
│   ├── tts/
│   ├── sample_docs/               # Ảnh test batch
│   ├── captures/                  # Ảnh chụp từ live webcam
│   ├── cropped_tags/              # Crop YOLO để debug
│   ├── audio/                     # Audio TTS đầu ra
│   └── tests/
│       ├── output.json
│       └── test_pipeline.py
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app + debugger endpoints
│   │   ├── database.py            # SQLite CRUD
│   │   ├── models.py              # Pydantic schemas
│   │   └── mock_data.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── dashboard.tsx
│   │   │   ├── history.tsx
│   │   │   ├── analytics.tsx
│   │   │   └── debugger.tsx
│   │   ├── components/
│   │   ├── lib/
│   │   ├── App.tsx
│   │   └── types.ts
│   ├── package.json
│   └── Dockerfile
├── docs/
├── .env.example
├── docker-compose.yml
├── HANDOFF.md
├── LOCAL_RUN_COMMANDS.md
└── README.md
```

## Stack công nghệ

### AI Pipeline

- Python 3.11
- OpenCV
- YOLO
- Kreuzberg + PaddleOCR
- LLM extraction qua Alibaba DashScope compatible API
- TTS qua `vieneu`

### Backend

- FastAPI
- SQLite
- Pydantic

### Frontend

- React 19
- TypeScript
- Vite
- React Router
- Tailwind CSS
- shadcn/ui
- Recharts

## Các tính năng chính

### 1. Product scan pipeline

- Detect nhiều price tag trong cùng một ảnh
- OCR trên từng candidate crop
- Cho LLM nhìn ảnh scene + crop để chọn đúng price tag khớp với sản phẩm
- Chuẩn hóa tên sản phẩm và giá
- Phân loại category bằng LLM
- Sinh audio tiếng Việt cho kết quả cuối

### 2. Guardian dashboard

- `Dashboard`: thẻ thống kê, cảnh báo, recent products, confidence bar, category badge
- `History`: xem log cũ, sửa record, xóa record
- `Analytics`: pie chart category và bar chart confidence
- `Debugger`: upload ảnh test, chạy batch OCR từ web, xem trạng thái và log

### 3. Batch sample workflow

- đặt ảnh `.jpg/.jpeg/.png/.webp` vào `ai-pipeline/sample_docs`
- chạy `python run_agentic_ocr.py`
- kết quả tổng hợp được lưu vào `ai-pipeline/tests/output.json`

### 4. Live webcam workflow

- mở webcam local
- bấm `SPACE` để chụp
- pipeline xử lý và push log mới lên dashboard
- hỗ trợ auto-capture theo chu kỳ

## Yêu cầu môi trường

Khuyên dùng:

- Python `3.11`
- Node.js `20+`
- `npm`
- webcam local nếu muốn test live
- file YOLO weights tại `ai-pipeline/yolo/weights/best.pt`
- API key cho Alibaba DashScope nếu dùng LLM cloud

Lưu ý:

- Trên Windows, nên chạy `ai-pipeline` local thay vì trông chờ Docker webcam passthrough.
- Nếu dùng Python `3.13` có thể gặp lỗi với một số dependency OCR/Paddle.

## Cấu hình nhanh

Tạo file `.env` từ [`.env.example`](./.env.example):

```powershell
Copy-Item .env.example .env
```

Các biến quan trọng nhất:

```env
ALIBABA_API_KEY=your_key
LLM_PROVIDER=alibaba
LLM_API_KEY=your_key
LLM_BASE_URL=https://coding-intl.dashscope.aliyuncs.com/v1
LLM_MODEL=qwen3.5-plus

TTS_PROVIDER=vieneu

BACKEND_URL=http://localhost:8000
ENABLE_BACKEND_SYNC=false

WEBCAM_INDEX=0
AGENTIC_USE_YOLO=true
AGENTIC_ENABLE_SELECTION=true
AGENTIC_ENABLE_TTS=true
```

Model visual hiện đang phù hợp:

- `qwen3.5-plus`
- `kimi-k2.5`

## Cách chạy local

Tài liệu lệnh đầy đủ nằm ở [LOCAL_RUN_COMMANDS.md](./LOCAL_RUN_COMMANDS.md).

Luồng local khuyên dùng:

### 1. Setup dependency

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Frontend:

```powershell
cd frontend
npm install
```

AI pipeline:

```powershell
cd ai-pipeline
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r ocr\requirements.txt
pip install vieneu --extra-index-url https://pnnbao97.github.io/llama-cpp-python-v0.3.16/cpu/
```

### 2. Chạy backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
$env:SEED_MOCK_DATA="false"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Chạy frontend

```powershell
cd frontend
npm run dev
```

Truy cập:

- Dashboard: `http://127.0.0.1:5173`
- Debugger: `http://127.0.0.1:5173/debugger`
- Backend docs: `http://127.0.0.1:8000/api/docs`

### 4. Chạy batch OCR từ terminal

```powershell
cd ai-pipeline
.\.venv\Scripts\Activate.ps1
python run_agentic_ocr.py
```

### 5. Chạy batch OCR từ web

1. mở `http://127.0.0.1:5173/debugger`
2. upload ảnh vào `sample_docs`
3. chọn các switch:
   - `Dùng YOLO`
   - `Chọn candidate bằng AI`
   - `Bật TTS`
4. bấm `Chạy run_agentic_ocr.py`

### 6. Chạy live webcam

```powershell
cd ai-pipeline
.\.venv\Scripts\Activate.ps1
$env:WEBCAM_INDEX="0"
$env:ENABLE_BACKEND_SYNC="true"
$env:BACKEND_URL="http://127.0.0.1:8000"
python run_live_webcam.py
```

Controls:

- `SPACE`: chụp và xử lý ngay
- `A`: bật/tắt auto capture
- `Q`: thoát

## Docker

`docker-compose.yml` hiện đang dựng 3 service:

- `backend`
- `frontend`
- `ai-pipeline`

Chạy:

```powershell
docker-compose up -d --build
```

Truy cập:

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/api/docs`

Lưu ý quan trọng về Docker hiện tại:

- frontend trong Docker được serve static ở cổng `3000`
- backend ở cổng `8000`
- `ai-pipeline` container hiện dùng cho môi trường đóng gói và chia sẻ `sample_docs`, không phải inference API public riêng
- webcam passthrough trong compose chủ yếu phù hợp Linux
- nếu test live webcam trên Windows, nên chạy `ai-pipeline` local

## API chính của backend

### Public app / health

- `GET /health`
- `GET /`
- `GET /history`
- `GET /analytics`

### JSON API cho dashboard và pipeline

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `GET` | `/api/logs` | Lấy danh sách log |
| `GET` | `/api/logs/{log_id}` | Lấy chi tiết 1 log |
| `POST` | `/api/scan` | Nhận payload scan từ pipeline |
| `PUT` | `/api/logs/{log_id}` | Cập nhật log |
| `DELETE` | `/api/logs/{log_id}` | Xóa log |
| `GET` | `/api/stats` | Lấy thống kê tổng quan |

### Debugger API

| Method | Endpoint | Mô tả |
| --- | --- | --- |
| `GET` | `/api/debugger/sample-docs` | Liệt kê ảnh trong `sample_docs` |
| `GET` | `/api/debugger/sample-docs/{filename}` | Xem ảnh debugger |
| `POST` | `/api/debugger/sample-docs/upload` | Upload ảnh test |
| `DELETE` | `/api/debugger/sample-docs/{filename}` | Xóa ảnh test |
| `GET` | `/api/debugger/agentic-ocr/status` | Trạng thái runner batch |
| `POST` | `/api/debugger/agentic-ocr/run` | Chạy `run_agentic_ocr.py` từ web |

## Các output quan trọng

- Ảnh test batch: [ai-pipeline/sample_docs](./ai-pipeline/sample_docs)
- Output JSON: [ai-pipeline/tests/output.json](./ai-pipeline/tests/output.json)
- Crop YOLO: [ai-pipeline/cropped_tags](./ai-pipeline/cropped_tags)
- Audio TTS: [ai-pipeline/audio](./ai-pipeline/audio)
- Capture webcam live: [ai-pipeline/captures](./ai-pipeline/captures)

## Troubleshooting

### 1. Cài dependency OCR bị lỗi trên Python 3.13

Chuyển sang Python `3.11`.

### 2. `run_agentic_ocr.py` không phát hiện được gì

Kiểm tra:

- ảnh đã nằm trong `ai-pipeline/sample_docs`
- weights tồn tại ở `ai-pipeline/yolo/weights/best.pt`
- `AGENTIC_USE_YOLO=true`

### 3. Dashboard không thấy log mới

Kiểm tra:

- backend đang chạy ở `http://127.0.0.1:8000`
- `ENABLE_BACKEND_SYNC=true` khi chạy pipeline
- frontend đang dùng đúng `VITE_API_BASE_URL`

### 4. Nút chạy batch từ web không hoạt động

Backend sẽ cố chạy Python trong:

- `ai-pipeline/.venv/Scripts/python.exe` trên Windows
- hoặc Python override từ `DEBUGGER_AI_PIPELINE_PYTHON`

Hãy chắc chắn `ai-pipeline/.venv` đã được cài dependency đầy đủ.

### 5. Webcam không mở được

Thử đổi:

```powershell
$env:WEBCAM_INDEX="1"
python run_live_webcam.py
```

## Tài liệu liên quan

- [LOCAL_RUN_COMMANDS.md](./LOCAL_RUN_COMMANDS.md)
- [QUICKSTART.md](./QUICKSTART.md)
- [HANDOFF.md](./HANDOFF.md)
- [.env.example](./.env.example)

## Ghi chú

README này phản ánh codebase hiện tại trong repo. Nếu bạn thay đổi thêm luồng deploy cloud, DB production, hoặc inference service dạng HTTP riêng cho `ai-pipeline`, hãy cập nhật lại README để tránh lệch với cách chạy thực tế.
