import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("AgenticOCRRunner")


def _load_project_env(base_dir: Path) -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = base_dir.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _list_images(directory: Path) -> List[Path]:
    return sorted(
        path for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )


def _candidate_score(candidate: Dict) -> tuple:
    result = candidate.get("result") or {}
    return (
        result.get("price") is not None,
        result.get("name") is not None,
        len(result.get("raw_ocr_text") or ""),
    )


def _sanitize_candidate(candidate: Dict) -> Dict:
    result = candidate.get("result") or {}
    return {
        "candidate_id": candidate.get("candidate_id"),
        "crop_name": candidate.get("crop_name"),
        "crop_path": candidate.get("crop_path"),
        "name": result.get("name"),
        "price": result.get("price"),
        "category": result.get("category"),
        "price_tag_text_normalized": result.get("price_tag_text_normalized"),
        "raw_ocr_text": result.get("raw_ocr_text"),
    }


def _choose_candidate_fallback(candidates: List[Dict]) -> Optional[Dict]:
    viable_candidates = [candidate for candidate in candidates if candidate.get("result")]
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


async def _save_tts_audio(tts, audio_dir: Path, output_stem: str, result: Dict) -> Optional[Path]:
    text = _build_tts_text(result)
    if not text:
        logger.warning("TTS skipped because selected result is empty.")
        return None

    logger.info("FINAL TTS text: %s", text)
    audio_bytes = await tts.synthesize(text)
    if not audio_bytes:
        logger.error("TTS returned empty audio bytes.")
        return None

    audio_dir.mkdir(parents=True, exist_ok=True)
    output_path = audio_dir / f"{output_stem}.wav"
    output_path.write_bytes(audio_bytes)
    logger.info("Saved final audio to %s", output_path)
    return output_path


