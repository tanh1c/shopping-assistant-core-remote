"""FastAPI application — serves both JSON API and HTML dashboard."""

from collections import deque
from datetime import datetime
from pathlib import Path
import re
import subprocess
import sys
import threading

from fastapi import FastAPI, Request, Query, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

from app.database import init_db, insert_log, get_logs, get_log_by_id, delete_log, update_log, get_stats, get_warning_logs
from app.models import (
    DebuggerAgenticOcrStatus,
    DebuggerAgenticOcrRunRequest,
    DebuggerSampleDoc,
    DebuggerUploadResponse,
    ReferencePriceCategorySummary,
    ReferencePriceImportResponse,
    ReferencePriceListResponse,
    ReferencePriceResponse,
    ReferencePriceSuggestion,
    ScanRequest,
    LogResponse,
    StatsResponse,
    UpdateLogRequest,
)
from app.mock_data import seed_database
from app.reference_prices import (
    count_reference_prices_filtered,
    get_reference_price_by_id,
    get_reference_prices,
    hydrate_reference_price_suggestion,
    import_reference_prices_from_csv,
    list_reference_price_categories,
    suggest_reference_price,
)

# ─── App Setup ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = Path(BASE_DIR).parent
ALLOWED_DEBUGGER_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
DEBUGGER_MAX_LOG_LINES = 250

_agentic_ocr_lock = threading.Lock()
_agentic_ocr_logs: deque[str] = deque(maxlen=DEBUGGER_MAX_LOG_LINES)
_agentic_ocr_status = {
    "status": "idle",
    "is_running": False,
    "message": "Chưa chạy run_agentic_ocr.py từ web.",
    "started_at": None,
    "finished_at": None,
    "exit_code": None,
    "pid": None,
    "command": [],
    "workdir": None,
    "python_executable": None,
    "runner_script": None,
    "output_json_path": None,
    "output_json_exists": False,
    "use_yolo": True,
    "enable_selection": True,
    "enable_tts": True,
}

