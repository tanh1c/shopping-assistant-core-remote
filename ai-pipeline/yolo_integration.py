import logging
from pathlib import Path
from typing import List

logger = logging.getLogger("YOLODetector")


class PriceTagDetector:

    def __init__(self, model_version: str = "yolo/weights/best.pt", confidence_threshold: float = 0.1):
        """
        Args:
            model_version: Path to YOLO weights file (e.g., yolo/weights/best.pt).
            confidence_threshold: Minimum confidence score (0.0 to 1.0) to keep a bounding box.
        """
        self.model_version = str(model_version)
        self.conf_threshold = confidence_threshold
        logger.info(f"Loading YOLO model ({self.model_version})...")

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "PriceTagDetector requires the `ultralytics` package to be installed."
            ) from exc

        self.model = YOLO(self.model_version)
        logger.info("YOLO initialization successful.")

    def detect_and_crop(self, image_path: str | Path, output_dir: str | Path = "cropped_tags") -> List[Path]:
        """
        Args:
            image_path: Path to the main input image.
            output_dir: Directory to save the cropped tag images.
        Returns:
            List of paths to smaller cropped images ready for OCR processing.
        """
        path = Path(image_path)
        out_dir = Path(output_dir)

        if not path.exists():
            logger.error(f"Image not found: {path}")
            return []

        out_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Starting object detection on image: {path.name}")

        results = self.model.predict(
            source=str(path),
            conf=self.conf_threshold,
            save=False,
        )

        try:
            import cv2
        except ImportError as exc:
            raise ImportError(
                "PriceTagDetector requires the `opencv-python-headless` package to be installed."
            ) from exc

        img = cv2.imread(str(path))
        if img is None:
            logger.error(f"Failed to open image via OpenCV: {path}")
            return []

        cropped_files = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for idx, box in enumerate(boxes):
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                cls = int(box.cls[0])

                logger.info(f"Detected object {idx + 1} (Class {cls}) with confidence: {conf:.2f}")

                cropped_img = img[y1:y2, x1:x2]
                crop_path = out_dir / f"{path.stem}_tag_{idx + 1}.jpg"
                cv2.imwrite(str(crop_path), cropped_img)
                cropped_files.append(crop_path)

        logger.info(f"Completed! Saved {len(cropped_files)} cropped tag images to {out_dir}")
        return cropped_files


def main():
    detector = PriceTagDetector(model_version="yolo/weights/best.pt")
    detector.detect_and_crop(image_path="sample_docs/invoice_1.jpg")


if __name__ == "__main__":
    main()
