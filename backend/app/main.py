"""FastAPI application — serves both JSON API and HTML dashboard."""

from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

from app.database import init_db, insert_log, get_logs, get_log_by_id, delete_log, update_log, get_stats, get_warning_logs
from app.models import ScanRequest, LogResponse, StatsResponse, UpdateLogRequest
from app.mock_data import seed_database

# ─── App Setup ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
    log_id = insert_log(data)
    return {"message": "Đã lưu log thành công", "log_id": log_id}


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
    updated = update_log(log_id, update.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Log not found")
    return _format_log(updated)


@app.get("/api/stats", response_model=StatsResponse)
async def api_get_stats():
    """Get dashboard statistics as JSON."""
    return get_stats()


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
    }


def _is_truthy(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