app = FastAPI(
    title="Shopping Monitor API",
    description="API ghi nhận hoạt động mua sắm cho người khiếm thị",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (optional, only if directory exists)
static_dir = os.path.join(BASE_DIR, "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Jinja2 templates (optional, only if directory exists)
templates_dir = os.path.join(BASE_DIR, "templates")
templates = None
if os.path.isdir(templates_dir):
    templates = Jinja2Templates(directory=templates_dir)


# ─── Startup Event ───────────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()
    if _is_truthy(os.getenv("AUTO_IMPORT_REFERENCE_PRICES"), default=True):
        import_result = import_reference_prices_from_csv()
        if import_result["ok"]:
            print(
                "✓ Reference prices ready: "
                f"{import_result['total_rows_in_db']} rows "
                f"from {Path(import_result['csv_path']).name}"
            )
        else:
            print(f"! Reference price import skipped: {import_result['message']}")

    if _is_truthy(os.getenv("SEED_MOCK_DATA"), default=False):
        seeded = seed_database()
        if seeded:
            print("✓ Database initialized with mock records")
        else:
            print("✓ Database already has data, skipping mock seed")
    else:
        print("✓ Database initialized without mock seed")


# ═══════════════════════════════════════════════════════════════
#  HTML Page Routes (Dashboard)
# ═══════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Render main dashboard page."""
    logs = get_logs(limit=50)
    stats = get_stats()
    warnings = get_warning_logs()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "logs": logs,
        "stats": stats,
        "warnings": warnings,
        "active_page": "dashboard",
    })


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """Render history page with all logs."""
    logs = get_logs(limit=100)
    return templates.TemplateResponse("history.html", {
        "request": request,
        "logs": logs,
        "active_page": "history",
    })


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Render analytics page with charts and stats."""
    stats = get_stats()
    warnings = get_warning_logs()
    logs = get_logs(limit=100)

    # Category breakdown
    cat_colors = {
        "dairy": "#2563EB", "beverage": "#0891B2", "snack": "#D97706",
        "bakery": "#C4A77D", "condiment": "#7C3AED",
        "personal_care": "#DB2777", "household": "#4F46E5", "other": "#8A8A7A",
    }
    cat_counts: dict[str, int] = {}
    for log in logs:
        cat = log.get("category") or "unknown"
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    cat_stats = [
        {"name": k, "count": v, "color": cat_colors.get(k, "#8A8A7A")}
        for k, v in sorted(cat_counts.items(), key=lambda x: -x[1])
    ]

    # Confidence distribution
    high = sum(1 for l in logs if l.get("confidence_score", 0) >= 0.9)
    mid = sum(1 for l in logs if 0.7 <= l.get("confidence_score", 0) < 0.9)
    low = sum(1 for l in logs if l.get("confidence_score", 0) < 0.7)
    total = max(len(logs), 1)
    conf_dist = {
        "high": high, "mid": mid, "low": low,
        "high_pct": round(high / total * 100),
        "mid_pct": round(mid / total * 100),
        "low_pct": round(low / total * 100),
    }

    # Warning percentage
    warn_pct = (stats["warning_count"] / max(stats["total_logs"], 1)) * 100

    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "stats": stats,
        "warnings": warnings,
        "cat_stats": cat_stats,
        "conf_dist": conf_dist,
        "warn_pct": warn_pct,
        "active_page": "analytics",
    })


@app.get("/partials/table", response_class=HTMLResponse)
async def partial_table(
    request: Request,
    search: str = Query("", description="Search keyword"),
    category: str = Query("", description="Filter by category"),
    warning_only: str = Query("", description="Show warnings only"),
):
    """HTMX partial: return log table HTML fragment."""
    warning_flag = warning_only == "true"
    logs = get_logs(limit=50, warning_only=warning_flag)

    # Server-side filtering
    if search:
        search_lower = search.lower()
        logs = [l for l in logs if search_lower in l["detected_object"].lower()
                or search_lower in (l.get("category") or "").lower()]
    if category:
        logs = [l for l in logs if l.get("category") == category]

    return templates.TemplateResponse("partials/log_table.html", {
        "request": request,
        "logs": logs,
    })


@app.get("/partials/stats", response_class=HTMLResponse)
async def partial_stats(request: Request):
    """HTMX partial: return stats cards HTML fragment."""
    stats = get_stats()
    return templates.TemplateResponse("partials/stats_cards.html", {
        "request": request,
        "stats": stats,
    })


@app.get("/partials/alerts", response_class=HTMLResponse)
async def partial_alerts(request: Request):
    """HTMX partial: return alert banner HTML fragment."""
    warnings = get_warning_logs()
    return templates.TemplateResponse("partials/alert_banner.html", {
        "request": request,
        "warnings": warnings,
    })


@app.get("/partials/modal/{log_id}", response_class=HTMLResponse)
async def partial_modal(request: Request, log_id: str):
    """HTMX partial: return log detail modal HTML fragment."""
    log = get_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return templates.TemplateResponse("partials/log_modal.html", {
        "request": request,
        "log": log,
    })


# ═══════════════════════════════════════════════════════════════
#  JSON API Endpoints (for AI/CV module)
# ═══════════════════════════════════════════════════════════════

@app.get("/health")
async def healthcheck():
    return {"status": "ok"}

@app.get("/api/logs", response_model=list[LogResponse])
async def api_get_logs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    warning_only: bool = Query(False),
):
    """Get list of shopping logs as JSON."""
    logs = get_logs(limit=limit, offset=offset, warning_only=warning_only)
    return [_format_log(log) for log in logs]


@app.get("/api/logs/{log_id}", response_model=LogResponse)
async def api_get_log(log_id: str):
    """Get a single log detail as JSON."""
    log = get_log_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return _format_log(log)


@app.post("/api/scan")
async def api_scan(scan: ScanRequest):
    """Receive scan data from AI module, save to database."""
    data = _normalize_scan_payload(scan)
    _attach_reference_price_match(data)
    log_id = insert_log(data)
    saved = get_log_by_id(log_id)
    return {
        "message": "Đã lưu log thành công",
        "log_id": log_id,
        "reference_price_suggestion": (
            _resolve_reference_price_suggestion(saved) if saved else None
        ),
    }


@app.delete("/api/logs/{log_id}")
async def api_delete_log(log_id: str):
    """Delete a log entry."""
    deleted = delete_log(log_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Log not found")
    return {"message": "Đã xóa log thành công", "log_id": log_id}


@app.put("/api/logs/{log_id}", response_model=LogResponse)
async def api_update_log(log_id: str, update: UpdateLogRequest):
    """Update a log entry."""
    payload = update.model_dump(exclude_unset=True)
    if "detected_object" in payload or "category" in payload:
        existing = get_log_by_id(log_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Log not found")
        match_input = {
            "detected_object": payload.get("detected_object", existing.get("detected_object")),
            "category": payload.get("category", existing.get("category")),
        }
        _attach_reference_price_match(match_input)
        payload["reference_price_id"] = match_input.get("reference_price_id")
        payload["reference_price_match_score"] = match_input.get("reference_price_match_score")
        payload["reference_price_match_method"] = match_input.get("reference_price_match_method")
    updated = update_log(log_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Log not found")
    return _format_log(updated)


@app.get("/api/stats", response_model=StatsResponse)
async def api_get_stats():
    """Get dashboard statistics as JSON."""
    return get_stats()


@app.get("/api/reference-prices", response_model=ReferencePriceListResponse)
async def api_get_reference_prices(
    query: str = Query("", description="Search by product name, brand, variant, or size"),
    category: str = Query("", description="Normalized category filter"),
    brand: str = Query("", description="Brand filter"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List normalized retail reference prices imported from CSV."""
    items = get_reference_prices(
        query=query,
        category=category,
        brand=brand,
        limit=limit,
        offset=offset,
    )
    total = count_reference_prices_filtered(
        query=query,
        category=category,
        brand=brand,
    )
    return ReferencePriceListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[ReferencePriceResponse(**item) for item in items],
    )


