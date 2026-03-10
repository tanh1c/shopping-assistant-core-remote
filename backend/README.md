# Shopping Monitor Dashboard

Hệ thống ghi nhận hoạt động mua sắm cho người khiếm thị.  
Backend: **FastAPI + SQLite**
Frontend: **React (Vite) + Tailwind CSS + shadcn/ui**

## Quick Start (Development)

Bạn cần mở 2 terminal để chạy Backend và Frontend riêng biệt:

**1. Chạy Backend (FastAPI)**
```bash
# Cài đặt thư viện Python (nếu chưa cài)
pip install -r requirements.txt

# Khởi động server (sẽ tự động tạo mock data nếu database rỗng)
python -m app.main
```
Backend sẽ chạy tại: **http://localhost:3000** (API docs: `http://localhost:3000/api/docs`)


**2. Chạy Frontend (React/Vite)**
```bash
# Mở một terminal mới, chuyển vào thư mục frontend
cd frontend

# Cài đặt thư viện Node (cho lần đầu)
npm install

# Build và chạy dev server
npm run dev
```
Mở trình duyệt tại: **http://localhost:5173** để xem giao diện Dashboard.

## Endpoints (Backend API)

Toàn bộ dữ liệu giao tiếp thông qua JSON API (không còn trả về cấu trúc HTML HTMX).

| Endpoint | Mô tả |
|----------|-------|
| `http://localhost:3000/api/docs` | Swagger API docs |
| `POST /api/scan` | Nhận dữ liệu từ AI/CV module |
| `GET /api/logs` | Lấy danh sách logs (JSON) |
| `GET /api/stats` | Thống kê tổng quan (JSON) |
| `DELETE /api/logs/{log_id}` | Xóa một log cụ thể |

## Ghép nối với AI Module

Từ Python script của module AI/CV, gửi kết quả dạng JSON POST request:

```python
import requests

data = {
    "detected_object": "Sữa tươi Vinamilk 180ml",
    "ocr_text": "HSD: 20/12/2026",
    "price": "8000 VND",
    "confidence_score": 0.95,
    "image_base64": "data:image/jpeg;base64,...",
    "category": "dairy",
    "expiry_date": "2026-12-20",
    "warning_flag": False,
    "warning_reason": None
}

requests.post("http://localhost:3000/api/scan", json=data)
```

## Tech Stack

- **Backend**: FastAPI + SQLite (Pydantic Models)
- **Frontend**: React 19 + TypeScript + Vite
- **Styling**: Tailwind CSS v4 + shadcn/ui
- **Icons**: Lucide React
- **Design**: Light/Dark Mode + Hỗ trợ Auto-polling realtime
- **Charts**: Recharts
