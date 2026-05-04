"""SQLite database setup & CRUD functions."""

import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional

REQUIRED_COLUMNS = {
    "source_image": "TEXT",
    "price_tag_text_normalized": "TEXT",
    "product_name_source": "TEXT",
    "selected_crop_name": "TEXT",
    "selection_reason": "TEXT",
    "reference_price_id": "INTEGER",
    "reference_price_match_score": "REAL",
    "reference_price_match_method": "TEXT",
}


def _default_db_path() -> Path:
    return Path(__file__).resolve().parent / "shopping.db"


def resolve_db_path() -> Path:
    explicit_path = os.getenv("SHOPPING_DB_PATH")
    if explicit_path:
        return Path(explicit_path).expanduser()

    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url.startswith("sqlite:///"):
        sqlite_path = database_url.removeprefix("sqlite:///")
        if sqlite_path:
            return Path(sqlite_path).expanduser()

    return _default_db_path()


def get_connection() -> sqlite3.Connection:
    """Get SQLite connection with Row factory."""
    db_path = resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist and migrate missing columns."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shopping_logs (
            log_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            source_image TEXT,
            image_base64 TEXT,
            detected_object TEXT NOT NULL,
            ocr_text TEXT DEFAULT '',
            price TEXT DEFAULT '',
            confidence_score REAL DEFAULT 0.0,
            status TEXT DEFAULT 'success',
            warning_flag INTEGER DEFAULT 0,
            category TEXT,
            expiry_date TEXT,
            warning_reason TEXT,
            price_tag_text_normalized TEXT,
            product_name_source TEXT,
            selected_crop_name TEXT,
            selection_reason TEXT,
            reference_price_id INTEGER,
            reference_price_match_score REAL,
            reference_price_match_method TEXT
        )
    """)

    existing_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(shopping_logs)").fetchall()
    }
    for column_name, column_type in REQUIRED_COLUMNS.items():
        if column_name not in existing_columns:
            conn.execute(f"ALTER TABLE shopping_logs ADD COLUMN {column_name} {column_type}")

    conn.commit()
    conn.close()


def generate_log_id() -> str:
    """Generate unique log ID based on timestamp."""
    now = datetime.now()
    return f"LOG_{now.strftime('%Y%m%d%H%M%S')}_{now.microsecond // 1000:03d}"


def _apply_warning_rules(data: dict) -> tuple[bool, str]:
    warning_flag = bool(data.get("warning_flag", False))
    warning_reason = data.get("warning_reason", "") or ""

    status = data.get("status", "success")
    if status != "success" and not warning_flag:
        warning_flag = True
        warning_reason = warning_reason or "Pipeline xử lý lỗi hoặc không hoàn tất"

    confidence = data.get("confidence_score", 0.0) or 0.0
    if confidence < 0.7 and not warning_flag:
        warning_flag = True
        warning_reason = warning_reason or f"Độ tin cậy AI thấp ({confidence:.0%})"

    expiry_date = data.get("expiry_date")
    if expiry_date and not warning_flag:
        try:
            exp = date.fromisoformat(expiry_date)
            if exp < date.today():
                warning_flag = True
                warning_reason = warning_reason or "Sản phẩm đã hết hạn sử dụng"
        except ValueError:
            pass

    return warning_flag, warning_reason


def insert_log(data: dict) -> str:
    """Insert a new log entry. Returns log_id."""
    conn = get_connection()

    log_id = data.get("log_id") or generate_log_id()
    timestamp = data.get("timestamp") or datetime.now().isoformat()
    warning_flag, warning_reason = _apply_warning_rules(data)

    conn.execute("""
        INSERT OR REPLACE INTO shopping_logs
        (log_id, timestamp, source_image, image_base64, detected_object, ocr_text, price,
         confidence_score, status, warning_flag, category, expiry_date, warning_reason,
         price_tag_text_normalized, product_name_source, selected_crop_name, selection_reason,
         reference_price_id, reference_price_match_score, reference_price_match_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id,
        timestamp,
        data.get("source_image"),
        data.get("image_base64"),
        data.get("detected_object", "Unknown"),
        data.get("ocr_text", ""),
        data.get("price", ""),
        data.get("confidence_score", 0.0) or 0.0,
        data.get("status", "success"),
        1 if warning_flag else 0,
        data.get("category"),
        data.get("expiry_date"),
        warning_reason,
        data.get("price_tag_text_normalized"),
        data.get("product_name_source"),
        data.get("selected_crop_name"),
        data.get("selection_reason"),
        data.get("reference_price_id"),
        data.get("reference_price_match_score"),
        data.get("reference_price_match_method"),
    ))
    conn.commit()
    conn.close()
    return log_id