@app.get(
    "/api/reference-prices/categories",
    response_model=list[ReferencePriceCategorySummary],
)
async def api_get_reference_price_categories():
    """List normalized reference-price categories with item counts."""
    rows = list_reference_price_categories()
    return [ReferencePriceCategorySummary(**row) for row in rows]


@app.get("/api/reference-prices/{price_id}", response_model=ReferencePriceResponse)
async def api_get_reference_price(price_id: int):
    """Get one reference-price row by id."""
    item = get_reference_price_by_id(price_id)
    if not item:
        raise HTTPException(status_code=404, detail="Reference price not found")
    return ReferencePriceResponse(**item)


@app.post("/api/reference-prices/import", response_model=ReferencePriceImportResponse)
async def api_import_reference_prices():
    """Manually re-import the CSV retail price catalog into SQLite."""
    return ReferencePriceImportResponse(**import_reference_prices_from_csv())


@app.get("/api/debugger/sample-docs", response_model=list[DebuggerSampleDoc])
async def api_list_sample_docs():
    """List files available in ai-pipeline/sample_docs for debugger workflows."""
    return _list_sample_docs()


@app.get("/api/debugger/sample-docs/{filename}")
async def api_get_sample_doc(filename: str):
    """Serve a debugger sample image for preview/download."""
    file_path = _resolve_sample_doc_path(filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.post("/api/debugger/sample-docs/upload", response_model=DebuggerUploadResponse)
async def api_upload_sample_docs(files: list[UploadFile] = File(...)):
    """Upload one or more sample images into ai-pipeline/sample_docs."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    sample_docs_dir = _sample_docs_dir()
    sample_docs_dir.mkdir(parents=True, exist_ok=True)
    upload_count = 0

    for upload in files:
        if not upload.filename:
            continue
        suffix = Path(upload.filename).suffix.lower()
        if suffix not in ALLOWED_DEBUGGER_SUFFIXES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {upload.filename}",
            )

        safe_name = _build_safe_sample_doc_name(upload.filename)
        destination = sample_docs_dir / safe_name
        content = await upload.read()
        destination.write_bytes(content)
        upload_count += 1

    return DebuggerUploadResponse(
        message="Đã tải ảnh vào sample_docs thành công",
        upload_count=upload_count,
        files=_list_sample_docs(),
        sample_docs_path=str(sample_docs_dir),
    )


@app.delete("/api/debugger/sample-docs/{filename}", response_model=DebuggerUploadResponse)
async def api_delete_sample_doc(filename: str):
    """Delete a sample image from ai-pipeline/sample_docs."""
    file_path = _resolve_sample_doc_path(filename)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    file_path.unlink()

    return DebuggerUploadResponse(
        message="Đã xóa ảnh khỏi sample_docs",
        upload_count=0,
        files=_list_sample_docs(),
        sample_docs_path=str(_sample_docs_dir()),
    )


@app.get("/api/debugger/agentic-ocr/status", response_model=DebuggerAgenticOcrStatus)
async def api_get_agentic_ocr_status():
    """Get the current or most recent run_agentic_ocr.py status."""
    return _serialize_agentic_ocr_status()


@app.post("/api/debugger/agentic-ocr/run", response_model=DebuggerAgenticOcrStatus)
async def api_run_agentic_ocr(options: DebuggerAgenticOcrRunRequest):
    """Start run_agentic_ocr.py in the background so it can be triggered from the web debugger."""
    with _agentic_ocr_lock:
        if _agentic_ocr_status["is_running"]:
            raise HTTPException(status_code=409, detail="run_agentic_ocr.py đang chạy")

        python_executable = _resolve_ai_pipeline_python()
        runner_script = _resolve_agentic_runner_script()
        workdir = _resolve_ai_pipeline_workdir()
        output_json_path = _resolve_agentic_output_json_path()

        if not python_executable.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Python executable không tồn tại: {python_executable}",
            )
        if not runner_script.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Runner script không tồn tại: {runner_script}",
            )

        _agentic_ocr_logs.clear()
        _agentic_ocr_status.update(
            {
                "status": "starting",
                "is_running": True,
                "message": "Đang khởi chạy run_agentic_ocr.py...",
                "started_at": datetime.now().isoformat(),
                "finished_at": None,
                "exit_code": None,
                "pid": None,
                "command": [str(python_executable), str(runner_script)],
                "workdir": str(workdir),
                "python_executable": str(python_executable),
                "runner_script": str(runner_script),
                "output_json_path": str(output_json_path),
                "output_json_exists": output_json_path.exists(),
                "use_yolo": options.use_yolo,
                "enable_selection": options.enable_selection,
                "enable_tts": options.enable_tts,
            }
        )

    thread = threading.Thread(target=_run_agentic_ocr_subprocess, daemon=True)
    thread.start()
    return _serialize_agentic_ocr_status()


# ─── Helpers ─────────────────────────────────────────────────

def _format_log(log: dict) -> dict:
    """Format a DB row into LogResponse-compatible dict."""
    return {
        "log_id": log["log_id"],
        "timestamp": log["timestamp"],
        "source_image": log.get("source_image"),
        "image_base64": log.get("image_base64"),
        "detected_object": log["detected_object"],
        "ocr_text": log.get("ocr_text", ""),
        "price": log.get("price", ""),
        "confidence_score": log.get("confidence_score", 0.0),
        "status": log.get("status", "success"),
        "warning_flag": bool(log.get("warning_flag", 0)),
        "category": log.get("category"),
        "warning_reason": log.get("warning_reason"),
        "price_tag_text_normalized": log.get("price_tag_text_normalized"),
        "product_name_source": log.get("product_name_source"),
        "selected_crop_name": log.get("selected_crop_name"),
        "selection_reason": log.get("selection_reason"),
        "expiry_date": log.get("expiry_date"),
        "reference_price_suggestion": _resolve_reference_price_suggestion(log),
    }


def _resolve_reference_price_suggestion(log: dict) -> ReferencePriceSuggestion | None:
    suggestion = hydrate_reference_price_suggestion(
        log.get("reference_price_id"),
        match_score=log.get("reference_price_match_score"),
        match_method=log.get("reference_price_match_method"),
    )
    if suggestion is None:
        suggestion = suggest_reference_price(
            log.get("detected_object"),
            category=log.get("category"),
        )
    return ReferencePriceSuggestion(**suggestion) if suggestion else None


def _attach_reference_price_match(data: dict) -> None:
    suggestion = suggest_reference_price(
        data.get("detected_object"),
        category=data.get("category"),
    )
    if suggestion is None:
        data["reference_price_id"] = None
        data["reference_price_match_score"] = None
        data["reference_price_match_method"] = None
        return

    data["reference_price_id"] = suggestion["reference_price_id"]
    data["reference_price_match_score"] = suggestion["match_score"]
    data["reference_price_match_method"] = suggestion["match_method"]


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _sample_docs_dir() -> Path:
    configured = os.getenv("DEBUGGER_SAMPLE_DOCS_DIR")
    if configured:
        return Path(configured)
    return REPO_ROOT / "ai-pipeline" / "sample_docs"


def _resolve_ai_pipeline_workdir() -> Path:
    configured = os.getenv("DEBUGGER_AI_PIPELINE_WORKDIR")
    if configured:
        return Path(configured)
    return REPO_ROOT / "ai-pipeline"


def _resolve_agentic_runner_script() -> Path:
    configured = os.getenv("DEBUGGER_AGENTIC_RUNNER")
    if configured:
        return Path(configured)
    return _resolve_ai_pipeline_workdir() / "run_agentic_ocr.py"


def _resolve_agentic_output_json_path() -> Path:
    configured = os.getenv("AGENTIC_OUTPUT_JSON")
    if configured:
        return Path(configured)
    return _resolve_ai_pipeline_workdir() / "tests" / "output.json"


def _resolve_ai_pipeline_python() -> Path:
    configured = os.getenv("DEBUGGER_AI_PIPELINE_PYTHON")
    if configured:
        return Path(configured)

    workdir = _resolve_ai_pipeline_workdir()
    candidates = [
        workdir / ".venv" / "Scripts" / "python.exe",
        workdir / ".venv" / "bin" / "python",
        Path(sys.executable),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def _append_agentic_ocr_log(line: str) -> None:
    cleaned = line.rstrip()
    if not cleaned:
        return
    with _agentic_ocr_lock:
        _agentic_ocr_logs.append(cleaned)


def _serialize_agentic_ocr_status() -> DebuggerAgenticOcrStatus:
    with _agentic_ocr_lock:
        payload = dict(_agentic_ocr_status)
        payload["log_lines"] = list(_agentic_ocr_logs)

    output_json_path = payload.get("output_json_path")
    payload["output_json_exists"] = bool(output_json_path and Path(output_json_path).exists())
    return DebuggerAgenticOcrStatus(**payload)


def _run_agentic_ocr_subprocess() -> None:
    with _agentic_ocr_lock:
        command = list(_agentic_ocr_status["command"])
        workdir = _agentic_ocr_status["workdir"]
        output_json_path = _agentic_ocr_status["output_json_path"]
        use_yolo = _agentic_ocr_status["use_yolo"]
        enable_selection = _agentic_ocr_status["enable_selection"]
        enable_tts = _agentic_ocr_status["enable_tts"]

    env = os.environ.copy()
    env.setdefault("ENABLE_BACKEND_SYNC", "true")
    env.setdefault("BACKEND_URL", "http://127.0.0.1:8000")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env["AGENTIC_USE_YOLO"] = str(use_yolo).lower()
    env["AGENTIC_ENABLE_SELECTION"] = str(enable_selection).lower()
    env["AGENTIC_ENABLE_TTS"] = str(enable_tts).lower()

    try:
        process = subprocess.Popen(
            command,
            cwd=workdir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
    except Exception as exc:
        with _agentic_ocr_lock:
            _agentic_ocr_status.update(
                {
                    "status": "failed",
                    "is_running": False,
                    "message": f"Không thể khởi chạy run_agentic_ocr.py: {exc}",
                    "finished_at": datetime.now().isoformat(),
                    "exit_code": None,
                    "pid": None,
                    "output_json_exists": bool(output_json_path and Path(output_json_path).exists()),
                }
            )
        _append_agentic_ocr_log(f"[launcher-error] {exc}")
        return

    with _agentic_ocr_lock:
        _agentic_ocr_status.update(
            {
                "status": "running",
                "is_running": True,
                "message": "run_agentic_ocr.py đang xử lý ảnh trong sample_docs...",
                "pid": process.pid,
            }
        )

    _append_agentic_ocr_log(f"[started] pid={process.pid}")

    assert process.stdout is not None
    for line in process.stdout:
        _append_agentic_ocr_log(line)

    exit_code = process.wait()
    status = "completed" if exit_code == 0 else "failed"
    message = (
        "Đã chạy xong run_agentic_ocr.py."
        if exit_code == 0
        else f"run_agentic_ocr.py kết thúc với mã lỗi {exit_code}."
    )

    with _agentic_ocr_lock:
        _agentic_ocr_status.update(
            {
                "status": status,
                "is_running": False,
                "message": message,
                "finished_at": datetime.now().isoformat(),
                "exit_code": exit_code,
                "pid": None,
                "output_json_exists": bool(output_json_path and Path(output_json_path).exists()),
            }
        )


def _build_safe_sample_doc_name(original_name: str) -> str:
    path = Path(original_name)
    suffix = path.suffix.lower()
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", path.stem).strip("_") or "upload"
    candidate = f"{stem}{suffix}"
    destination = _sample_docs_dir() / candidate

    if not destination.exists():
        return candidate

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    return f"{stem}_{timestamp}{suffix}"


def _resolve_sample_doc_path(filename: str) -> Path:
    safe_name = Path(filename).name
    if safe_name != filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_DEBUGGER_SUFFIXES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    return _sample_docs_dir() / safe_name


def _serialize_sample_doc(file_path: Path) -> DebuggerSampleDoc:
    stat = file_path.stat()
    return DebuggerSampleDoc(
        name=file_path.name,
        size_bytes=stat.st_size,
        modified_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        preview_url=f"/api/debugger/sample-docs/{file_path.name}",
    )


def _list_sample_docs() -> list[DebuggerSampleDoc]:
    sample_docs_dir = _sample_docs_dir()
    sample_docs_dir.mkdir(parents=True, exist_ok=True)
    files = [
        _serialize_sample_doc(path)
        for path in sorted(
            sample_docs_dir.iterdir(),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        if path.is_file() and path.suffix.lower() in ALLOWED_DEBUGGER_SUFFIXES
    ]
    return files


def _format_price(price) -> str:
    if price is None:
        return ""

    if isinstance(price, str):
        stripped = price.strip()
        return stripped

    try:
        numeric = int(float(price))
    except (TypeError, ValueError):
        return str(price)

    return f"{numeric:,.0f} VND".replace(",", ",")


def _normalize_scan_payload(scan: ScanRequest) -> dict:
    selected = scan.selected_result
    analysis = scan.ai_analysis

    detected_object = "Unknown Product"
    if selected and selected.resolved_product_name():
        detected_object = selected.resolved_product_name()
    elif analysis and analysis.detected_object:
        detected_object = analysis.detected_object

    raw_ocr_text = ""
    if selected and selected.raw_ocr_text:
        raw_ocr_text = selected.raw_ocr_text
    elif analysis and analysis.ocr_text:
        raw_ocr_text = analysis.ocr_text

    price_value = None
    if selected and selected.price is not None:
        price_value = selected.price
    elif analysis and analysis.price:
        price_value = analysis.price

    confidence_score = 0.0
    if selected and selected.selection_confidence is not None:
        confidence_score = selected.selection_confidence
    elif analysis:
        confidence_score = analysis.confidence_score

    price_tag_text_normalized = None
    if selected and selected.price_tag_text_normalized:
        price_tag_text_normalized = selected.price_tag_text_normalized
    elif analysis and analysis.price_tag_text_normalized:
        price_tag_text_normalized = analysis.price_tag_text_normalized

    product_name_source = None
    if selected and selected.product_name_source:
        product_name_source = selected.product_name_source
    elif analysis and analysis.product_name_source:
        product_name_source = analysis.product_name_source

    selected_crop_name = None
    if selected and selected.selected_crop_name:
        selected_crop_name = selected.selected_crop_name
    elif analysis and analysis.selected_crop_name:
        selected_crop_name = analysis.selected_crop_name

    selection_reason = None
    if selected and selected.selection_reason:
        selection_reason = selected.selection_reason
    elif analysis and analysis.selection_reason:
        selection_reason = analysis.selection_reason

    category = scan.category
    if not category and selected and selected.category:
        category = selected.category
    elif not category and analysis and analysis.category:
        category = analysis.category

    return {
        "log_id": scan.log_id,
        "timestamp": scan.timestamp,
        "source_image": scan.source_image,
        "image_base64": scan.image_base64,
        "detected_object": detected_object,
        "ocr_text": raw_ocr_text,
        "price": _format_price(price_value),
        "confidence_score": confidence_score,
        "status": scan.status,
        "warning_flag": scan.warning_flag,
        "category": category,
        "expiry_date": scan.expiry_date,
        "warning_reason": scan.warning_reason,
        "price_tag_text_normalized": price_tag_text_normalized,
        "product_name_source": product_name_source,
        "selected_crop_name": selected_crop_name,
        "selection_reason": selection_reason,
    }


# ─── Run ─────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
