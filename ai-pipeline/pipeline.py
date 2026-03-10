"""
AI Pipeline - Orchestrator cho toàn bộ hệ thống
YOLO → OCR → LLM → TTS
"""
import asyncio
from typing import Dict, Optional
import numpy as np

# Import các module
from yolo.model import YOLODetector
from ocr.kreuzberg_extractor import OCRExtractor  # Will be implemented
from llm.extractor import LLMExtractor, ExtractedInfo
from tts.tts_engine import TTSEngine


class ShoppingAssistantPipeline:
    """
    Main pipeline điều phối toàn bộ hệ thống
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Initialize các module
        print("🚀 Initializing Shopping Assistant Pipeline...")

        # YOLO Detector
        yolo_weights = self.config.get('yolo_weights', 'ai-pipeline/yolo/weights/best.pt')
        self.yolo = YOLODetector.get_instance(weights_path=yolo_weights)
        print("  ✅ YOLO Detector initialized")

        # OCR Extractor
        self.ocr = OCRExtractor()
        print("  ✅ OCR Extractor initialized")

        # LLM Extractor
        llm_provider = self.config.get('llm_provider', 'gemini')
        llm_api_key = self.config.get('llm_api_key')
        self.llm = LLMExtractor(provider=llm_provider, api_key=llm_api_key)
        print(f"  ✅ LLM Extractor initialized ({llm_provider})")

        # TTS Engine
        tts_provider = self.config.get('tts_provider', 'gtts')
        self.tts = TTSEngine(provider=tts_provider)
        print(f"  ✅ TTS Engine initialized ({tts_provider})")

        print("✅ Pipeline ready!\n")

    async def process_image(self, image: np.ndarray) -> Dict:
        """
        Xử lý ảnh từ đầu vào đến đầu ra

        Args:
            image: Ảnh từ webcam (numpy array)

        Returns:
            Dictionary chứa toàn bộ kết quả
        """
        result = {
            'success': False,
            'steps': {},
            'final_output': None,
            'error': None
        }

        try:
            # Step 1: YOLO Detection
            print("🔍 Step 1: Running YOLO detection...")
            yolo_result = self.yolo.predict(image)
            result['steps']['yolo'] = {
                'detections': yolo_result['detections'],
                'count': len(yolo_result['detections'])
            }
            print(f"   Found {len(yolo_result['detections'])} objects")

            if not yolo_result['detections']:
                result['error'] = "No objects detected"
                return result

            # Step 2: OCR trên cropped images
            print("📝 Step 2: Running OCR on cropped regions...")
            ocr_results = []
            for crop_info in yolo_result['cropped_images']:
                crop = crop_info['crop']
                ocr_text = self.ocr.extract_text(crop)
                if ocr_text:
                    ocr_results.append({
                        'detection_idx': crop_info['detection_idx'],
                        'ocr_text': ocr_text
                    })
            result['steps']['ocr'] = ocr_results
            print(f"   Extracted text from {len(ocr_results)} regions")

            # Step 3: LLM Extraction
            print("🧠 Step 3: Running LLM extraction...")
            extracted_info = []
            for ocr_res in ocr_results:
                detection = yolo_result['detections'][ocr_res['detection_idx']]
                info = self.llm.extract(
                    ocr_text=ocr_res['ocr_text'],
                    detected_object=detection['class']
                )
                extracted_info.append(info.dict())
            result['steps']['llm'] = extracted_info
            print(f"   Extracted {len(extracted_info)} structured records")

            # Step 4: Generate speech output
            print("🔊 Step 4: Generating speech output...")
            speech_texts = []
            for info in extracted_info:
                text = self._generate_speech_text(info)
                speech_texts.append(text)
                self.tts.speak(text, play=False)  # Lưu file, không phát ngay

            result['steps']['tts'] = speech_texts
            result['final_output'] = extracted_info
            result['success'] = True

            print("✅ Pipeline completed successfully!\n")

        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Pipeline error: {e}\n")

        return result

    def _generate_speech_text(self, info: Dict) -> str:
        """
        Generate câu nói tự nhiên từ extracted info
        """
        parts = []

        if info.get('product_name'):
            parts.append(f"Đây là {info['product_name']}")

        if info.get('price'):
            price_str = f"{info['price']:,.0f}".replace(',', '.')
            parts.append(f"giá {price_str} ngàn đồng")

        if info.get('expiry_date'):
            parts.append(f"hạn sử dụng đến ngày {info['expiry_date']}")

        if not parts:
            return "Không thể nhận diện thông tin sản phẩm"

        return ", ".join(parts) + "."


# Demo usage
if __name__ == '__main__':
    import cv2

    # Initialize pipeline
    pipeline = ShoppingAssistantPipeline(config={
        'llm_provider': 'gemini',  # hoặc 'ollama'
        'llm_api_key': 'YOUR_API_KEY',  # Replace với API key thật
        'tts_provider': 'gtts'
    })

    # Test với webcam
    cap = cv2.VideoCapture(0)

    print("Press SPACE to capture and process, 'q' to quit\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow('Shopping Assistant - Press SPACE to capture', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            # Process captured frame
            result = asyncio.run(pipeline.process_image(frame))

            if result['success']:
                print("\n" + "="*50)
                print("📊 KẾT QUẢ:")
                print("="*50)
                for item in result['final_output']:
                    print(f"  • {item.get('product_name', 'Unknown')}")
                    print(f"    Giá: {item.get('price', 'N/A')} {item.get('currency', 'VND')}")
                    print(f"    HSD: {item.get('expiry_date', 'N/A')}")
                print("="*50 + "\n")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")

    cap.release()
    cv2.destroyAllWindows()
