import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

from llm.extractor import LLMExtractor


logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("CategoryBackfill")


def _load_project_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)


def _backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def _fetch_logs(limit: int = 200) -> List[Dict]:
    all_logs: List[Dict] = []
    offset = 0

    while True:
        response = requests.get(
            f"{_backend_url()}/api/logs",
            params={"limit": min(limit, 100), "offset": offset},
            timeout=int(os.getenv("BACKFILL_TIMEOUT_SECONDS", "30")),
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break

        all_logs.extend(batch)
        offset += len(batch)
        if len(all_logs) >= limit or len(batch) < 100:
            break

    return all_logs[:limit]


def _split_data_url(value: Optional[str]) -> Tuple[Optional[str], str]:
    if not value:
        return None, "image/png"
    if value.startswith("data:") and ";base64," in value:
        header, encoded = value.split(";base64,", 1)
        return encoded, header.removeprefix("data:")
    return value, "image/png"


def _build_context(log: Dict) -> str:
    parts = []

    if log.get("detected_object"):
        parts.append(f"Tên sản phẩm hiện có: {log['detected_object']}")
    if log.get("price_tag_text_normalized"):
        parts.append(f"Nội dung price tag: {log['price_tag_text_normalized']}")
    elif log.get("ocr_text"):
        parts.append(f"OCR text: {log['ocr_text']}")
    if log.get("price"):
        parts.append(f"Giá hiện có: {log['price']}")

    return "\n".join(parts)


def _update_log_category(log_id: str, category: str) -> Dict:
    response = requests.put(
        f"{_backend_url()}/api/logs/{log_id}",
        json={"category": category},
        timeout=int(os.getenv("BACKFILL_TIMEOUT_SECONDS", "30")),
    )
    response.raise_for_status()
    return response.json()


def main():
    _load_project_env()

    limit = int(os.getenv("BACKFILL_LIMIT", "200"))
    force_reclassify = os.getenv("BACKFILL_FORCE_RECLASSIFY", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    extractor = LLMExtractor(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        api_key=os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or os.getenv("ALIBABA_API_KEY"),
        model=os.getenv("LLM_MODEL"),
        base_url=os.getenv("LLM_BASE_URL"),
        timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
    )

    logs = _fetch_logs(limit=limit)
    targets = [
        log for log in logs
        if force_reclassify or not (log.get("category") or "").strip()
    ]

    if not targets:
        logger.info("No logs need category backfill.")
        return

    logger.info("Found %s logs to classify.", len(targets))

    for log in targets:
        image_base64, image_mime_type = _split_data_url(log.get("image_base64"))
        context = _build_context(log)
        try:
            result = extractor.extract(
                ocr_text=context,
                detected_object=log.get("detected_object") or "",
                image_base64=image_base64,
                image_mime_type=image_mime_type,
            )
        except Exception as exc:
            logger.warning(
                "Primary classification failed for %s (%s). Retrying without image. Error: %s",
                log.get("log_id"),
                log.get("detected_object"),
                exc,
            )
            try:
                result = extractor.extract(
                    ocr_text=context,
                    detected_object=log.get("detected_object") or "",
                    image_base64=None,
                    image_mime_type="image/png",
                )
            except Exception as retry_exc:
                logger.warning(
                    "Retry without image also failed for %s (%s). Falling back to 'other'. Error: %s",
                    log.get("log_id"),
                    log.get("detected_object"),
                    retry_exc,
                )
                result = None

        category = (result.category if result else None) or "other"
        updated = _update_log_category(log["log_id"], category)
        logger.info(
            "Updated %s | %s -> %s",
            updated["log_id"],
            updated["detected_object"],
            updated.get("category"),
        )


if __name__ == "__main__":
    main()
