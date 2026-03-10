# 📋 Hướng dẫn setup cho từng thành viên

---

## 👤 Bạn (UI/Dashboard + Backend Lead)

### ✅ Công việc đã hoàn thành

- [x] Backend API với FastAPI
- [x] Frontend Dashboard với Next.js + shadcn/ui
- [x] Docker Compose orchestration
- [x] Database schema & API contract
- [x] TTS module template

### 🔜 Công việc tiếp theo

1. **Integration Testing**
   - Test end-to-end flow: YOLO → OCR → LLM → Backend → Frontend
   - Setup WebSocket cho realtime updates

2. **UI/UX Improvements**
   - Thêm real-time polling cho dashboard
   - Hiển thị webcam feed trên dashboard
   - Thêm chart thống kê

3. **Deployment**
   - Deploy frontend lên Vercel
   - Deploy backend lên Render/Railway
   - Setup Supabase/Firebase database

---

## 👤 Hải Tuấn & Tấn Hưng (YOLO Module)

### 📁 Folder của bạn: `ai-pipeline/yolo/`

### ✅ Công việc cần làm

1. **Dataset Preparation**
   - Download dataset từ Roboflow (đã có trong notebook)
   - Preprocess và augment data
   - Tạo data.yaml config

2. **Training Model**
   - Dùng notebook `train_colab.ipynb` để train
   - Chọn model: yolov8m.pt hoặc yolov8x.pt
   - Export weights best.pt về folder `ai-pipeline/yolo/weights/`

3. **Inference Optimization**
   - Test inference time trên CPU
   - Optimize cho Raspberry Pi 5 (giảm imgsz, confidence threshold)
   - Export sang ONNX nếu cần tốc độ nhanh hơn

### 📖 Tài liệu

- `ai-pipeline/yolo/README.md` - API interface & usage
- `train_colab.ipynb` - Training notebook
- https://docs.ultralytics.com/ - YOLOv8 docs

### ✅ Checkpoint cần đạt

- [ ] Model weights `best.pt` với mAP@0.5 > 0.8
- [ ] Inference time < 100ms trên CPU
- [ ] Test thành công với `python ai-pipeline/yolo/model.py`

---

## 👤 QHieu & NNam (OCR + LLM Module)

### 📁 Folder của bạn: `ai-pipeline/ocr/`, `ai-pipeline/llm/`

### ✅ Công việc cần làm

#### OCR Module

1. **Setup Kreuzberg**
   - Đọc `ai-pipeline/ocr/README.md`
   - Cài đặt dependencies: `pip install kreuzberg paddleocr`
   - Test với sample images

2. **Preprocessing**
   - Implement image enhancement (contrast, denoise)
   - Perspective correction cho bao bì cong
   - Text line detection & separation

3. **Vietnamese OCR Optimization**
   - Fine-tune PaddleOCR với dataset tiếng Việt
   - Test với các font chữ khác nhau trên bao bì

#### LLM Module

1. **Prompt Engineering**
   - Đọc `ai-pipeline/llm/README.md`
   - Tạo prompt templates cho extraction
   - Test với Gemini API

2. **LayoutLM (Optional)**
   - Fine-tune LayoutLM cho Vietnamese receipts
   - Integration với OCR output

3. **Integration**
   - Connect với pipeline: `python ai-pipeline/pipeline.py`
   - Test end-to-end flow

### 📖 Tài liệu

- https://kreuzberg-dev.github.io/kreuzberg/
- https://github.com/PaddlePaddle/PaddleOCR
- https://cloud.google.com/gemini/docs

### ✅ Checkpoint cần đạt

- [ ] OCR accuracy > 90% trên text in rõ ràng
- [ ] LLM extraction đúng schema JSON
- [ ] End-to-end test thành công với pipeline

---

## 🔄 Collaboration Workflow

### 1. Git Workflow

```bash
# Pull code mới nhất
git pull origin main

# Tạo branch cho feature của bạn
git checkout -b feature/yolo-training

# Commit code vào folder của bạn
git add ai-pipeline/yolo/
git commit -m "Train YOLOv8 model v1"

# Push lên GitHub
git push origin feature/yolo-training

# Tạo Pull Request
```

### 2. Testing Integration

Sau khi hoàn thành module, test với pipeline:

```bash
cd ai-pipeline
python pipeline.py
```

### 3. Docker Testing

Test toàn bộ hệ thống:

```bash
docker-compose up -d --build
docker-compose logs -f
```

---

## 📞 Hỗ trợ

- **Kỹ thuật**: Tạo issue trên GitHub
- **Module questions**: Chat trong Discord/Slack group
- **Demo requirements**: Xem `project_overview.md`

---

## 🎯 Timeline gợi ý

| Week | YOLO Team | OCR/LLM Team | Backend/Frontend Team |
|------|-----------|--------------|----------------------|
| 1 | Dataset & Training | OCR setup & testing | Integration scaffolding |
| 2 | Inference optimization | LLM prompt engineering | WebSocket realtime |
| 3 | Integration test | End-to-end test | Full system test |
| 4 | Documentation | Documentation | Deployment prep |

---

**Let's build something amazing! 🚀**
