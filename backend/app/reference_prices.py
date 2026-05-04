"""Reference retail price catalog import and query helpers."""

from __future__ import annotations

import csv
import os
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional
import re
import unicodedata

from app.database import get_connection

DEFAULT_REFERENCE_PRICE_CSV = "vn_retail_prices_140_confirmed_20_each_category_2026-05-03.csv"
SUPPORTED_CONFIDENCE_LEVELS = {"high", "medium", "low"}
CATEGORY_MAPPING = {
    "beverage": "beverage",
    "dairy": "dairy",
    "instant_noodles": "snack",
    "snacks": "snack",
    "seasoning": "condiment",
    "personal_care": "personal_care",
    "household_essentials": "household",
    "bakery": "bakery",
    "condiment": "condiment",
    "snack": "snack",
    "household": "household",
    "other": "other",
}
REQUIRED_HEADERS = {
    "product_name",
    "brand",
    "variant",
    "size_or_volume",
    "category",
    "currency",
    "country",
    "price_min_vnd",
    "price_max_vnd",
    "price_avg_vnd",
    "source_1_name",
    "source_1_price_vnd",
    "source_1_url",
    "checked_at",
    "confidence",
    "notes",
}
IGNORED_MATCH_TOKENS = {
    "nuoc",
    "nước",
    "sua",
    "sữa",
    "ngot",
    "tinh",
    "khiet",
    "thung",
    "thùng",
    "chai",
    "lon",
    "goi",
    "gói",
    "hop",
    "hộp",
    "vi",
    "vị",
    "khong",
    "không",
}


def resolve_reference_price_csv_path() -> Path:
    configured = os.getenv("REFERENCE_PRICE_CSV_PATH")
    if configured:
        return Path(configured)
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / DEFAULT_REFERENCE_PRICE_CSV


