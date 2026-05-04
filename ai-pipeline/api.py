import logging
import os
import re
import tempfile
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Optional

import uvicorn
from fastapi import FastAPI, File, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from inference_service import (
    InferenceInitializationError,
    InferenceOptions,
    build_inference_service,
)

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("InferenceAPI")

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
CONTENT_TYPE_TO_SUFFIX = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


class InferDebugPayload(BaseModel):
    used_yolo: bool = Field(..., description="True nếu YOLO crop thực sự được áp dụng.")
    used_selection: bool = Field(..., description="True nếu bước chọn candidate thực sự được gọi.")
    num_candidates: int = Field(..., description="Số candidate đã phân tích.")
    selection_enabled: bool = Field(..., description="Flag đầu vào cho bước chọn candidate.")
    yolo_requested: Optional[bool] = Field(default=None, description="Flag yêu cầu YOLO từ request.")
    yolo_note: Optional[str] = Field(default=None, description="Thông tin fallback/debug cho YOLO.")


class InferSuccessResponse(BaseModel):
    ok: bool = Field(True)
    message: str = Field(..., description="Thông báo ngắn gọn về kết quả xử lý.")
    source_image: Optional[str] = Field(default=None, description="Tên file nguồn đã xử lý.")
    product_name: Optional[str] = Field(default=None, description="Tên sản phẩm cuối cùng.")
    price_text: Optional[str] = Field(default=None, description="Giá đã format để hiển thị.")
    normalized_price: Optional[str] = Field(default=None, description="Giá chuẩn hóa chỉ gồm chữ số.")
    category: Optional[str] = Field(default=None, description="Nhóm sản phẩm cuối cùng.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Độ tin cậy của kết quả cuối.")
    raw_text: Optional[str] = Field(default=None, description="OCR text thô của candidate được chọn.")
    audio_path: Optional[str] = Field(default=None, description="Đường dẫn audio nếu bật TTS.")
    debug: InferDebugPayload


class InferErrorResponse(BaseModel):
    ok: bool = Field(False)
    message: str = Field(..., description="Mô tả lỗi rõ ràng, ổn định cho client.")
    debug: Optional[InferDebugPayload] = None


app = FastAPI(
    title="Shopping Assistant Inference API",
    description="HTTP inference service for uploaded price-tag images.",
    version="1.0.0",
)


@lru_cache(maxsize=1)
def _get_inference_service():
    return build_inference_service(base_dir=Path(__file__).resolve().parent)


def _sanitize_filename(filename: Optional[str], suffix: str) -> str:
    stem = Path(filename or "upload").stem
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_") or "upload"
    return f"{safe_stem}{suffix}"


