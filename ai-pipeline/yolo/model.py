"""
YOLO Detection Module - Wrapper cho YOLOv8 model
"""
from ultralytics import YOLO
import cv2
import numpy as np
from typing import List, Dict, Optional
import base64


class YOLODetector:
    """
    Singleton wrapper cho YOLOv8 model
    """
    _instance = None

    def __init__(self, weights_path: str = 'weights/best.pt', conf_threshold: float = 0.25):
        self.conf_threshold = conf_threshold
        self.model = YOLO(weights_path)

    @classmethod
    def get_instance(cls, weights_path: str = 'weights/best.pt') -> 'YOLODetector':
        if cls._instance is None:
            cls._instance = YOLODetector(weights_path)
        return cls._instance

    def predict(self, image: np.ndarray) -> Dict:
        """
        Chạy inference trên ảnh đầu vào

        Args:
            image: Ảnh numpy array (BGR format)

        Returns:
            Dictionary chứa detections và cropped images
        """
        results = self.model(image, conf=self.conf_threshold)

        detections = []
        cropped_images = []

        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for i, box in enumerate(boxes):
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0].cpu().numpy())
                    cls_id = int(box.cls[0].cpu().numpy())
                    cls_name = self.model.names[cls_id]

                    detections.append({
                        'class': cls_name,
                        'class_id': cls_id,
                        'confidence': conf,
                        'bbox': [int(x1), int(y1), int(x2), int(y2)]
                    })

                    # Crop region để gửi sang OCR
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    cropped = image[y1:y2, x1:x2]
                    cropped_images.append({
                        'crop': cropped,
                        'detection_idx': i
                    })

        return {
            'detections': detections,
            'cropped_images': cropped_images,
            'original_shape': image.shape
        }

    def predict_from_base64(self, image_base64: str) -> Dict:
        """
        Chạy inference từ base64 image
        """
        # Decode base64
        img_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return self.predict(image)


# Demo usage
if __name__ == '__main__':
    detector = YOLODetector.get_instance()
    print("YOLO Detector initialized successfully!")