def ensure_reference_prices_table() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS reference_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            brand TEXT,
            variant TEXT,
            size_or_volume TEXT,
            category TEXT,
            raw_category TEXT,
            currency TEXT,
            country TEXT,
            price_min_vnd INTEGER,
            price_max_vnd INTEGER,
            price_avg_vnd INTEGER,
            source_1_name TEXT,
            source_1_price_vnd INTEGER,
            source_1_url TEXT,
            source_2_name TEXT,
            source_2_price_vnd INTEGER,
            source_2_url TEXT,
            source_3_name TEXT,
            source_3_price_vnd INTEGER,
            source_3_url TEXT,
            checked_at TEXT,
            confidence TEXT,
            notes TEXT,
            source_csv TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_reference_prices_identity
        ON reference_prices (product_name, brand, variant, size_or_volume)
        """
    )
    conn.commit()
    conn.close()


def normalize_reference_price_category(raw_category: Optional[str]) -> Optional[str]:
    if raw_category is None:
        return None
    normalized = raw_category.strip().lower()
    if not normalized:
        return None
    return CATEGORY_MAPPING.get(normalized, "other")


def count_reference_prices() -> int:
    ensure_reference_prices_table()
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM reference_prices").fetchone()[0]
    conn.close()
    return int(count)


def count_reference_prices_filtered(
    *,
    query: str = "",
    category: str = "",
    brand: str = "",
) -> int:
    ensure_reference_prices_table()
    conn = get_connection()

    where_sql, params = _build_reference_price_filters(
        query=query,
        category=category,
        brand=brand,
    )
    count = conn.execute(
        f"SELECT COUNT(*) FROM reference_prices {where_sql}",
        params,
    ).fetchone()[0]
    conn.close()
    return int(count)


def list_reference_price_categories() -> list[dict]:
    ensure_reference_prices_table()
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT category, COUNT(*) AS item_count
        FROM reference_prices
        GROUP BY category
        ORDER BY category
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_reference_prices(
    *,
    query: str = "",
    category: str = "",
    brand: str = "",
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    ensure_reference_prices_table()
    conn = get_connection()
    where_sql, params = _build_reference_price_filters(
        query=query,
        category=category,
        brand=brand,
    )
    rows = conn.execute(
        f"""
        SELECT *
        FROM reference_prices
        {where_sql}
        ORDER BY category, brand, product_name, size_or_volume
        LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_reference_price_by_id(price_id: int) -> Optional[dict]:
    ensure_reference_prices_table()
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reference_prices WHERE id = ?",
        (price_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def suggest_reference_price(
    product_name: Optional[str],
    *,
    category: Optional[str] = None,
) -> Optional[dict]:
    normalized_name = _normalize_match_text(product_name)
    if not _should_attempt_reference_match(normalized_name):
        return None

    ensure_reference_prices_table()
    conn = get_connection()
    rows = [dict(row) for row in conn.execute("SELECT * FROM reference_prices").fetchall()]
    conn.close()

    best_row: Optional[dict] = None
    best_score = 0.0
    best_method = "fuzzy"

    for row in rows:
        score, method = _score_reference_candidate(
            normalized_name=normalized_name,
            raw_product_name=product_name or "",
            requested_category=category,
            candidate=row,
        )
        if score > best_score:
            best_score = score
            best_method = method
            best_row = row

    if best_row is None or best_score < 0.55:
        return None

    return _build_reference_price_suggestion(
        best_row,
        match_score=best_score,
        match_method=best_method,
    )


def hydrate_reference_price_suggestion(
    reference_price_id: Optional[int],
    *,
    match_score: Optional[float] = None,
    match_method: Optional[str] = None,
) -> Optional[dict]:
    if not reference_price_id:
        return None

    row = get_reference_price_by_id(reference_price_id)
    if not row:
        return None

    return _build_reference_price_suggestion(
        row,
        match_score=match_score,
        match_method=match_method,
    )


def import_reference_prices_from_csv(csv_path: Optional[Path] = None) -> dict:
    ensure_reference_prices_table()
    path = csv_path or resolve_reference_price_csv_path()

    if not path.exists():
        return {
            "ok": False,
            "message": f"Reference price CSV not found: {path}",
            "csv_path": str(path),
            "found_file": False,
            "rows_read": 0,
            "upserted": 0,
            "total_rows_in_db": count_reference_prices(),
            "category_counts": {},
            "warnings": [],
        }

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        headers = set(reader.fieldnames or [])
        missing_headers = sorted(REQUIRED_HEADERS - headers)
        if missing_headers:
            return {
                "ok": False,
                "message": f"Reference price CSV is missing required headers: {', '.join(missing_headers)}",
                "csv_path": str(path),
                "found_file": True,
                "rows_read": 0,
                "upserted": 0,
                "total_rows_in_db": count_reference_prices(),
                "category_counts": {},
                "warnings": [],
            }

        rows = list(reader)

    warnings: list[str] = []
    raw_category_counts = Counter()
    normalized_category_counts = Counter()
    now_iso = datetime.now().isoformat()

    conn = get_connection()
    upserted = 0

    for idx, row in enumerate(rows, start=2):
        product_name = _clean_text(row.get("product_name"))
        if not product_name:
            warnings.append(f"Row {idx}: missing product_name, skipped.")
            continue

        raw_category = _clean_text(row.get("category"))
        normalized_category = normalize_reference_price_category(raw_category)
        raw_category_counts[raw_category or ""] += 1
        normalized_category_counts[normalized_category or ""] += 1

        confidence = (_clean_text(row.get("confidence")) or "medium").lower()
        if confidence not in SUPPORTED_CONFIDENCE_LEVELS:
            warnings.append(f"Row {idx}: unsupported confidence '{confidence}', coerced to medium.")
            confidence = "medium"

        conn.execute(
            """
            INSERT INTO reference_prices (
                product_name, brand, variant, size_or_volume,
                category, raw_category, currency, country,
                price_min_vnd, price_max_vnd, price_avg_vnd,
                source_1_name, source_1_price_vnd, source_1_url,
                source_2_name, source_2_price_vnd, source_2_url,
                source_3_name, source_3_price_vnd, source_3_url,
                checked_at, confidence, notes, source_csv, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_name, brand, variant, size_or_volume) DO UPDATE SET
                category = excluded.category,
                raw_category = excluded.raw_category,
                currency = excluded.currency,
                country = excluded.country,
                price_min_vnd = excluded.price_min_vnd,
                price_max_vnd = excluded.price_max_vnd,
                price_avg_vnd = excluded.price_avg_vnd,
                source_1_name = excluded.source_1_name,
                source_1_price_vnd = excluded.source_1_price_vnd,
                source_1_url = excluded.source_1_url,
                source_2_name = excluded.source_2_name,
                source_2_price_vnd = excluded.source_2_price_vnd,
                source_2_url = excluded.source_2_url,
                source_3_name = excluded.source_3_name,
                source_3_price_vnd = excluded.source_3_price_vnd,
                source_3_url = excluded.source_3_url,
                checked_at = excluded.checked_at,
                confidence = excluded.confidence,
                notes = excluded.notes,
                source_csv = excluded.source_csv,
                updated_at = excluded.updated_at
            """,
            (
                product_name,
                _clean_text(row.get("brand")),
                _clean_text(row.get("variant")),
                _clean_text(row.get("size_or_volume")),
                normalized_category,
                raw_category,
                (_clean_text(row.get("currency")) or "VND").upper(),
                (_clean_text(row.get("country")) or "VN").upper(),
                _parse_int(row.get("price_min_vnd")),
                _parse_int(row.get("price_max_vnd")),
                _parse_int(row.get("price_avg_vnd")),
                _clean_text(row.get("source_1_name")),
                _parse_int(row.get("source_1_price_vnd")),
                _clean_text(row.get("source_1_url")),
                _clean_text(row.get("source_2_name")),
                _parse_int(row.get("source_2_price_vnd")),
                _clean_text(row.get("source_2_url")),
                _clean_text(row.get("source_3_name")),
                _parse_int(row.get("source_3_price_vnd")),
                _clean_text(row.get("source_3_url")),
                _clean_text(row.get("checked_at")),
                confidence,
                _clean_text(row.get("notes")),
                path.name,
                now_iso,
                now_iso,
            ),
        )
        upserted += 1

    conn.commit()
    total_rows = conn.execute("SELECT COUNT(*) FROM reference_prices").fetchone()[0]
    conn.close()

    if raw_category_counts != normalized_category_counts:
        warnings.append(
            "Some CSV categories were mapped into backend categories "
            f"({dict((k, CATEGORY_MAPPING.get(k, 'other')) for k in raw_category_counts.keys() if k)})."
        )

    return {
        "ok": True,
        "message": f"Imported {upserted} reference price rows from CSV.",
        "csv_path": str(path),
        "found_file": True,
        "rows_read": len(rows),
        "upserted": upserted,
        "total_rows_in_db": int(total_rows),
        "category_counts": {k: v for k, v in normalized_category_counts.items() if k},
        "warnings": warnings,
    }


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = " ".join(str(value).split()).strip()
    return cleaned or None


def _parse_int(value: Optional[str]) -> Optional[int]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    digits_only = "".join(ch for ch in cleaned if ch.isdigit())
    if not digits_only:
        return None
    return int(digits_only)


def _build_reference_price_suggestion(
    row: dict,
    *,
    match_score: Optional[float],
    match_method: Optional[str],
) -> dict:
    return {
        "reference_price_id": row["id"],
        "match_score": round(float(match_score or 0.0), 4),
        "match_method": match_method or "stored",
        "product_name": row.get("product_name"),
        "brand": row.get("brand"),
        "variant": row.get("variant"),
        "size_or_volume": row.get("size_or_volume"),
        "category": row.get("category"),
        "raw_category": row.get("raw_category"),
        "currency": row.get("currency"),
        "price_min_vnd": row.get("price_min_vnd"),
        "price_max_vnd": row.get("price_max_vnd"),
        "price_avg_vnd": row.get("price_avg_vnd"),
        "confidence": row.get("confidence"),
        "checked_at": row.get("checked_at"),
        "notes": row.get("notes"),
        "source_1_name": row.get("source_1_name"),
        "source_1_url": row.get("source_1_url"),
    }


def _score_reference_candidate(
    *,
    normalized_name: str,
    raw_product_name: str,
    requested_category: Optional[str],
    candidate: dict,
) -> tuple[float, str]:
    candidate_name = _normalize_match_text(candidate.get("product_name"))
    candidate_full = _normalize_match_text(
        " ".join(
            part
            for part in [
                candidate.get("product_name"),
                candidate.get("brand"),
                candidate.get("variant"),
                candidate.get("size_or_volume"),
            ]
            if part
        )
    )

    input_tokens = _tokenize_for_match(normalized_name)
    candidate_tokens = _tokenize_for_match(candidate_full)
    if not input_tokens or not candidate_tokens:
        return 0.0, "fuzzy"

    overlap_count = len(input_tokens & candidate_tokens)
    input_overlap = overlap_count / max(len(input_tokens), 1)
    candidate_overlap = overlap_count / max(len(candidate_tokens), 1)
    name_ratio = SequenceMatcher(None, normalized_name, candidate_name).ratio()
    full_ratio = SequenceMatcher(None, normalized_name, candidate_full).ratio()

    score = (
        (name_ratio * 0.45)
        + (full_ratio * 0.2)
        + (input_overlap * 0.25)
        + (candidate_overlap * 0.1)
    )
    method = "fuzzy"

    if normalized_name == candidate_name:
        score += 0.3
        method = "exact_name"
    elif candidate_name and candidate_name in normalized_name:
        score += 0.18
        method = "contains_name"

    brand_text = _normalize_match_text(candidate.get("brand"))
    if brand_text and brand_text in normalized_name:
        score += 0.12
        if method == "fuzzy":
            method = "brand_match"

    size_text = _normalize_match_text(candidate.get("size_or_volume"))
    if size_text and size_text in normalized_name:
        score += 0.14
        if method == "fuzzy":
            method = "size_match"

    requested_normalized_category = normalize_reference_price_category(requested_category)
    candidate_category = candidate.get("category")
    if requested_normalized_category and candidate_category == requested_normalized_category:
        score += 0.08
    elif requested_normalized_category and candidate_category and candidate_category != requested_normalized_category:
        score -= 0.06

    # Avoid overly confident matches for very short or generic strings.
    if len(_tokenize_for_match(raw_product_name)) <= 1 and name_ratio < 0.75:
        score -= 0.2

    return min(max(score, 0.0), 1.0), method


def _normalize_match_text(value: Optional[str]) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split()).strip()


