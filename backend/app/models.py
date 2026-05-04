"""Pydantic models for request/response validation."""

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class AIAnalysis(BaseModel):
    """Legacy-compatible AI analysis result payload."""

    detected_object: str = Field(..., description="Tên sản phẩm AI nhận diện")
    ocr_text: str = Field("", description="Kết quả OCR")
    price: str = Field("", description="Giá sản phẩm")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Độ tin cậy 0-1")
    category: Optional[str] = Field(None, description="Phân loại sản phẩm")
    price_tag_text_normalized: Optional[str] = Field(
        None,
        description="Nội dung price tag đã được chuẩn hóa",
    )
    product_name_source: Optional[str] = Field(
        None,
        description="Nguồn suy luận tên sản phẩm",
    )
    selected_crop_name: Optional[str] = Field(
        None,
        description="Tên crop price tag được chọn",
    )
    selection_reason: Optional[str] = Field(
        None,
        description="Giải thích vì sao tag này được chọn",
    )


class SelectedResult(BaseModel):
    """Native ai-pipeline selected result payload."""

    name: Optional[str] = Field(None, description="Tên sản phẩm")
    product_name: Optional[str] = Field(None, description="Tên sản phẩm đã chuẩn hóa")
    price: Optional[float | int | str] = Field(None, description="Giá sản phẩm")
    category: Optional[str] = Field(None, description="Phân loại sản phẩm")
    raw_ocr_text: Optional[str] = Field(None, description="OCR text thô từ tag được chọn")
    price_tag_text_normalized: Optional[str] = Field(
        None,
        description="Nội dung price tag đã được chuẩn hóa",
    )
    product_name_source: Optional[str] = Field(
        None,
        description="Nguồn suy luận tên sản phẩm",
    )
    selected_crop_name: Optional[str] = Field(
        None,
        description="Tên crop price tag được chọn",
    )
    selection_reason: Optional[str] = Field(
        None,
        description="Giải thích vì sao tag này được chọn",
    )
    selection_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Độ tin cậy bước chọn candidate",
    )

    def resolved_product_name(self) -> Optional[str]:
        return self.product_name or self.name


class ScanRequest(BaseModel):
    """Request body for POST /api/scan."""

    log_id: Optional[str] = Field(None, description="ID log, auto-gen nếu không có")
    timestamp: Optional[str] = Field(None, description="Thời gian quét ISO 8601")
    source_image: Optional[str] = Field(None, description="Tên ảnh gốc từ edge pipeline")
    image_base64: Optional[str] = Field(None, description="Ảnh base64 encoded")
    ai_analysis: Optional[AIAnalysis] = Field(
        None,
        description="Payload cũ từ AI module",
    )
    selected_result: Optional[SelectedResult] = Field(
        None,
        description="Payload mới từ ai-pipeline sau bước chọn price tag",
    )
    status: str = Field("success", description="success / error")
    warning_flag: Optional[bool] = Field(None, description="Cảnh báo hay không")
    category: Optional[str] = Field(None, description="Phân loại: dairy, snack, beverage...")
    expiry_date: Optional[str] = Field(
        None,
        description="Deprecated. Giữ lại để backward-compatible.",
    )
    warning_reason: Optional[str] = Field(None, description="Lý do cảnh báo")

    @model_validator(mode="after")
    def validate_payload(self):
        if self.ai_analysis is None and self.selected_result is None:
            raise ValueError("Either ai_analysis or selected_result must be provided.")
        return self


class LogResponse(BaseModel):
    """Response format cho 1 log entry."""

    log_id: str
    timestamp: str
    source_image: Optional[str] = None
    image_base64: Optional[str] = None
    detected_object: str
    ocr_text: str
    price: str
    confidence_score: float
    status: str
    warning_flag: bool
    category: Optional[str] = None
    warning_reason: Optional[str] = None
    price_tag_text_normalized: Optional[str] = None
    product_name_source: Optional[str] = None
    selected_crop_name: Optional[str] = None
    selection_reason: Optional[str] = None
    expiry_date: Optional[str] = None
    reference_price_suggestion: Optional["ReferencePriceSuggestion"] = None


class StatsResponse(BaseModel):
    """Response format cho thống kê tổng quan."""

    total_logs: int
    today_logs: int
    warning_count: int
    avg_confidence: float
    top_product: Optional[str] = None


