import asyncio
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from backend_client import (
    backend_sync_enabled,
    build_scan_payload,
    encode_image_path_to_data_url,
    post_scan_payload,
)

logger = logging.getLogger("ShoppingInferenceService")


def _load_project_env(base_dir: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = base_dir.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


@dataclass(slots=True)
class InferenceOptions:
    use_yolo: bool = True
    enable_selection: bool = True
    enable_tts: bool = False
    enable_backend_sync: bool = False


class InferenceInitializationError(RuntimeError):
    """Raised when the reusable inference service cannot initialize its dependencies."""


def _candidate_score(candidate: Dict) -> tuple:
    result = candidate.get("result") or {}
    return (
        result.get("price") is not None,
        (result.get("product_name") or result.get("name")) is not None,
        len(result.get("raw_ocr_text") or ""),
    )


def _sanitize_candidate(candidate: Dict) -> Dict:
    result = candidate.get("result") or {}
    return {
        "candidate_id": candidate.get("candidate_id"),
        "crop_name": candidate.get("crop_name"),
        "crop_path": candidate.get("crop_path"),
        "name": result.get("name") or result.get("product_name"),
        "price": result.get("price"),
        "category": result.get("category"),
        "price_tag_text_normalized": result.get("price_tag_text_normalized"),
        "raw_ocr_text": result.get("raw_ocr_text"),
    }


def _has_meaningful_result(result: Optional[Dict]) -> bool:
    if not result:
        return False

    return any(
        result.get(key) not in {None, ""}
        for key in ("name", "product_name", "price", "category", "price_tag_text_normalized")
    )


def _choose_candidate_fallback(candidates: List[Dict]) -> Optional[Dict]:
    viable_candidates = [
        candidate
        for candidate in candidates
        if _has_meaningful_result(candidate.get("result"))
    ]
    if not viable_candidates:
        return None
    return sorted(viable_candidates, key=_candidate_score, reverse=True)[0]


def _merge_selection(selection: Optional[Dict], candidates: List[Dict]) -> Optional[Dict]:
    selected_candidate = None

    if selection:
        selected_candidate_id = selection.get("selected_candidate_id")
        selected_crop_name = selection.get("selected_crop_name")

        for candidate in candidates:
            if not candidate.get("result"):
                continue
            if selected_candidate_id is not None and candidate.get("candidate_id") == selected_candidate_id:
                selected_candidate = candidate
                break
            if selected_crop_name and candidate.get("crop_name") == selected_crop_name:
                selected_candidate = candidate
                break

    if selected_candidate is None:
        selected_candidate = _choose_candidate_fallback(candidates)

    if selected_candidate is None:
        return None

    result = dict(selected_candidate["result"])
    result.pop("expiration_date", None)
    result["selected_candidate_id"] = selected_candidate["candidate_id"]
    result["selected_crop_name"] = selected_candidate["crop_name"]
    result["selected_crop_path"] = selected_candidate["crop_path"]
    result["product_name"] = result.get("name") or result.get("product_name")

    if selection:
        if selection.get("product_name"):
            result["name"] = selection["product_name"]
            result["product_name"] = selection["product_name"]
        if selection.get("product_name_source"):
            result["product_name_source"] = selection["product_name_source"]
        if selection.get("price") is not None:
            result["price"] = selection["price"]
        if selection.get("category"):
            result["category"] = selection["category"]
        if selection.get("price_tag_text_normalized"):
            result["price_tag_text_normalized"] = selection["price_tag_text_normalized"]
        result["selection_reason"] = selection.get("reason")
        result["selection_confidence"] = selection.get("confidence")
    else:
        result["selection_reason"] = "Fallback selection based on the most complete candidate."
        result["selection_confidence"] = 0.35

    return result


def _format_price_for_tts(price) -> str:
    try:
        price_value = int(float(price))
    except (TypeError, ValueError):
        return f"{price} đồng"

    if price_value >= 1000 and price_value % 1000 == 0:
        return f"{price_value // 1000} nghìn đồng"

    return f"{price_value:,.0f}".replace(",", ".") + " đồng"


def _build_tts_text(result: Dict) -> str:
    parts = []

    product_name = result.get("product_name") or result.get("name")
    if product_name:
        parts.append(f"Sản phẩm {product_name}")

    if result.get("price") is not None:
        parts.append(f"giá {_format_price_for_tts(result['price'])}")

    if not parts:
        return ""

    return ", ".join(parts) + "."


class ShoppingAssistantInferenceService:
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or Path(__file__).resolve().parent
        _load_project_env(self.base_dir)

        self.weights_path = Path(os.getenv("YOLO_WEIGHTS_PATH", self.base_dir / "yolo" / "weights" / "best.pt"))
        self.confidence_threshold = float(os.getenv("AGENTIC_CONF_THRESHOLD", "0.1"))
        self.audio_dir = Path(os.getenv("AGENTIC_AUDIO_DIR", self.base_dir / "audio"))
        self.default_cropped_dir = Path(os.getenv("AGENTIC_CROPPED_DIR", self.base_dir / "cropped_tags"))

        self._ocr = None
        self._llm = None
        self._pipeline = None
        self._tts = None
        self._yolo_detector = None

    def _ensure_pipeline(self) -> None:
        if self._pipeline is not None:
            return

        try:
            from ocr.kreuzberg_extractor import KreuzbergFramework, KreuzbergOCRExtractor
            from ocr.llm_extractor import build_llm_extractor
            from ocr.pipeline import PriceTagPipeline
        except ImportError as exc:
            raise InferenceInitializationError(
                "Missing AI runtime dependency. Install `pip install -r ai-pipeline/requirements.txt` "
                "and `pip install -r ai-pipeline/ocr/requirements.txt`."
            ) from exc

        logger.info("Initializing OCR + LLM pipeline components...")
        self._ocr = KreuzbergOCRExtractor(
            framework=KreuzbergFramework(
                backend=os.getenv("OCR_BACKEND", "paddleocr"),
                language=os.getenv("OCR_LANGUAGE", "vi"),
            )
        )
        self._llm = build_llm_extractor(provider=os.getenv("LLM_PROVIDER"))
        self._pipeline = PriceTagPipeline(ocr=self._ocr, llm=self._llm, tts=None)

    def _get_tts(self):
        if self._tts is not None:
            return self._tts

        try:
            from tts.tts_engine import TTSEngine
        except ImportError as exc:
            raise InferenceInitializationError(
                "Missing TTS runtime dependency. Install `pip install -r ai-pipeline/requirements.txt`."
            ) from exc

        provider = os.getenv("TTS_PROVIDER", "vieneu")
        logger.info("Initializing TTS provider=%s", provider)
        self._tts = TTSEngine(provider=provider)
        return self._tts

    def _get_yolo_detector(self):
        if self._yolo_detector is not None:
            return self._yolo_detector

        try:
            from yolo_integration import PriceTagDetector
        except ImportError as exc:
            raise InferenceInitializationError(
                "Missing YOLO runtime dependency. Install `pip install -r ai-pipeline/requirements.txt`."
            ) from exc

        logger.info("Initializing YOLO detector from %s", self.weights_path)
        self._yolo_detector = PriceTagDetector(
            model_version=str(self.weights_path),
            confidence_threshold=self.confidence_threshold,
        )
        return self._yolo_detector

    async def _maybe_generate_audio(self, output_stem: str, result: Dict) -> Optional[str]:
        text = _build_tts_text(result)
        if not text:
            logger.warning("TTS skipped because selected result is empty.")
            return None

        tts = self._get_tts()
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        provider = os.getenv("TTS_PROVIDER", "vieneu").lower()
        suffix = ".wav" if provider == "vieneu" else ".mp3"
        output_path = self.audio_dir / f"{output_stem}{suffix}"
        generated_path = await tts.generate_speech_file_async(text, str(output_path))
        return str(generated_path) if generated_path else None

    async def infer_image(
        self,
        image_path: Path,
        *,
        options: Optional[InferenceOptions] = None,
        source_image: Optional[str] = None,
        crop_output_dir: Optional[Path] = None,
        keep_crops: bool = False,
    ) -> Dict:
        options = options or InferenceOptions()
        source_name = source_image or image_path.name

        if not image_path.exists():
            return {
                "ok": False,
                "message": f"Image not found: {image_path}",
                "source_image": source_name,
                "selected_result": None,
                "selection": None,
                "all_candidates": [],
                "audio_path": None,
                "backend_sync": None,
                "debug": {
                    "used_yolo": False,
                    "used_selection": False,
                    "num_candidates": 0,
                    "selection_enabled": options.enable_selection,
                    "yolo_requested": options.use_yolo,
                },
            }

        self._ensure_pipeline()

        temp_crop_dir: Optional[tempfile.TemporaryDirectory] = None
        targets = [image_path]
        yolo_requested = options.use_yolo
        yolo_applied = False
        yolo_note: Optional[str] = None

        try:
            if options.use_yolo:
                if not self.weights_path.exists():
                    yolo_note = f"YOLO weights not found at '{self.weights_path}'. Falling back to direct OCR mode."
                    logger.warning(yolo_note)
                else:
                    try:
                        detector = self._get_yolo_detector()
                        if crop_output_dir is not None:
                            target_crop_dir = crop_output_dir
                        elif keep_crops:
                            target_crop_dir = self.default_cropped_dir
                        else:
                            temp_crop_dir = tempfile.TemporaryDirectory(prefix="shopping-assistant-crops-")
                            target_crop_dir = Path(temp_crop_dir.name)

                        targets = detector.detect_and_crop(image_path, output_dir=target_crop_dir)
                        if targets:
                            yolo_applied = True
                        else:
                            yolo_note = (
                                f"No price tags detected in image {image_path.name}. "
                                "Falling back to direct OCR on the original image."
                            )
                            logger.warning(yolo_note)
                            targets = [image_path]
                    except Exception as exc:
                        yolo_note = f"YOLO detection failed: {exc}. Falling back to direct OCR mode."
                        logger.warning(yolo_note)
                        targets = [image_path]

            candidates: List[Dict] = []
            for idx, target in enumerate(targets, start=1):
                logger.info("Analyzing candidate #%s from %s", idx, target.name)
                result = await self._pipeline.run(target)
                candidates.append(
                    {
                        "candidate_id": idx,
                        "crop_name": target.name,
                        "crop_path": str(target),
                        "result": result,
                    }
                )

            viable_candidates = [
                candidate
                for candidate in candidates
                if _has_meaningful_result(candidate.get("result"))
            ]
            if not viable_candidates:
                return {
                    "ok": False,
                    "message": "OCR/LLM could not extract a meaningful structured result from the uploaded image.",
                    "source_image": source_name,
                    "selected_result": None,
                    "selection": None,
                    "all_candidates": [_sanitize_candidate(candidate) for candidate in candidates],
                    "audio_path": None,
                    "backend_sync": None,
                    "debug": {
                        "used_yolo": yolo_applied,
                        "used_selection": False,
                        "num_candidates": len(candidates),
                        "selection_enabled": options.enable_selection,
                        "yolo_requested": yolo_requested,
                        "yolo_note": yolo_note,
                    },
                }

            selection = None
            used_selection = False
            if options.enable_selection and len(viable_candidates) > 1 and hasattr(self._llm, "select_best_candidate"):
                selection = await self._llm.select_best_candidate(image_path, candidates)
                used_selection = selection is not None
            elif len(viable_candidates) == 1:
                only_candidate = viable_candidates[0]
                only_result = only_candidate["result"]
                selection = {
                    "selected_candidate_id": only_candidate["candidate_id"],
                    "selected_crop_name": only_candidate["crop_name"],
                    "product_name": only_result.get("name") or only_result.get("product_name"),
                    "product_name_source": f"candidate_{only_candidate['candidate_id']}",
                    "price": only_result.get("price"),
                    "category": only_result.get("category"),
                    "price_tag_text_normalized": only_result.get("price_tag_text_normalized"),
                    "reason": "Only one candidate was available.",
                    "confidence": 1.0,
                }

            final_result = _merge_selection(selection, candidates)
            if final_result is None:
                return {
                    "ok": False,
                    "message": "Could not determine a final product result from the uploaded image.",
                    "source_image": source_name,
                    "selected_result": None,
                    "selection": selection,
                    "all_candidates": [_sanitize_candidate(candidate) for candidate in candidates],
                    "audio_path": None,
                    "backend_sync": None,
                    "debug": {
                        "used_yolo": yolo_applied,
                        "used_selection": used_selection,
                        "num_candidates": len(candidates),
                        "selection_enabled": options.enable_selection,
                        "yolo_requested": yolo_requested,
                        "yolo_note": yolo_note,
                    },
                }

            audio_path = None
            if options.enable_tts:
                try:
                    audio_path = await self._maybe_generate_audio(image_path.stem, final_result)
                except Exception as exc:
                    logger.warning("TTS generation failed: %s", exc)

            backend_sync = None
            if options.enable_backend_sync:
                payload = build_scan_payload(
                    selected_result=final_result,
                    source_image=source_name,
                    image_base64=encode_image_path_to_data_url(image_path),
                    category=final_result.get("category"),
                )
                try:
                    backend_sync = await asyncio.to_thread(post_scan_payload, payload)
                except Exception as exc:
                    backend_sync = {"error": str(exc)}
                    logger.error("Failed to sync result to backend: %s", exc)

            return {
                "ok": True,
                "message": "Inference completed successfully.",
                "source_image": source_name,
                "selected_result": final_result,
                "selection": selection,
                "all_candidates": [_sanitize_candidate(candidate) for candidate in candidates],
                "audio_path": audio_path,
                "backend_sync": backend_sync,
                "debug": {
                    "used_yolo": yolo_applied,
                    "used_selection": used_selection,
                    "num_candidates": len(candidates),
                    "selection_enabled": options.enable_selection,
                    "yolo_requested": yolo_requested,
                    "yolo_note": yolo_note,
                },
            }
        except Exception as exc:
            logger.exception("Inference failed for %s", image_path)
            return {
                "ok": False,
                "message": f"Inference failed: {exc}",
                "source_image": source_name,
                "selected_result": None,
                "selection": None,
                "all_candidates": [],
                "audio_path": None,
                "backend_sync": None,
                "debug": {
                    "used_yolo": yolo_applied,
                    "used_selection": False,
                    "num_candidates": 0,
                    "selection_enabled": options.enable_selection,
                    "yolo_requested": yolo_requested,
                },
            }
        finally:
            if temp_crop_dir is not None:
                temp_crop_dir.cleanup()


def default_inference_options() -> InferenceOptions:
    return InferenceOptions(
        use_yolo=os.getenv("AGENTIC_USE_YOLO", "true").strip().lower() in {"1", "true", "yes", "on"},
        enable_selection=os.getenv("AGENTIC_ENABLE_SELECTION", "true").strip().lower() in {"1", "true", "yes", "on"},
        enable_tts=os.getenv("AGENTIC_ENABLE_TTS", "false").strip().lower() in {"1", "true", "yes", "on"},
        enable_backend_sync=backend_sync_enabled(default=False),
    )


def build_inference_service(base_dir: Optional[Path] = None) -> ShoppingAssistantInferenceService:
    return ShoppingAssistantInferenceService(base_dir=base_dir)