def _tokenize_for_match(value: Optional[str]) -> set[str]:
    normalized = _normalize_match_text(value)
    return {
        token
        for token in normalized.split()
        if len(token) > 1 and token not in IGNORED_MATCH_TOKENS
    }


def _should_attempt_reference_match(normalized_name: str) -> bool:
    if not normalized_name:
        return False
    if normalized_name in {"unknown", "unknown product", "n a"}:
        return False
    if len(normalized_name) < 4:
        return False
    return len(_tokenize_for_match(normalized_name)) >= 1


def _build_reference_price_filters(
    *,
    query: str,
    category: str,
    brand: str,
) -> tuple[str, list[object]]:
    clauses = []
    params: list[object] = []

    if query.strip():
        clauses.append(
            "("
            "LOWER(product_name) LIKE ? "
            "OR LOWER(brand) LIKE ? "
            "OR LOWER(variant) LIKE ? "
            "OR LOWER(size_or_volume) LIKE ?"
            ")"
        )
        needle = f"%{query.strip().lower()}%"
        params.extend([needle, needle, needle, needle])

    if category.strip():
        clauses.append("category = ?")
        params.append(category.strip())

    if brand.strip():
        clauses.append("LOWER(brand) LIKE ?")
        params.append(f"%{brand.strip().lower()}%")

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params