class ReferencePriceResponse(BaseModel):
    """Normalized reference retail price record."""

    id: int
    product_name: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    size_or_volume: Optional[str] = None
    category: Optional[str] = None
    raw_category: Optional[str] = None
    currency: str
    country: str
    price_min_vnd: Optional[int] = None
    price_max_vnd: Optional[int] = None
    price_avg_vnd: Optional[int] = None
    source_1_name: Optional[str] = None
    source_1_price_vnd: Optional[int] = None
    source_1_url: Optional[str] = None
    source_2_name: Optional[str] = None
    source_2_price_vnd: Optional[int] = None
    source_2_url: Optional[str] = None
    source_3_name: Optional[str] = None
    source_3_price_vnd: Optional[int] = None
    source_3_url: Optional[str] = None
    checked_at: Optional[str] = None
    confidence: Optional[str] = None
    notes: Optional[str] = None
    source_csv: Optional[str] = None
    created_at: str
    updated_at: str


class ReferencePriceSuggestion(BaseModel):
    """Closest reference-price match for a scanned product."""

    reference_price_id: int
    match_score: float
    match_method: str
    product_name: str
    brand: Optional[str] = None
    variant: Optional[str] = None
    size_or_volume: Optional[str] = None
    category: Optional[str] = None
    raw_category: Optional[str] = None
    currency: str
    price_min_vnd: Optional[int] = None
    price_max_vnd: Optional[int] = None
    price_avg_vnd: Optional[int] = None
    confidence: Optional[str] = None
    checked_at: Optional[str] = None
    notes: Optional[str] = None
    source_1_name: Optional[str] = None
    source_1_url: Optional[str] = None


class ReferencePriceListResponse(BaseModel):
    """Paginated reference price list payload."""

    total: int
    limit: int
    offset: int
    items: list[ReferencePriceResponse]


class ReferencePriceCategorySummary(BaseModel):
    """Category summary for the reference price catalog."""

    category: Optional[str] = None
    item_count: int


class ReferencePriceImportResponse(BaseModel):
    """CSV import result for reference retail prices."""

    ok: bool
    message: str
    csv_path: str
    found_file: bool
    rows_read: int
    upserted: int
    total_rows_in_db: int
    category_counts: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class DebuggerSampleDoc(BaseModel):
    """Debugger file entry for uploaded sample documents."""

    name: str
    size_bytes: int
    modified_at: str
    preview_url: str


class DebuggerUploadResponse(BaseModel):
    """Debugger upload response payload."""

    message: str
    upload_count: int
    files: list[DebuggerSampleDoc]
    sample_docs_path: str


class DebuggerAgenticOcrStatus(BaseModel):
    """Debugger run status for the sample-doc batch pipeline."""

    status: str
    is_running: bool
    message: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    exit_code: Optional[int] = None
    pid: Optional[int] = None
    command: list[str] = Field(default_factory=list)
    workdir: Optional[str] = None
    python_executable: Optional[str] = None
    runner_script: Optional[str] = None
    output_json_path: Optional[str] = None
    output_json_exists: bool = False
    use_yolo: bool = True
    enable_selection: bool = True
    enable_tts: bool = True
    log_lines: list[str] = Field(default_factory=list)


class DebuggerAgenticOcrRunRequest(BaseModel):
    """Debugger options for starting run_agentic_ocr.py from the web."""

    use_yolo: bool = Field(default=True)
    enable_selection: bool = Field(default=True)
    enable_tts: bool = Field(default=True)


class UpdateLogRequest(BaseModel):
    """Request body for PUT /api/logs/{log_id}."""

    detected_object: Optional[str] = Field(None, description="Tên sản phẩm")
    ocr_text: Optional[str] = Field(None, description="Kết quả OCR")
    price: Optional[str] = Field(None, description="Giá sản phẩm")
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Độ tin cậy 0-1")
    category: Optional[str] = Field(None, description="Phân loại: dairy, snack, beverage...")
    warning_flag: Optional[bool] = Field(None, description="Cảnh báo hay không")
    warning_reason: Optional[str] = Field(None, description="Lý do cảnh báo")
    status: Optional[str] = Field(None, description="Trạng thái: success / error")
    source_image: Optional[str] = Field(None, description="Tên ảnh gốc")
    price_tag_text_normalized: Optional[str] = Field(
        None,
        description="Nội dung price tag đã được chuẩn hóa",
    )
    product_name_source: Optional[str] = Field(
        None,
        description="Nguồn suy luận tên sản phẩm",
    )
    selected_crop_name: Optional[str] = Field(
        None,
        description="Tên crop price tag được chọn",
    )
    selection_reason: Optional[str] = Field(
        None,
        description="Giải thích vì sao tag này được chọn",
    )
    expiry_date: Optional[str] = Field(
        None,
        description="Deprecated. Giữ lại để backward-compatible.",
    )


LogResponse.model_rebuild()