def _is_truthy(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_upload_suffix(upload: UploadFile) -> Optional[str]:
    filename_suffix = Path(upload.filename or "").suffix.lower()
    if filename_suffix in ALLOWED_SUFFIXES:
        return filename_suffix
    return CONTENT_TYPE_TO_SUFFIX.get((upload.content_type or "").lower())


def _format_price_text(price) -> Optional[str]:
    if price is None:
        return None
    try:
        price_value = int(float(price))
    except (TypeError, ValueError):
        return str(price)
    return f"{price_value:,.0f} VND"


def _normalized_price(price) -> Optional[str]:
    if price is None:
        return None
    try:
        return str(int(float(price)))
    except (TypeError, ValueError):
        digits_only = "".join(ch for ch in str(price) if ch.isdigit())
        return digits_only or None


def _build_success_response(result: dict) -> InferSuccessResponse:
    selected = result.get("selected_result") or {}
    debug = InferDebugPayload(**(result.get("debug") or {}))
    confidence = selected.get("selection_confidence")
    if confidence is None:
        confidence = 0.0

    return InferSuccessResponse(
        ok=True,
        message=result.get("message", "Inference completed successfully."),
        source_image=result.get("source_image"),
        product_name=selected.get("product_name") or selected.get("name"),
        price_text=_format_price_text(selected.get("price")),
        normalized_price=_normalized_price(selected.get("price")),
        category=selected.get("category"),
        confidence=float(confidence),
        raw_text=selected.get("raw_ocr_text"),
        audio_path=result.get("audio_path"),
        debug=debug,
    )


def _build_error_response(result: dict) -> InferErrorResponse:
    debug_payload = result.get("debug")
    debug = InferDebugPayload(**debug_payload) if debug_payload else None
    return InferErrorResponse(
        ok=False,
        message=result.get("message", "Inference failed."),
        debug=debug,
    )


def _debug_upload_dir() -> Path:
    configured = os.getenv("INFER_DEBUG_IMAGE_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent / "debug_uploads"


def _debug_upload_enabled() -> bool:
    return _is_truthy(os.getenv("INFER_SAVE_DEBUG_UPLOADS"), default=True)


def _debug_max_files() -> int:
    try:
        return max(1, int(os.getenv("INFER_DEBUG_MAX_FILES", "50")))
    except ValueError:
        return 50


def _save_debug_upload(content: bytes, safe_filename: str, suffix: str) -> Optional[Path]:
    if not _debug_upload_enabled():
        return None

    debug_dir = _debug_upload_dir()
    debug_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(safe_filename).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    saved_path = debug_dir / f"{timestamp}_{stem}{suffix}"
    saved_path.write_bytes(content)

    latest_path = debug_dir / f"latest{suffix}"
    latest_path.write_bytes(content)
    (debug_dir / "latest_name.txt").write_text(saved_path.name, encoding="utf-8")

    _prune_debug_uploads(debug_dir, keep=_debug_max_files())
    return saved_path


def _prune_debug_uploads(debug_dir: Path, *, keep: int) -> None:
    files = sorted(
        [
            path for path in debug_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() in ALLOWED_SUFFIXES
            and not path.name.startswith("latest")
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for stale_path in files[keep:]:
        stale_path.unlink(missing_ok=True)


def _latest_debug_upload() -> Optional[Path]:
    debug_dir = _debug_upload_dir()
    if not debug_dir.exists():
        return None

    latest_name_path = debug_dir / "latest_name.txt"
    if latest_name_path.exists():
        candidate_name = latest_name_path.read_text(encoding="utf-8").strip()
        candidate = debug_dir / candidate_name
        if candidate.exists():
            return candidate

    files = sorted(
        [path for path in debug_dir.iterdir() if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def _list_debug_uploads(limit: int = 20) -> list[dict]:
    debug_dir = _debug_upload_dir()
    if not debug_dir.exists():
        return []

    items = sorted(
        [
            path for path in debug_dir.iterdir()
            if path.is_file()
            and path.suffix.lower() in ALLOWED_SUFFIXES
            and not path.name.startswith("latest")
        ],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    payload = []
    for path in items[:limit]:
        stat = path.stat()
        payload.append(
            {
                "name": path.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": f"/debug/uploads/{path.name}",
            }
        )
    return payload


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


@app.get("/debug/uploads")
async def list_debug_uploads():
    return {
        "enabled": _debug_upload_enabled(),
        "directory": str(_debug_upload_dir()),
        "files": _list_debug_uploads(),
    }


@app.get("/debug/uploads/latest")
async def get_latest_debug_upload():
    latest = _latest_debug_upload()
    if latest is None:
        return JSONResponse(status_code=404, content={"ok": False, "message": "No debug upload available yet."})
    return FileResponse(latest)


@app.get("/debug/uploads/{filename}")
async def get_debug_upload(filename: str):
    safe_name = Path(filename).name
    if safe_name != filename:
        return JSONResponse(status_code=400, content={"ok": False, "message": "Invalid filename."})

    target = _debug_upload_dir() / safe_name
    if not target.exists() or target.suffix.lower() not in ALLOWED_SUFFIXES:
        return JSONResponse(status_code=404, content={"ok": False, "message": "Debug upload not found."})
    return FileResponse(target)


@app.get("/debug/view", response_class=HTMLResponse)
async def debug_view():
    latest = _latest_debug_upload()
    latest_name = latest.name if latest else "No image yet"
    latest_src = ""
    if latest:
        latest_src = f"/debug/uploads/latest?t={datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="3">
  <title>Pi Upload Debug View</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      background: #111827;
      color: #f3f4f6;
      margin: 0;
      padding: 24px;
    }}
    .wrap {{
      max-width: 960px;
      margin: 0 auto;
    }}
    .meta {{
      margin-bottom: 16px;
      color: #cbd5e1;
    }}
    img {{
      max-width: 100%;
      height: auto;
      border-radius: 12px;
      border: 1px solid #374151;
      background: #000;
    }}
    a {{
      color: #93c5fd;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Pi Upload Debug View</h1>
    <div class="meta">Auto refresh mỗi 3 giây.</div>
    <div class="meta">Latest file: {latest_name}</div>
    <div class="meta">JSON list: <a href="/debug/uploads">/debug/uploads</a></div>
    {"<img src='" + latest_src + "' alt='latest upload'>" if latest else "<p>Chưa có ảnh nào được upload.</p>"}
  </div>
</body>
</html>"""
    return HTMLResponse(html)


@app.post("/infer", response_model=InferSuccessResponse | InferErrorResponse)
async def infer_image(
    file: Annotated[UploadFile, File(description="Ảnh chụp từ gateway/ESP32-CAM")],
    use_yolo: bool = Query(True, description="Bật YOLO crop trước khi OCR."),
    enable_selection: bool = Query(True, description="Bật bước chọn candidate tốt nhất."),
    enable_tts: bool = Query(False, description="Bật tạo file audio trả về đường dẫn audio_path."),
):
    suffix = _resolve_upload_suffix(file)
    if suffix is None:
        return JSONResponse(
            status_code=400,
            content=InferErrorResponse(
                ok=False,
                message="Unsupported file type. Allowed: .jpg, .jpeg, .png, .webp",
            ).model_dump(),
        )

    temp_root_env = os.getenv("INFER_UPLOAD_TMP_DIR")
    temp_root = Path(temp_root_env) if temp_root_env else None
    if temp_root is not None:
        temp_root.mkdir(parents=True, exist_ok=True)

    try:
        service = _get_inference_service()
    except InferenceInitializationError as exc:
        logger.exception("Inference service initialization failed.")
        return JSONResponse(
            status_code=500,
            content=InferErrorResponse(ok=False, message=str(exc)).model_dump(),
        )

    try:
        with tempfile.TemporaryDirectory(prefix="shopping-assistant-upload-", dir=temp_root) as temp_dir:
            safe_filename = _sanitize_filename(file.filename, suffix)
            upload_path = Path(temp_dir) / safe_filename
            content = await file.read()
            if not content:
                return JSONResponse(
                    status_code=400,
                    content=InferErrorResponse(ok=False, message="Uploaded file is empty.").model_dump(),
                )

            upload_path.write_bytes(content)
            debug_upload_path = _save_debug_upload(content, safe_filename, suffix)
            if debug_upload_path is not None:
                logger.info("Saved debug upload to %s", debug_upload_path)

            result = await service.infer_image(
                upload_path,
                options=InferenceOptions(
                    use_yolo=use_yolo,
                    enable_selection=enable_selection,
                    enable_tts=enable_tts,
                    enable_backend_sync=False,
                ),
                source_image=safe_filename,
            )
    except InferenceInitializationError as exc:
        logger.error("Inference runtime is not available: %s", exc)
        return JSONResponse(
            status_code=500,
            content=InferErrorResponse(ok=False, message=str(exc)).model_dump(),
        )
    except Exception as exc:
        logger.exception("Unhandled /infer error for file=%s", file.filename)
        return JSONResponse(
            status_code=500,
            content=InferErrorResponse(ok=False, message=f"Unhandled inference error: {exc}").model_dump(),
        )
    finally:
        await file.close()

    if not result.get("ok"):
        return JSONResponse(status_code=200, content=_build_error_response(result).model_dump())

    return _build_success_response(result)


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8001, reload=True)
