"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AIAnalysis(BaseModel):
    """AI analysis result from CV module."""
    detected_object: str = Field(..., description="Tên sản phẩm AI nhận diện")
    ocr_text: str = Field("", description="Kết quả OCR (HSD, thông tin)")
    price: str = Field("", description="Giá sản phẩm")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Độ tin cậy 0-1")


class ScanRequest(BaseModel):
    """Request body for POST /api/scan — nhận dữ liệu từ AI module."""
    log_id: Optional[str] = Field(None, description="ID log, auto-gen nếu không có")
    timestamp: Optional[str] = Field(None, description="Thời gian quét ISO 8601")
    image_base64: Optional[str] = Field(None, description="Ảnh base64 encoded")
    ai_analysis: AIAnalysis
    status: str = Field("success", description="success / error")
    warning_flag: bool = Field(False, description="Cảnh báo hay không")
    category: Optional[str] = Field(None, description="Phân loại: dairy, snack, beverage...")
    expiry_date: Optional[str] = Field(None, description="Ngày hết hạn ISO (YYYY-MM-DD)")
    warning_reason: Optional[str] = Field(None, description="Lý do cảnh báo")


class LogResponse(BaseModel):
    """Response format cho 1 log entry."""
    log_id: str
    timestamp: str
    image_base64: Optional[str] = None
    detected_object: str
    ocr_text: str
    price: str
    confidence_score: float
    status: str
    warning_flag: bool
    category: Optional[str] = None
    expiry_date: Optional[str] = None
    warning_reason: Optional[str] = None


class StatsResponse(BaseModel):
    """Response format cho thống kê tổng quan."""
    total_logs: int
    today_logs: int
    warning_count: int
    avg_confidence: float
    top_product: Optional[str] = None


class UpdateLogRequest(BaseModel):
    """Request body for PUT /api/logs/{log_id} — cập nhật log entry."""
    detected_object: Optional[str] = Field(None, description="Tên sản phẩm")
    ocr_text: Optional[str] = Field(None, description="Kết quả OCR")
    price: Optional[str] = Field(None, description="Giá sản phẩm")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Độ tin cậy 0-1")
    category: Optional[str] = Field(None, description="Phân loại: dairy, snack, beverage...")
    expiry_date: Optional[str] = Field(None, description="Ngày hết hạn ISO (YYYY-MM-DD)")
    warning_flag: Optional[bool] = Field(None, description="Cảnh báo hay không")
    warning_reason: Optional[str] = Field(None, description="Lý do cảnh báo")
    status: Optional[str] = Field(None, description="Trạng thái: success / error")
