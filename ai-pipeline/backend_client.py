import base64
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def backend_sync_enabled(default: bool = False) -> bool:
    return _is_truthy(os.getenv("ENABLE_BACKEND_SYNC"), default=default)


def build_scan_api_url() -> str:
    explicit_url = os.getenv("BACKEND_SCAN_API_URL")
    if explicit_url:
        return explicit_url.rstrip("/")

    internal_hostport = os.getenv("BACKEND_HOSTPORT")
    if internal_hostport:
        return f"http://{internal_hostport.rstrip('/')}/api/scan"

    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    return f"{backend_url}/api/scan"


def encode_image_path_to_data_url(image_path: Path) -> Optional[str]:
    if not image_path.exists():
        return None

    suffix = image_path.suffix.lower()
    mime_type = "image/jpeg"
    if suffix == ".png":
        mime_type = "image/png"
    elif suffix == ".webp":
        mime_type = "image/webp"

    image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return f"data:{mime_type};base64,{image_base64}"


def build_scan_payload(
    *,
    selected_result: Dict,
    source_image: Optional[str] = None,
    image_base64: Optional[str] = None,
    category: Optional[str] = None,
    status: str = "success",
    warning_flag: Optional[bool] = None,
    warning_reason: Optional[str] = None,
) -> Dict:
    confidence = selected_result.get("selection_confidence")
    if confidence is None:
        confidence = selected_result.get("confidence")

    if category is None:
        category = selected_result.get("category")

    if warning_flag is None:
        warning_flag = status != "success" or (
            confidence is not None and float(confidence) < float(os.getenv("BACKEND_WARNING_CONFIDENCE", "0.7"))
        )

    if warning_reason is None and warning_flag:
        if status != "success":
            warning_reason = "Pipeline xử lý lỗi hoặc không hoàn tất"
        elif confidence is not None and float(confidence) < float(os.getenv("BACKEND_WARNING_CONFIDENCE", "0.7")):
            warning_reason = f"Độ tin cậy bước chọn thấp ({float(confidence):.0%})"

    return {
        "timestamp": datetime.now().isoformat(),
        "source_image": source_image,
        "image_base64": image_base64,
        "selected_result": {
            "name": selected_result.get("name"),
            "product_name": selected_result.get("product_name") or selected_result.get("name"),
            "price": selected_result.get("price"),
            "raw_ocr_text": selected_result.get("raw_ocr_text"),
            "price_tag_text_normalized": selected_result.get("price_tag_text_normalized"),
            "product_name_source": selected_result.get("product_name_source"),
            "selected_crop_name": selected_result.get("selected_crop_name"),
            "selection_reason": selected_result.get("selection_reason"),
            "category": selected_result.get("category"),
            "selection_confidence": confidence,
        },
        "status": status,
        "warning_flag": warning_flag,
        "warning_reason": warning_reason,
        "category": category,
    }


def post_scan_payload(payload: Dict, scan_api_url: Optional[str] = None, timeout_seconds: Optional[int] = None) -> Dict:
    response = requests.post(
        scan_api_url or build_scan_api_url(),
        json=payload,
        timeout=timeout_seconds or int(os.getenv("BACKEND_SYNC_TIMEOUT_SECONDS", "30")),
    )
    response.raise_for_status()
    return response.json()