def get_logs(limit: int = 50, offset: int = 0, warning_only: bool = False) -> list[dict]:
    """Get list of logs, newest first."""
    conn = get_connection()

    query = "SELECT * FROM shopping_logs"
    params: list = []

    if warning_only:
        query += " WHERE warning_flag = 1"

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_log_by_id(log_id: str) -> Optional[dict]:
    """Get a single log by ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM shopping_logs WHERE log_id = ?",
        (log_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_log(log_id: str) -> bool:
    """Delete a log by ID. Returns True if deleted."""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM shopping_logs WHERE log_id = ?",
        (log_id,),
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update_log(log_id: str, data: dict) -> Optional[dict]:
    """Update a log entry. Returns updated log or None if not found."""
    conn = get_connection()

    existing = conn.execute(
        "SELECT * FROM shopping_logs WHERE log_id = ?",
        (log_id,),
    ).fetchone()
    if not existing:
        conn.close()
        return None

    existing = dict(existing)

    merged_data = {
        "detected_object": data.get("detected_object", existing["detected_object"]),
        "ocr_text": data.get("ocr_text", existing["ocr_text"]),
        "price": data.get("price", existing["price"]),
        "confidence_score": data.get("confidence_score", existing["confidence_score"]),
        "category": data.get("category", existing["category"]),
        "expiry_date": data.get("expiry_date", existing["expiry_date"]),
        "warning_flag": data.get("warning_flag", bool(existing["warning_flag"])),
        "warning_reason": data.get("warning_reason", existing["warning_reason"]),
        "status": data.get("status", existing["status"]),
        "source_image": data.get("source_image", existing.get("source_image")),
        "image_base64": existing.get("image_base64"),
        "price_tag_text_normalized": data.get(
            "price_tag_text_normalized",
            existing.get("price_tag_text_normalized"),
        ),
        "product_name_source": data.get(
            "product_name_source",
            existing.get("product_name_source"),
        ),
        "selected_crop_name": data.get(
            "selected_crop_name",
            existing.get("selected_crop_name"),
        ),
        "selection_reason": data.get(
            "selection_reason",
            existing.get("selection_reason"),
        ),
        "reference_price_id": data.get(
            "reference_price_id",
            existing.get("reference_price_id"),
        ),
        "reference_price_match_score": data.get(
            "reference_price_match_score",
            existing.get("reference_price_match_score"),
        ),
        "reference_price_match_method": data.get(
            "reference_price_match_method",
            existing.get("reference_price_match_method"),
        ),
    }

    warning_flag, warning_reason = _apply_warning_rules(merged_data)

    conn.execute("""
        UPDATE shopping_logs SET
            detected_object = ?, ocr_text = ?, price = ?,
            confidence_score = ?, category = ?, expiry_date = ?,
            warning_flag = ?, warning_reason = ?, status = ?,
            source_image = ?, price_tag_text_normalized = ?,
            product_name_source = ?, selected_crop_name = ?, selection_reason = ?,
            reference_price_id = ?, reference_price_match_score = ?, reference_price_match_method = ?
        WHERE log_id = ?
    """, (
        merged_data["detected_object"],
        merged_data["ocr_text"],
        merged_data["price"],
        merged_data["confidence_score"],
        merged_data["category"],
        merged_data["expiry_date"],
        1 if warning_flag else 0,
        warning_reason,
        merged_data["status"],
        merged_data["source_image"],
        merged_data["price_tag_text_normalized"],
        merged_data["product_name_source"],
        merged_data["selected_crop_name"],
        merged_data["selection_reason"],
        merged_data["reference_price_id"],
        merged_data["reference_price_match_score"],
        merged_data["reference_price_match_method"],
        log_id,
    ))
    conn.commit()

    updated = conn.execute(
        "SELECT * FROM shopping_logs WHERE log_id = ?",
        (log_id,),
    ).fetchone()
    conn.close()
    return dict(updated) if updated else None


def get_stats() -> dict:
    """Get dashboard statistics."""
    conn = get_connection()
    today = date.today().isoformat()

    total = conn.execute("SELECT COUNT(*) FROM shopping_logs").fetchone()[0]
    today_count = conn.execute(
        "SELECT COUNT(*) FROM shopping_logs WHERE timestamp LIKE ?",
        (f"{today}%",),
    ).fetchone()[0]
    warn_count = conn.execute(
        "SELECT COUNT(*) FROM shopping_logs WHERE warning_flag = 1",
    ).fetchone()[0]
    avg_conf = conn.execute(
        "SELECT COALESCE(AVG(confidence_score), 0) FROM shopping_logs",
    ).fetchone()[0]
    top = conn.execute(
        "SELECT detected_object, COUNT(*) as cnt FROM shopping_logs "
        "GROUP BY detected_object ORDER BY cnt DESC LIMIT 1",
    ).fetchone()

    conn.close()
    return {
        "total_logs": total,
        "today_logs": today_count,
        "warning_count": warn_count,
        "avg_confidence": round(avg_conf, 2),
        "top_product": top["detected_object"] if top else None,
    }


def get_warning_logs() -> list[dict]:
    """Get all logs with warning_flag = true."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM shopping_logs WHERE warning_flag = 1 ORDER BY timestamp DESC",
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_log_count() -> int:
    """Get total log count."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM shopping_logs").fetchone()[0]
    conn.close()
    return count
