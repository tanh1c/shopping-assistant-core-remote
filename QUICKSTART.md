# 🚀 Quick Start Guide

## Tóm tắt những gì đã tạo

### ✅ Cấu trúc monorepo hoàn chỉnh

```
shopping-assistant-core/
├── backend/                 # FastAPI backend (đã có sẵn)
│   ├── app/
│   ├── models/
│   ├── requirements.txt
│   └── Dockerfile           # ✅ Mới tạo
│
├── ai-pipeline/             # AI/ML Pipeline
│   ├── pipeline.py          # ✅ Main orchestrator
│   ├── yolo/                # Template cho Hải Tuấn + Tấn Hưng
│   ├── ocr/                 # ✅ Copied từ agentic_ocr
│   ├── llm/                 # ✅ Template cho QHieu + NNam
│   ├── tts/                 # ✅ Template TTS
│   ├── Dockerfile           # ✅ Mới tạo
│   └── requirements.txt     # ✅ Mới tạo
│
├── frontend/                # ✅ Fixed structure
│   ├── src/
│   ├── package.json
│   ├── Dockerfile           # ✅ Mới tạo
│   └── ...
│
├── docker-compose.yml       # ✅ Đã tạo
├── .env.example             # ✅ Đã tạo
├── .gitignore               # ✅ Đã tạo
├── README.md                # ✅ Đã tạo
├── TEAM_SETUP_GUIDE.md      # ✅ Đã tạo
├── MIGRATION_SUMMARY.md     # ✅ Đã tạo
├── setup.sh                 # ✅ Linux/Mac setup
└── setup.ps1                # ✅ Windows setup
```

---

## 📋 Các bước tiếp theo

### 1. Push lên GitHub

```bash
cd shopping-assistant-core

# Initialize git
git init

# Tạo repo trên GitHub trước, sau đó:
git remote add origin https://github.com/YOUR-ORG/shopping-assistant-core.git

# Commit
git add .
git commit -m "Initial monorepo setup

- Backend: FastAPI + SQLite
- Frontend: React + Vite + shadcn/ui
- AI Pipeline: YOLO + OCR + LLM + TTS modules
- Docker Compose for orchestration
"

# Push
git push -u origin main
```

### 2. Chạy testing local

**Option A: Docker (Recommended)**

```bash
cd shopping-assistant-core

# Copy .env file
cp .env.example .env

# Edit .env với API keys (nếu cần)
notepad .env  # Windows
nano .env     # Linux/Mac

# Build và chạy
docker compose up -d --build

# Xem logs
docker compose logs -f

# Stop
docker compose down
```

**Option B: Local Development**

```bash
# Terminal 1 - Backend
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m app.main

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev

# Terminal 3 - AI Pipeline (optional)
cd ai-pipeline
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python pipeline.py
```

### 3. Truy cập services

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | Dashboard UI |
| Backend API | http://localhost:8000 | FastAPI server |
| API Docs | http://localhost:8000/api/docs | Swagger UI |
| AI Pipeline | Port 8001 | Internal AI service |

---

## 👥 Phân công cho nhóm

Gửi message này cho nhóm:

```
👋 Chào cả nhóm,

Mình đã tạo monorepo cho dự án Shopping Assistant:
📁 https://github.com/YOUR-ORG/shopping-assistant-core

📌 Mỗi người clone về và check folder của mình:

git clone https://github.com/YOUR-ORG/shopping-assistant-core.git

📖 Xem chi tiết trong TEAM_SETUP_GUIDE.md

✅ Backend + Frontend: @Ban (đã xong)
✅ YOLO: @HaiTuan @TanHung - folder ai-pipeline/yolo/
✅ OCR + LLM: @QHieu @NNam - folder ai-pipeline/ocr/, ai-pipeline/llm/

🚀 Chạy thử: docker compose up -d

有任何问题随时联系！
```

---

## 📚 Tài liệu đã tạo

| File | Description |
|------|-------------|
| `README.md` | Main documentation |
| `TEAM_SETUP_GUIDE.md` | Hướng dẫn cho từng thành viên |
| `MIGRATION_SUMMARY.md` | Summary migration process |
| `QUICKSTART.md` | File này - quick reference |
| `.env.example` | Environment template |

---

## 🐛 Troubleshooting

### Frontend không chạy được

```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend lỗi dependencies

```bash
cd backend
pip uninstall -y -r requirements.txt
pip install -r requirements.txt
```

### Docker build lỗi

```bash
docker compose down -v
docker compose build --no-cache
docker compose up
```

---

**Ready to go! 🎉**
