import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import cv2


logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("LiveWebcamRunner")


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


def _open_webcam(index: int):
    if os.name == "nt":
        cap = cv2.VideoCapture(index, getattr(cv2, "CAP_DSHOW", 0))
    else:
        cap = cv2.VideoCapture(index)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return cap


def _capture_filename(prefix: str = "webcam") -> str:
    return datetime.now().strftime(f"{prefix}_%Y%m%d_%H%M%S_%f")[:-3] + ".jpg"


def _save_capture(frame, capture_dir: Path, filename: str) -> Path:
    capture_dir.mkdir(parents=True, exist_ok=True)
    capture_path = capture_dir / filename
    cv2.imwrite(str(capture_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    return capture_path


def _format_price(price) -> str:
    if price is None:
        return "N/A"
    try:
        return f"{int(float(price)):,.0f} VND"
    except (TypeError, ValueError):
        return str(price)


def _selection_status(result: Optional[Dict]) -> str:
    if not result:
        return "No result yet"

    selected = result.get("selected_output") or {}
    name = selected.get("product_name") or selected.get("name") or "Unknown"
    category = selected.get("category") or "uncategorized"
    price = _format_price(selected.get("price"))
    return f"{name} | {category} | {price}"


def _sync_status(result: Optional[Dict]) -> str:
    if not result:
        return "Waiting for first capture"

    sync = (result.get("steps") or {}).get("backend_sync")
    if not sync:
        return "Backend sync disabled"
    if sync.get("error"):
        return f"Sync error: {sync['error']}"
    return f"Synced log_id={sync.get('log_id', 'ok')}"


def _draw_overlay(frame, *, auto_mode: bool, auto_interval: float, next_in: Optional[float], last_result: Optional[Dict]):
    overlay_lines = [
        "SPACE: capture now | A: toggle auto | Q: quit",
        f"Auto capture: {'ON' if auto_mode else 'OFF'}"
        + (f" ({max(next_in or 0.0, 0.0):.1f}s)" if auto_mode and auto_interval > 0 else ""),
        _selection_status(last_result),
        _sync_status(last_result),
    ]

    x = 12
    y = 24
    line_height = 24
    color = (235, 235, 235)

    cv2.rectangle(frame, (8, 8), (frame.shape[1] - 8, 8 + line_height * len(overlay_lines) + 16), (18, 18, 18), -1)
    cv2.rectangle(frame, (8, 8), (frame.shape[1] - 8, 8 + line_height * len(overlay_lines) + 16), (70, 70, 70), 1)

    for idx, line in enumerate(overlay_lines):
        cv2.putText(
            frame,
            line,
            (x, y + idx * line_height),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            1,
            cv2.LINE_AA,
        )


async def _process_capture(pipeline, frame, capture_dir: Path) -> tuple[Path, Dict]:
    filename = _capture_filename()
    capture_path = _save_capture(frame, capture_dir, filename)
    result = await pipeline.process_image(frame, source_image=filename)
    return capture_path, result


def main():
    base_dir = Path(__file__).resolve().parent
    _load_project_env(base_dir)

    os.environ.setdefault("ENABLE_BACKEND_SYNC", "true")
    os.environ.setdefault("BACKEND_URL", "http://127.0.0.1:8000")

    try:
        from pipeline import ShoppingAssistantPipeline
    except ImportError as exc:
        logger.error("Failed to import ShoppingAssistantPipeline: %s", exc)
        logger.info("Install dependencies first with `pip install -r requirements.txt` and `pip install -r ocr/requirements.txt`.")
        return

    webcam_index = int(os.getenv("WEBCAM_INDEX", "0"))
    frame_width = int(os.getenv("WEBCAM_FRAME_WIDTH", "1280"))
    frame_height = int(os.getenv("WEBCAM_FRAME_HEIGHT", "720"))
    auto_interval = float(os.getenv("WEBCAM_AUTO_INTERVAL_SECONDS", "0"))
    auto_mode = _is_truthy(os.getenv("WEBCAM_AUTO_START"), default=False) and auto_interval > 0
    capture_dir = Path(os.getenv("WEBCAM_CAPTURE_DIR", base_dir / "captures"))

    logger.info("Loading live webcam pipeline...")
    pipeline = ShoppingAssistantPipeline(
        config={
            "enable_backend_sync": _is_truthy(os.getenv("ENABLE_BACKEND_SYNC"), default=True),
        }
    )

    cap = _open_webcam(webcam_index)
    if not cap.isOpened():
        logger.error("Could not open webcam index %s", webcam_index)
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, frame_height)

    window_name = "Shopping Assistant Live Webcam"
    last_result: Optional[Dict] = None
    next_auto_capture_at = time.monotonic() + auto_interval if auto_mode and auto_interval > 0 else None

    logger.info("Webcam ready. Controls: SPACE=capture | A=toggle auto | Q=quit")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                logger.warning("Failed to read frame from webcam.")
                time.sleep(0.2)
                continue

            display = frame.copy()
            next_in = None
            if auto_mode and auto_interval > 0 and next_auto_capture_at is not None:
                next_in = next_auto_capture_at - time.monotonic()
            _draw_overlay(
                display,
                auto_mode=auto_mode,
                auto_interval=auto_interval,
                next_in=next_in,
                last_result=last_result,
            )
            cv2.imshow(window_name, display)

            key = cv2.waitKey(1) & 0xFF
            should_capture = False

            if key in {ord("q"), 27}:
                break
            if key == ord(" "):
                should_capture = True
            elif key in {ord("a"), ord("A")} and auto_interval > 0:
                auto_mode = not auto_mode
                next_auto_capture_at = time.monotonic() + auto_interval if auto_mode else None
                logger.info("Auto capture %s", "enabled" if auto_mode else "disabled")
            elif auto_mode and auto_interval > 0 and next_auto_capture_at is not None and time.monotonic() >= next_auto_capture_at:
                should_capture = True

            if not should_capture:
                continue

            processing_frame = frame.copy()
            cv2.putText(
                processing_frame,
                "Processing capture... please wait",
                (20, processing_frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(window_name, processing_frame)
            cv2.waitKey(1)

            capture_path, result = asyncio.run(_process_capture(pipeline, frame.copy(), capture_dir))
            last_result = result
            next_auto_capture_at = time.monotonic() + auto_interval if auto_mode and auto_interval > 0 else None

            if result.get("success"):
                selected = result.get("selected_output") or {}
                logger.info(
                    "Capture processed | file=%s | product=%s | category=%s | price=%s",
                    capture_path.name,
                    selected.get("product_name") or selected.get("name"),
                    selected.get("category"),
                    _format_price(selected.get("price")),
                )
            else:
                logger.error("Capture failed | file=%s | error=%s", capture_path.name, result.get("error"))
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
