# HANDOFF: Shopping Assistant Monorepo Setup

## 🎯 Mục tiêu
Tạo monorepo cho dự án **Shopping Assistant for Visually Impaired** — gồm backend FastAPI, frontend React, và AI pipeline (YOLO/OCR/LLM/TTS). Gom 3 repo rời rạc thành 1 cấu trúc thống nhất, có Docker orchestration và documentation đầy đủ cho 6 thành viên.

---

## ✅ Hiện trạng hiện tại

- Monorepo structure hoàn thành: `backend/`, `ai-pipeline/`, `frontend/`, `shared/`
- Docker Compose orchestration đã tạo
- Documentation đầy đủ (README, TEAM_SETUP_GUIDE, QUICKSTART, COMPLETE_SUMMARY, MIGRATION_SUMMARY)
- Frontend đã fix cấu trúc nested (`frontend/frontend/next-app` → `frontend/`)
- Chưa push lên GitHub
- Chưa test Docker build thực tế

---

## 📁 Các file cần xem

### Core setup
- `docker-compose.yml` — orchestration chính
- `setup.ps1` / `setup.sh` — setup scripts
- `.env.example` — environment template

### AI Pipeline (templates đã tạo, code placeholder)
- `ai-pipeline/pipeline.py` — orchestrator
- `ai-pipeline/ocr/` — copied từ `agentic_ocr`
- `ai-pipeline/yolo/` — placeholder cho Hải Tuấn + Tấn Hưng
- `ai-pipeline/llm/` — placeholder cho QHieu + NNam
- `ai-pipeline/tts/` — placeholder TTS
- `ai-pipeline/Dockerfile`
- `ai-pipeline/requirements.txt`

### Backend & Frontend
- `backend/` — FastAPI (đã có sẵn, chưa sửa)
- `frontend/` — React + Vite (đã fix folder structure)

### Documentation
- `README.md`
- `TEAM_SETUP_GUIDE.md`
- `QUICKSTART.md`
- `COMPLETE_SUMMARY.md`
- `MIGRATION_SUMMARY.md`

---

## ⚙️ Quyết định kỹ thuật đã chốt

- **Monorepo layout**: `backend/`, `ai-pipeline/`, `frontend/`, `shared/` ở root
- **AI Pipeline**: Module hóa thành `yolo/`, `ocr/`, `llm/`, `tts/` subdirectories
- **Docker orchestration**: `docker-compose.yml` với 4 services (backend, frontend, ai-pipeline, shared)
- **OCR module**: Đã copy từ `agentic_ocr` — **KHÔNG merge lại**
- **Frontend stack**: Vite + React + TypeScript + shadcn/ui + Tailwind v4 (không phải Next.js)
- **Backend stack**: FastAPI + SQLite (giữ nguyên từ web-monitor)
- **AI pipeline entry**: `pipeline.py` là orchestrator chính, gọi từng module

---

## 🚫 Ràng buộc cần tuân thủ

- Frontend chạy port **5173** (Vite default)
- Backend chạy port **8000** (FastAPI default)
- AI pipeline chạy port **8001**
- OCR module đã có code thực — không viết lại từ đầu
- YOLO, LLM, TTS là **templates/placeholders** — cần implement thực tế
- Không xóa `shared/` folder
- Git history không cần giữ (init mới)

---

## ❌ Những cách đã thử nhưng không hiệu quả

- **Thao tác nested folder**: `mv frontend/frontend/next-app/*` chỉ move được file visible, không move hidden files hoặc subfolders nếu có. Fix bằng `cp -r` rồi `rm -rf`.
- **rmdir folder không empty**: `rmdir` fail nếu folder còn hidden files (`.prettierignore`, `._*` macOS resource forks). Fix bằng `rm -rf`.
- **Dockerfile cho frontend Vite**: Không dùng `next` image vì đây là Vite project, không phải Next.js. Đã viết Dockerfile dùng `node:20-alpine` + `serve`.

---

## ➡️ Bước tiếp theo nhỏ nhất, an toàn nhất

**Verify Docker Compose syntax và build backend image trước:**

```powershell
cd "C:\Users\LG\Desktop\Study Material\DADN\shopping-assistant-core"
docker compose config --quiet
```

Nếu không lỗi → chạy:
```powershell
docker compose build backend
docker compose up -d backend
curl http://localhost:8000/api/docs
```

**Lý do**: Backend là service đơn giản nhất, có sẵn code thực, không phụ thuộc AI models. Verify được nó = infrastructure (Docker, ports, network) hoạt động.

---

## 🔍 Lệnh verify kết quả

```powershell
# 1. Kiểm tra Docker Compose hợp lệ
docker compose config --quiet

# 2. Build backend
docker compose build backend

# 3. Chạy backend
docker compose up -d backend

# 4. Test backend health
curl http://localhost:8000/api/docs
# Hoặc: curl http://localhost:8000/health

# 5. Stop
docker compose down
```

**Expected output**: Swagger UI hiện ra ở `http://localhost:8000/api/docs`

---

## 📌 Ghi chú cho agent tiếp theo

- OCR code đã thực, nhưng YOLO/LLM/TTS chỉ là templates
- Nếu cần sửa backend port, check `docker-compose.yml` trước
- Frontend `package.json` dùng `"next-app"` làm name — không nhầm với Next.js
