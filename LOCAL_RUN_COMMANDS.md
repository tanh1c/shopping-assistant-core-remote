# Local Run Commands

File này gom các lệnh chạy local cho từng phần: `backend`, `frontend`, `ai-pipeline`, batch image test, webcam live, và backfill category.

Lưu ý:
- Các script `ai-pipeline/run_agentic_ocr.py`, `ai-pipeline/run_live_webcam.py`, `ai-pipeline/backfill_categories.py` sẽ tự động đọc file [`.env`](./.env) ở root nếu file này đã tồn tại.
- Nên dùng Python 3.11 nếu máy gặp lỗi `paddlepaddle` trên Python 3.13.
- Chạy mỗi phần trong một terminal riêng.

## 1. Setup Một Lần

### Backend

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\backend"

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\frontend"

npm install
```

### AI Pipeline

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\ai-pipeline"

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r ocr\requirements.txt
pip install vieneu --extra-index-url https://pnnbao97.github.io/llama-cpp-python-v0.3.16/cpu/
```

## 2. Chạy Backend

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\backend"
.\.venv\Scripts\Activate.ps1

$env:SEED_MOCK_DATA="false"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API docs:
- `http://127.0.0.1:8000/api/docs`

## 3. Chạy Frontend

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\frontend"

npm run dev
```

Dashboard:
- `http://127.0.0.1:5173`
- Debugger upload ảnh: `http://127.0.0.1:5173/debugger`
- Tại trang `Debugger`, bạn cũng có thể bấm chạy `run_agentic_ocr.py` trực tiếp từ web
- Web-run hiện mặc định tương đương:
  `AGENTIC_USE_YOLO=true`, `AGENTIC_ENABLE_SELECTION=true`, `AGENTIC_ENABLE_TTS=true`

## 4. Chạy AI Pipeline Với Ảnh Sample

Đặt ảnh test vào [sample_docs](./ai-pipeline/sample_docs) và đảm bảo weights YOLO nằm ở [best.pt](./ai-pipeline/yolo/weights/best.pt).

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\ai-pipeline"
.\.venv\Scripts\Activate.ps1

python run_agentic_ocr.py
```

Kết quả:
- JSON tổng hợp: [output.json](./ai-pipeline/tests/output.json)
- Audio: [audio](./ai-pipeline/audio)
- Crop YOLO: [cropped_tags](./ai-pipeline/cropped_tags)

## 5. Chạy Webcam Live Và Tự Động Push Dashboard

Script này mở webcam live, bấm `SPACE` để chụp, xử lý `YOLO -> OCR -> LLM -> TTS`, sau đó tự động push lên backend/dashboard.

Controls:
- `SPACE`: chụp và xử lý ngay
- `A`: bật/tắt auto capture theo chu kỳ
- `Q`: thoát

Tùy chọn:
- `WEBCAM_INDEX`: webcam index, mặc định `0`
- `WEBCAM_FRAME_WIDTH`: mặc định `1280`
- `WEBCAM_FRAME_HEIGHT`: mặc định `720`
- `WEBCAM_AUTO_INTERVAL_SECONDS`: chu kỳ auto capture, ví dụ `10`
- `WEBCAM_AUTO_START=true`: tự động bật auto capture khi vừa mở

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\ai-pipeline"
.\.venv\Scripts\Activate.ps1

$env:WEBCAM_INDEX="0"
$env:ENABLE_BACKEND_SYNC="true"
$env:BACKEND_URL="http://127.0.0.1:8000"
$env:WEBCAM_AUTO_INTERVAL_SECONDS="0"

python run_live_webcam.py
```

Nếu muốn auto capture mỗi 10 giây:

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\ai-pipeline"
.\.venv\Scripts\Activate.ps1

$env:WEBCAM_INDEX="0"
$env:ENABLE_BACKEND_SYNC="true"
$env:BACKEND_URL="http://127.0.0.1:8000"
$env:WEBCAM_AUTO_INTERVAL_SECONDS="10"
$env:WEBCAM_AUTO_START="true"

python run_live_webcam.py
```

Ảnh chụp live sẽ được lưu ở [captures](./ai-pipeline/captures).

## 6. Backfill Category Cho Log Cũ

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\ai-pipeline"
.\.venv\Scripts\Activate.ps1

python backfill_categories.py
```

Ép chạy lại tất cả log:

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\ai-pipeline"
.\.venv\Scripts\Activate.ps1

$env:BACKFILL_FORCE_RECLASSIFY="true"
python backfill_categories.py
```

## 7. Thứ Tự Chạy Để Test Ngày Mai

Terminal 1:

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\backend"
.\.venv\Scripts\Activate.ps1
$env:SEED_MOCK_DATA="false"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2:

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\frontend"
npm run dev
```

Terminal 3:

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core\ai-pipeline"
.\.venv\Scripts\Activate.ps1
$env:WEBCAM_INDEX="0"
$env:ENABLE_BACKEND_SYNC="true"
$env:BACKEND_URL="http://127.0.0.1:8000"
python run_live_webcam.py
```

Sau đó:
- Mở dashboard `http://127.0.0.1:5173`
- Đặt sản phẩm trước webcam
- Bấm `SPACE`
- Chờ pipeline xử lý
- Kiểm tra log mới trên dashboard

## 8. Nếu Webcam Không Mở Được

Thử webcam index khác:

```powershell
$env:WEBCAM_INDEX="1"
python run_live_webcam.py
```

Hoặc tắt app đang chiếm webcam rồi chạy lại script.
