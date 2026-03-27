"""
AI Pipeline - Orchestrator cho toàn bộ hệ thống
YOLO → OCR → LLM → TTS
"""
import asyncio
import base64
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np

# Import các module
from backend_client import backend_sync_enabled, build_scan_payload, post_scan_payload
from yolo.model import YOLODetector
from ocr.kreuzberg_extractor import KreuzbergFramework, KreuzbergOCRExtractor
from llm.extractor import LLMExtractor
from tts.tts_engine import TTSEngine


class ShoppingAssistantPipeline:
    """
    Main pipeline điều phối toàn bộ hệ thống
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = {
            'yolo_weights': os.getenv('YOLO_WEIGHTS_PATH', 'yolo/weights/best.pt'),
            'ocr_backend': os.getenv('OCR_BACKEND', 'paddleocr'),
            'ocr_language': os.getenv('OCR_LANGUAGE', 'vi'),
            'llm_provider': os.getenv('LLM_PROVIDER', 'alibaba'),
            'llm_api_key': os.getenv('LLM_API_KEY') or os.getenv('ALIBABA_API_KEY'),
            'llm_model': os.getenv('LLM_MODEL', 'qwen3.5-plus'),
            'llm_base_url': os.getenv('LLM_BASE_URL', 'https://coding-intl.dashscope.aliyuncs.com/v1'),
            'llm_timeout_seconds': int(os.getenv('LLM_TIMEOUT_SECONDS', '60')),
            'tts_provider': os.getenv('TTS_PROVIDER', 'gtts'),
            'enable_backend_sync': backend_sync_enabled(default=False),
            **(config or {}),
        }

        # Initialize các module
        print("🚀 Initializing Shopping Assistant Pipeline...")

        # YOLO Detector
        yolo_weights = self.config.get('yolo_weights', 'ai-pipeline/yolo/weights/best.pt')
        self.yolo = YOLODetector.get_instance(weights_path=yolo_weights)
        print("  ✅ YOLO Detector initialized")

        # OCR Extractor
        ocr_backend = self.config.get('ocr_backend', 'paddleocr')
        ocr_language = self.config.get('ocr_language', 'vi')
        self.ocr = KreuzbergOCRExtractor(
            framework=KreuzbergFramework(backend=ocr_backend, language=ocr_language)
        )
        print("  ✅ OCR Extractor initialized")

        # LLM Extractor
        llm_provider = self.config.get('llm_provider', 'alibaba')
        llm_api_key = self.config.get('llm_api_key')
        llm_model = self.config.get('llm_model')
        llm_base_url = self.config.get('llm_base_url')
        llm_timeout_seconds = self.config.get('llm_timeout_seconds')
        self.llm = LLMExtractor(
            provider=llm_provider,
            api_key=llm_api_key,
            model=llm_model,
            base_url=llm_base_url,
            timeout_seconds=llm_timeout_seconds,
        )
        print(f"  ✅ LLM Extractor initialized ({llm_provider})")

        # TTS Engine
        tts_provider = self.config.get('tts_provider', 'gtts')
        self.tts = TTSEngine(provider=tts_provider)
        print(f"  ✅ TTS Engine initialized ({tts_provider})")

        print("✅ Pipeline ready!\n")

    async def process_image(self, image: np.ndarray, source_image: Optional[str] = None) -> Dict:
        """
        Xử lý ảnh từ đầu vào đến đầu ra

        Args:
            image: Ảnh từ webcam (numpy array)
            source_image: Tên ảnh nguồn để sync backend/dashboard

        Returns:
            Dictionary chứa toàn bộ kết quả
        """
        result = {
            'success': False,
            'steps': {},
            'final_output': None,
            'selected_output': None,
            'error': None,
            'source_image': source_image or 'webcam_capture',
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
            ocr_results = await self._run_ocr_on_crops(yolo_result['cropped_images'])
            result['steps']['ocr'] = [
                {
                    'detection_idx': item['detection_idx'],
                    'ocr_text': item['ocr_text'],
                }
                for item in ocr_results
            ]
            print(f"   Extracted text from {len(ocr_results)} regions")

            if not ocr_results:
                result['error'] = "No text extracted from detected regions"
                return result

            # Step 3: LLM Extraction
            print("🧠 Step 3: Running LLM extraction...")
            extracted_info = []
            candidate_records = []
            for ocr_res in ocr_results:
                detection = yolo_result['detections'][ocr_res['detection_idx']]
                info = self.llm.extract(
                    ocr_text=ocr_res['ocr_text'],
                    detected_object=detection['class'],
                    image_base64=ocr_res.get('image_base64'),
                    image_mime_type=ocr_res.get('image_mime_type', 'image/png'),
                )
                info_dict = self._serialize_extracted_info(info)
                extracted_info.append(info_dict)
                candidate_records.append(
                    {
                        'candidate_id': len(candidate_records) + 1,
                        'detection_idx': ocr_res['detection_idx'],
                        'detected_object': detection['class'],
                        'ocr_text': ocr_res['ocr_text'],
                        'image_base64': ocr_res.get('image_base64'),
                        'image_mime_type': ocr_res.get('image_mime_type', 'image/png'),
                        'result': info_dict,
                    }
                )
            result['steps']['llm'] = extracted_info
            print(f"   Extracted {len(extracted_info)} structured records")

            scene_image_base64, scene_image_mime_type = self._encode_image_to_base64(image)
            selection = self.llm.select_best_candidate(
                scene_image_base64=scene_image_base64,
                candidates=candidate_records,
                scene_image_mime_type=scene_image_mime_type,
            )
            selected_info = self._merge_selected_candidate(selection, candidate_records)
            result['steps']['selection'] = selection

            if not selected_info:
                result['error'] = "Could not determine the best matching product and price tag"
                return result

            # Step 4: Generate speech output
            print("🔊 Step 4: Generating speech output...")
            text = self._generate_speech_text(selected_info)
            audio_path = await self.tts.generate_speech_file_async(text)
            tts_results = [
                {
                    'text': text,
                    'audio_path': audio_path
                }
            ]

            result['steps']['tts'] = tts_results
            result['final_output'] = [selected_info]
            result['selected_output'] = selected_info

            if self.config.get('enable_backend_sync'):
                try:
                    payload = build_scan_payload(
                        selected_result=selected_info,
                        source_image=source_image or 'webcam_capture',
                        image_base64=scene_image_base64,
                        category=selected_info.get('category'),
                    )
                    backend_response = await asyncio.to_thread(post_scan_payload, payload)
                    result['steps']['backend_sync'] = backend_response
                except Exception as exc:
                    result['steps']['backend_sync'] = {'error': str(exc)}

            result['success'] = True

            print("✅ Pipeline completed successfully!\n")

        except Exception as e:
            result['error'] = str(e)
            print(f"❌ Pipeline error: {e}\n")

        return result

    async def _run_ocr_on_crops(self, cropped_images) -> list[Dict]:
        temp_dir = Path(tempfile.mkdtemp(prefix="shopping-assistant-crops-"))
        temp_paths = []
        indexed_paths = []

        try:
            for idx, crop_info in enumerate(cropped_images):
                crop = crop_info['crop']
                if crop is None or crop.size == 0:
                    continue

                crop_path = temp_dir / f"crop_{idx}.png"
                if cv2.imwrite(str(crop_path), crop):
                    success, encoded = cv2.imencode(".png", crop)
                    image_base64 = None
                    if success:
                        image_base64 = base64.b64encode(encoded.tobytes()).decode("utf-8")

                    temp_paths.append(crop_path)
                    indexed_paths.append(
                        {
                            'detection_idx': crop_info['detection_idx'],
                            'crop_path': crop_path,
                            'image_base64': image_base64,
                            'image_mime_type': 'image/png',
                        }
                    )

            if not temp_paths:
                return []

            ocr_outputs = await asyncio.gather(
                *(self.ocr.extract_text(path) for path in temp_paths),
                return_exceptions=True
            )

            ocr_results = []
            for crop_meta, ocr_output in zip(indexed_paths, ocr_outputs):
                if isinstance(ocr_output, Exception):
                    print(f"   OCR failed for {crop_meta['crop_path'].name}: {ocr_output}")
                    continue
                if not ocr_output:
                    continue

                ocr_results.append({
                    'detection_idx': crop_meta['detection_idx'],
                    'ocr_text': ocr_output,
                    'image_base64': crop_meta['image_base64'],
                    'image_mime_type': crop_meta['image_mime_type'],
                })

            return ocr_results
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _serialize_extracted_info(self, info) -> Dict:
        if hasattr(info, "model_dump"):
            return info.model_dump()
        if hasattr(info, "dict"):
            return info.dict()
        if isinstance(info, dict):
            return info
        raise TypeError(f"Unsupported extracted info type: {type(info)!r}")

    def _encode_image_to_base64(self, image: np.ndarray) -> tuple[Optional[str], str]:
        success, encoded = cv2.imencode(".png", image)
        if not success:
            return None, "image/png"
        return base64.b64encode(encoded.tobytes()).decode("utf-8"), "image/png"

    def _candidate_score(self, candidate: Dict) -> tuple:
        data = candidate.get('result') or {}
        return (
            data.get('price') is not None,
            data.get('product_name') is not None,
            len(candidate.get('ocr_text') or ""),
        )

    def _merge_selected_candidate(self, selection: Optional[Dict], candidates: List[Dict]) -> Optional[Dict]:
        selected_candidate = None

        if selection:
            selected_candidate_id = selection.get('selected_candidate_id')
            selected_detection_idx = selection.get('selected_detection_idx')

            for candidate in candidates:
                if not candidate.get('result'):
                    continue
                if selected_candidate_id is not None and candidate.get('candidate_id') == selected_candidate_id:
                    selected_candidate = candidate
                    break
                if selected_detection_idx is not None and candidate.get('detection_idx') == selected_detection_idx:
                    selected_candidate = candidate
                    break

        if selected_candidate is None:
            viable_candidates = [candidate for candidate in candidates if candidate.get('result')]
            if not viable_candidates:
                return None
            selected_candidate = sorted(
                viable_candidates,
                key=self._candidate_score,
                reverse=True,
            )[0]

        final_info = dict(selected_candidate['result'])
        final_info['selected_candidate_id'] = selected_candidate.get('candidate_id')
        final_info['selected_detection_idx'] = selected_candidate.get('detection_idx')
        final_info['selection_reason'] = None
        final_info['selection_confidence'] = None

        if selection:
            if selection.get('product_name'):
                final_info['product_name'] = selection['product_name']
            if selection.get('product_name_source'):
                final_info['product_name_source'] = selection['product_name_source']
            if selection.get('price') is not None:
                final_info['price'] = selection['price']
            if selection.get('category'):
                final_info['category'] = selection['category']
            if selection.get('currency'):
                final_info['currency'] = selection['currency']
            if selection.get('ocr_text_normalized'):
                final_info['ocr_text_normalized'] = selection['ocr_text_normalized']

            final_info['selection_reason'] = selection.get('reason')
            final_info['selection_confidence'] = selection.get('confidence')

        final_info.pop('expiry_date', None)
        return final_info

    def _generate_speech_text(self, info: Dict) -> str:
        """
        Generate câu nói tự nhiên từ extracted info
        """
        parts = []

        if info.get('product_name'):
            parts.append(f"Đây là {info['product_name']}")

        if info.get('price') is not None:
            parts.append(f"giá {self._format_price_for_speech(info['price'])}")

        if not parts:
            return "Không thể nhận diện thông tin sản phẩm"

        return ", ".join(parts) + "."

    def _format_price_for_speech(self, price) -> str:
        try:
            price_value = int(float(price))
        except (TypeError, ValueError):
            return f"{price} đồng"

        if price_value >= 1000 and price_value % 1000 == 0:
            return f"{price_value // 1000} nghìn đồng"

        return f"{price_value:,.0f}".replace(",", ".") + " đồng"


# Demo usage
if __name__ == '__main__':
    import cv2

    # Initialize pipeline
    pipeline = ShoppingAssistantPipeline()

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
                print("="*50 + "\n")
            else:
                print(f"❌ Error: {result.get('error', 'Unknown error')}")

    cap.release()
    cv2.destroyAllWindows()