async def main():
    base_dir = Path(__file__).resolve().parent
    _load_project_env(base_dir)

    try:
        from backend_client import (
            backend_sync_enabled,
            build_scan_payload,
            encode_image_path_to_data_url,
            post_scan_payload,
        )
        from ocr.kreuzberg_extractor import KreuzbergFramework, KreuzbergOCRExtractor
        from ocr.llm_extractor import build_llm_extractor
        from ocr.pipeline import PriceTagPipeline
        from yolo_integration import PriceTagDetector
    except ImportError as exc:
        logger.error("Missing runtime dependency: %s", exc)
        logger.info("Install dependencies first with `pip install -r requirements.txt` and `pip install -r ocr/requirements.txt`.")
        return

    sample_dir = Path(os.getenv("AGENTIC_SAMPLE_DIR", base_dir / "sample_docs"))
    cropped_dir = Path(os.getenv("AGENTIC_CROPPED_DIR", base_dir / "cropped_tags"))
    output_path = Path(os.getenv("AGENTIC_OUTPUT_JSON", base_dir / "tests" / "output.json"))
    audio_dir = Path(os.getenv("AGENTIC_AUDIO_DIR", base_dir / "audio"))
    weights_path = Path(os.getenv("YOLO_WEIGHTS_PATH", base_dir / "yolo" / "weights" / "best.pt"))
    confidence_threshold = float(os.getenv("AGENTIC_CONF_THRESHOLD", "0.1"))
    use_yolo = _is_truthy(os.getenv("AGENTIC_USE_YOLO"), default=weights_path.exists())
    enable_tts = _is_truthy(os.getenv("AGENTIC_ENABLE_TTS"), default=True)
    enable_selection = _is_truthy(os.getenv("AGENTIC_ENABLE_SELECTION"), default=True)
    enable_backend_sync = backend_sync_enabled(default=False)

    sample_dir.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    image_files = _list_images(sample_dir)
    if not image_files:
        logger.warning(f"No images found in '{sample_dir}'.")
        logger.info("Place one or more .jpg/.jpeg/.png/.webp files there, then rerun.")
        return

    logger.info("Initializing OCR, LLM, and TTS components...")
    ocr = KreuzbergOCRExtractor(
        framework=KreuzbergFramework(
            backend=os.getenv("OCR_BACKEND", "paddleocr"),
            language=os.getenv("OCR_LANGUAGE", "vi"),
        )
    )
    llm = build_llm_extractor()
    tts = None
    if enable_tts:
        try:
            from tts.vieneu_tts import VieneuTTS
            tts = VieneuTTS()
        except ImportError as exc:
            logger.warning("TTS disabled because dependency is missing: %s", exc)

    # Run OCR + extraction per crop first, then synthesize only for the final selected result.
    pipeline = PriceTagPipeline(ocr=ocr, llm=llm, tts=None)

    yolo_detector = None
    if use_yolo:
        if weights_path.exists():
            yolo_detector = PriceTagDetector(
                model_version=str(weights_path),
                confidence_threshold=confidence_threshold,
            )
        else:
            logger.warning(f"YOLO weights not found at '{weights_path}'. Falling back to direct OCR mode.")
            use_yolo = False

    all_results: Dict[str, Dict] = {}

    try:
        for img_file in image_files:
            logger.info("")
            logger.info("=" * 60)
            logger.info(f"PROCESSING IMAGE: {img_file.name}")
            logger.info("=" * 60)

            targets = [img_file]
            if use_yolo and yolo_detector is not None:
                targets = yolo_detector.detect_and_crop(img_file, output_dir=cropped_dir)
                if not targets:
                    logger.warning(
                        "No price tags detected in image %s. Falling back to direct OCR on original image.",
                        img_file.name,
                    )
                    targets = [img_file]

            candidates: List[Dict] = []
            for idx, target in enumerate(targets, start=1):
                logger.info("--- Analyzing Candidate #%s (%s) ---", idx, target.name)
                result = await pipeline.run(target)
                candidate = {
                    "candidate_id": idx,
                    "crop_name": target.name,
                    "crop_path": str(target),
                    "result": result,
                }
                candidates.append(candidate)

                if result:
                    logger.info(
                        "Candidate #%s extracted: Item=%s, Price=%s",
                        idx,
                        result.get("name") or result.get("product_name"),
                        result.get("price"),
                    )
                else:
                    logger.warning("Candidate #%s produced no structured result.", idx)

            selection = None
            if enable_selection and len(candidates) > 1 and hasattr(llm, "select_best_candidate"):
                selection = await llm.select_best_candidate(img_file, candidates)
            elif len(candidates) == 1 and candidates[0].get("result"):
                only_result = candidates[0]["result"]
                selection = {
                    "selected_candidate_id": candidates[0]["candidate_id"],
                    "selected_crop_name": candidates[0]["crop_name"],
                    "product_name": only_result.get("name"),
                    "product_name_source": f"candidate_{candidates[0]['candidate_id']}",
                    "price": only_result.get("price"),
                    "category": only_result.get("category"),
                    "price_tag_text_normalized": only_result.get("price_tag_text_normalized"),
                    "reason": "Only one candidate was available.",
                    "confidence": 1.0,
                }

            final_result = _merge_selection(selection, candidates)
            audio_path = None
            backend_sync = None
            if final_result:
                logger.info(
                    "SELECTED RESULT: Item=%s, Price=%s, Crop=%s",
                    final_result.get("product_name") or final_result.get("name"),
                    final_result.get("price"),
                    final_result.get("selected_crop_name"),
                )

                if tts is not None:
                    audio_path = await _save_tts_audio(tts, audio_dir, img_file.stem, final_result)

                if enable_backend_sync:
                    payload = build_scan_payload(
                        selected_result=final_result,
                        source_image=img_file.name,
                        image_base64=encode_image_path_to_data_url(img_file),
                        category=final_result.get("category"),
                    )
                    try:
                        backend_sync = await asyncio.to_thread(post_scan_payload, payload)
                        logger.info("Synced result to backend: %s", backend_sync)
                    except Exception as exc:
                        backend_sync = {"error": str(exc)}
                        logger.error("Failed to sync result to backend: %s", exc)
            else:
                logger.error("Failed to determine a final result for %s", img_file.name)

            all_results[img_file.name] = {
                "source_image": img_file.name,
                "selected_result": final_result,
                "selection": selection,
                "all_candidates": [_sanitize_candidate(candidate) for candidate in candidates],
                "audio_path": str(audio_path) if audio_path else None,
                "backend_sync": backend_sync,
            }

        output_path.write_text(
            json.dumps(all_results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Saved aggregated output to %s", output_path)
    finally:
        if tts is not None:
            tts.close()


if __name__ == "__main__":
    asyncio.run(main())
