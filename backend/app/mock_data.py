"""Seed 12 mock records with diverse Vietnamese products."""

from datetime import datetime, timedelta
import random

# Small 1x1 pixel JPEG as placeholder (valid base64)
PLACEHOLDER_IMAGE = (
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgK"
    "DBQNDBALDS0hERASHhIgIyEiICApKDAtIiAlIx8fKy0vMTU1ISZEQ0ZHTS0xUTshLz0/Pz//2wBD"
    "AQkJCQwNDBgNDRg9Ih0iPT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09"
    "PT09PT09PT09PT//wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQF"
    "BgcICQoL/8QAFRABAAAAAAAAAAAAAAAAAAAAEf/aAAwDAQACEQMRAD8AJQB//9k="
)

MOCK_RECORDS = [
    {
        "log_id": "LOG_20260307_001",
        "timestamp": (datetime.now() - timedelta(minutes=5)).isoformat(),
        "detected_object": "Sữa tươi Vinamilk 100% 180ml",
        "ocr_text": "HSD: 20/12/2026",
        "price": "8,000 VND",
        "confidence_score": 0.95,
        "status": "success",
        "warning_flag": False,
        "category": "dairy",
        "expiry_date": "2026-12-20",
        "warning_reason": "",
    },
    {
        "log_id": "LOG_20260307_002",
        "timestamp": (datetime.now() - timedelta(minutes=12)).isoformat(),
        "detected_object": "Mì Hảo Hảo tôm chua cay 75g",
        "ocr_text": "NSX: 01/2026 - HSD: 01/2027",
        "price": "4,500 VND",
        "confidence_score": 0.91,
        "status": "success",
        "warning_flag": False,
        "category": "snack",
        "expiry_date": "2027-01-15",
        "warning_reason": "",
    },
    {
        "log_id": "LOG_20260307_003",
        "timestamp": (datetime.now() - timedelta(minutes=20)).isoformat(),
        "detected_object": "Nước suối Aquafina 500ml",
        "ocr_text": "HSD: 03/2027",
        "price": "5,000 VND",
        "confidence_score": 0.98,
        "status": "success",
        "warning_flag": False,
        "category": "beverage",
        "expiry_date": "2027-03-01",
        "warning_reason": "",
    },
    {
        "log_id": "LOG_20260307_004",
        "timestamp": (datetime.now() - timedelta(minutes=35)).isoformat(),
        "detected_object": "Bánh mì Kinh Đô sandwich",
        "ocr_text": "HSD: 01/03/2026",
        "price": "12,000 VND",
        "confidence_score": 0.88,
        "status": "success",
        "warning_flag": True,
        "category": "bakery",
        "expiry_date": "2026-03-01",
        "warning_reason": "Sản phẩm đã hết hạn sử dụng",
    },
    {
        "log_id": "LOG_20260307_005",
        "timestamp": (datetime.now() - timedelta(hours=1)).isoformat(),
        "detected_object": "Coca-Cola lon 330ml",
        "ocr_text": "Best before: 06/2027",
        "price": "10,000 VND",
        "confidence_score": 0.97,
        "status": "success",
        "warning_flag": False,
        "category": "beverage",
        "expiry_date": "2027-06-30",
        "warning_reason": "",
    },
    {
        "log_id": "LOG_20260307_006",
        "timestamp": (datetime.now() - timedelta(hours=1, minutes=15)).isoformat(),
        "detected_object": "Phô mai Con Bò Cười 8 miếng",
        "ocr_text": "HSD: 15/08/2026",
        "price": "32,000 VND",
        "confidence_score": 0.93,
        "status": "success",
        "warning_flag": False,
        "category": "dairy",
        "expiry_date": "2026-08-15",
        "warning_reason": "",
    },
    {
        "log_id": "LOG_20260307_007",
        "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
        "detected_object": "Unknown Product",
        "ocr_text": "",
        "price": "",
        "confidence_score": 0.35,
        "status": "success",
        "warning_flag": True,
        "category": None,
        "expiry_date": None,
        "warning_reason": "Độ tin cậy AI thấp (35%)",
    },
    {
        "log_id": "LOG_20260307_008",
        "timestamp": (datetime.now() - timedelta(hours=2, minutes=30)).isoformat(),
        "detected_object": "Trà xanh Không Độ 455ml",
        "ocr_text": "HSD: 10/2026",
        "price": "10,000 VND",
        "confidence_score": 0.94,
        "status": "success",
        "warning_flag": False,
        "category": "beverage",
        "expiry_date": "2026-10-01",
        "warning_reason": "",
    },
    {
        "log_id": "LOG_20260307_009",
        "timestamp": (datetime.now() - timedelta(hours=3)).isoformat(),
        "detected_object": "Snack Oishi tôm 40g",
        "ocr_text": "NSX: 12/2025 HSD: 12/2026",
        "price": "6,000 VND",
        "confidence_score": 0.89,
        "status": "success",
        "warning_flag": False,
        "category": "snack",
        "expiry_date": "2026-12-01",
        "warning_reason": "",
    },
    {
        "log_id": "LOG_20260307_010",
        "timestamp": (datetime.now() - timedelta(hours=4)).isoformat(),
        "detected_object": "Sữa đặc Ông Thọ 380g",
        "ocr_text": "HSD: 02/2025",
        "price": "18,000 VND",
        "confidence_score": 0.92,
        "status": "success",
        "warning_flag": True,
        "category": "dairy",
        "expiry_date": "2025-02-28",
        "warning_reason": "Sản phẩm đã hết hạn sử dụng",
    },
    {
        "log_id": "LOG_20260307_011",
        "timestamp": (datetime.now() - timedelta(hours=5)).isoformat(),
        "detected_object": "Nước mắm Nam Ngư 500ml",
        "ocr_text": "HSD: 05/2027",
        "price": "22,000 VND",
        "confidence_score": 0.96,
        "status": "success",
        "warning_flag": False,
        "category": "condiment",
        "expiry_date": "2027-05-01",
        "warning_reason": "",
    },
    {
        "log_id": "LOG_20260307_012",
        "timestamp": (datetime.now() - timedelta(hours=6)).isoformat(),
        "detected_object": "Dầu ăn Tường An 1L",
        "ocr_text": "NSX: 01/2026 - HSD: 01/2027",
        "price": "38,000 VND",
        "confidence_score": 0.90,
        "status": "success",
        "warning_flag": False,
        "category": "condiment",
        "expiry_date": "2027-01-01",
        "warning_reason": "",
    },
]


def seed_database():
    """Insert mock records into database."""
    from app.database import get_connection, init_db

    init_db()
    conn = get_connection()

    # Check if data already exists
    count = conn.execute("SELECT COUNT(*) FROM shopping_logs").fetchone()[0]
    if count > 0:
        conn.close()
        return False

    for record in MOCK_RECORDS:
        conn.execute("""
            INSERT INTO shopping_logs 
            (log_id, timestamp, image_base64, detected_object, ocr_text, price,
             confidence_score, status, warning_flag, category, expiry_date, warning_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record["log_id"],
            record["timestamp"],
            PLACEHOLDER_IMAGE,
            record["detected_object"],
            record["ocr_text"],
            record["price"],
            record["confidence_score"],
            record["status"],
            1 if record["warning_flag"] else 0,
            record.get("category"),
            record.get("expiry_date"),
            record.get("warning_reason", ""),
        ))

    conn.commit()
    conn.close()
    return True


if __name__ == "__main__":
    seed_database()
    print("✓ Seeded 12 mock records successfully!")
