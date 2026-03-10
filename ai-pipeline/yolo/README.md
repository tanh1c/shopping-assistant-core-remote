# YOLO Detection Module

Module nhận diện vật thể và price tags sử dụng YOLOv8.

## Nhiệm vụ

1. Train model YOLOv8 để detect price tags trên货架
2. Export model sang format `.pt` để sử dụng trong pipeline
3. Tạo wrapper class để các module khác gọi dễ dàng

## Cấu trúc folder

```
yolo/
├── model.py              # Wrapper class cho YOLO model
├── inference.py          # Script chạy inference
├── train.py              # Script training (dùng Colab)
├── weights/
│   └── best.pt           # Model weights sau training
├── configs/
│   └── data.yaml         # Dataset configuration
├── requirements.txt
└── Dockerfile
```

## Quick Start

### 1. Cài đặt dependencies

```bash
pip install ultralytics opencv-python numpy
```

### 2. Training model (trên Colab)

```python
from ultralytics import YOLO

# Load pretrained model
model = YOLO('yolov8x.pt')

# Train
results = model.train(
    data='configs/data.yaml',
    epochs=40,
    imgsz=960,
    device='cuda'  # hoặc 'cpu'
)

# Export model
model.export(format='onnx')
```

### 3. Inference

```python
from model import YOLODetector

detector = YOLODetector(weights='weights/best.pt')
results = detector.predict(image_path='test.jpg')
```

## API Interface

Module sẽ expose API để backend gọi:

```python
# Input: Image (numpy array hoặc base64)
# Output: List of detections
{
    "detections": [
        {
            "class": "price_tag",
            "confidence": 0.95,
            "bbox": [x1, y1, x2, y2]
        }
    ],
    "cropped_images": [...]  # Ảnh đã crop cho OCR
}
```

## Dataset

Dataset được lấy từ Roboflow:
- [SIU Dataset](https://universe.roboflow.com/tuns-workspace-y7hci/siu-mjajl)
- Classes: 21 classes (price tags + vật phẩm)

## Thành viên phụ trách

- **Hải Tuấn**: Training & model optimization
- **Tấn Hưng**: Dataset preparation & inference optimization
