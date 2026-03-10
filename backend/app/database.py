"""SQLite database setup & CRUD functions."""

import sqlite3
import os
from datetime import datetime, date
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "shopping.db")


def get_connection() -> sqlite3.Connection:
    """Get SQLite connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shopping_logs (
            log_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            image_base64 TEXT,
            detected_object TEXT NOT NULL,
            ocr_text TEXT DEFAULT '',
            price TEXT DEFAULT '',
            confidence_score REAL DEFAULT 0.0,
            status TEXT DEFAULT 'success',
            warning_flag INTEGER DEFAULT 0,
            category TEXT,
            expiry_date TEXT,
            warning_reason TEXT
        )
    """)
    conn.commit()
    conn.close()


def generate_log_id() -> str:
    """Generate unique log ID based on timestamp."""
    now = datetime.now()
    return f"LOG_{now.strftime('%Y%m%d%H%M%S')}_{now.microsecond // 1000:03d}"


def insert_log(data: dict) -> str:
    """Insert a new log entry. Returns log_id."""
    conn = get_connection()

    log_id = data.get("log_id") or generate_log_id()
    timestamp = data.get("timestamp") or datetime.now().isoformat()

    # Auto-warning detection: check expiry_date
    warning_flag = data.get("warning_flag", False)
    warning_reason = data.get("warning_reason", "")
    expiry_date = data.get("expiry_date")

    if expiry_date and not warning_flag:
        try:
            exp = date.fromisoformat(expiry_date)
            if exp < date.today():
                warning_flag = True
                warning_reason = "Sản phẩm đã hết hạn sử dụng"
        except ValueError:
            pass

    # Low confidence warning
    confidence = data.get("confidence_score", 0.0)
    if confidence < 0.7 and not warning_flag:
        warning_flag = True
        warning_reason = f"Độ tin cậy AI thấp ({confidence:.0%})"

    conn.execute("""
        INSERT OR REPLACE INTO shopping_logs 
        (log_id, timestamp, image_base64, detected_object, ocr_text, price,
         confidence_score, status, warning_flag, category, expiry_date, warning_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id, timestamp, data.get("image_base64"),
        data.get("detected_object", "Unknown"),
        data.get("ocr_text", ""),
        data.get("price", ""),
        confidence,
        data.get("status", "success"),
        1 if warning_flag else 0,
        data.get("category"),
        expiry_date,
        warning_reason
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
        "SELECT * FROM shopping_logs WHERE log_id = ?", (log_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_log(log_id: str) -> bool:
    """Delete a log by ID. Returns True if deleted."""
    conn = get_connection()
    cursor = conn.execute(
        "DELETE FROM shopping_logs WHERE log_id = ?", (log_id,)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


def update_log(log_id: str, data: dict) -> Optional[dict]:
    """Update a log entry. Returns updated log or None if not found."""
    conn = get_connection()

    # Check if log exists
    existing = conn.execute(
        "SELECT * FROM shopping_logs WHERE log_id = ?", (log_id,)
    ).fetchone()
    if not existing:
        conn.close()
        return None

    existing = dict(existing)

    # Merge updates with existing data
    detected_object = data.get("detected_object", existing["detected_object"])
    ocr_text = data.get("ocr_text", existing["ocr_text"])
    price = data.get("price", existing["price"])
    confidence_score = data.get("confidence_score", existing["confidence_score"])
    category = data.get("category", existing["category"])
    expiry_date = data.get("expiry_date", existing["expiry_date"])
    warning_flag = data.get("warning_flag")
    warning_reason = data.get("warning_reason", existing["warning_reason"])
    status = data.get("status", existing["status"])

    # Auto-warning detection on update
    if warning_flag is None:
        warning_flag = bool(existing["warning_flag"])

    if expiry_date and not warning_flag:
        try:
            exp = date.fromisoformat(expiry_date)
            if exp < date.today():
                warning_flag = True
                warning_reason = "Sản phẩm đã hết hạn sử dụng"
        except ValueError:
            pass

    if confidence_score < 0.7 and not warning_flag:
        warning_flag = True
        warning_reason = f"Độ tin cậy AI thấp ({confidence_score:.0%})"

    conn.execute("""
        UPDATE shopping_logs SET
            detected_object = ?, ocr_text = ?, price = ?,
            confidence_score = ?, category = ?, expiry_date = ?,
            warning_flag = ?, warning_reason = ?, status = ?
        WHERE log_id = ?
    """, (
        detected_object, ocr_text, price,
        confidence_score, category, expiry_date,
        1 if warning_flag else 0, warning_reason, status,
        log_id
    ))
    conn.commit()

    updated = conn.execute(
        "SELECT * FROM shopping_logs WHERE log_id = ?", (log_id,)
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
        (f"{today}%",)
    ).fetchone()[0]
    warn_count = conn.execute(
        "SELECT COUNT(*) FROM shopping_logs WHERE warning_flag = 1"
    ).fetchone()[0]
    avg_conf = conn.execute(
        "SELECT COALESCE(AVG(confidence_score), 0) FROM shopping_logs"
    ).fetchone()[0]
    top = conn.execute(
        "SELECT detected_object, COUNT(*) as cnt FROM shopping_logs "
        "GROUP BY detected_object ORDER BY cnt DESC LIMIT 1"
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
        "SELECT * FROM shopping_logs WHERE warning_flag = 1 ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_log_count() -> int:
    """Get total log count."""
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM shopping_logs").fetchone()[0]
    conn.close()
    return count
