export interface LogEntry {
    log_id: string
    timestamp: string
    source_image?: string | null
    image_base64?: string | null
    detected_object: string
    ocr_text: string
    price: string
    confidence_score: number
    status: string
    warning_flag: boolean
    category?: string | null
    price_tag_text_normalized?: string | null
    product_name_source?: string | null
    selected_crop_name?: string | null
    selection_reason?: string | null
    expiry_date?: string | null
    warning_reason?: string | null
}

export interface Stats {
    total_logs: number
    today_logs: number
    warning_count: number
    avg_confidence: number
    top_product?: string | null
}

export interface DebuggerSampleDoc {
    name: string
    size_bytes: number
    modified_at: string
    preview_url: string
}

export interface DebuggerUploadResponse {
    message: string
    upload_count: number
    files: DebuggerSampleDoc[]
    sample_docs_path: string
}

export interface DebuggerAgenticOcrStatus {
    status: string
    is_running: boolean
    message: string
    started_at?: string | null
    finished_at?: string | null
    exit_code?: number | null
    pid?: number | null
    command: string[]
    workdir?: string | null
    python_executable?: string | null
    runner_script?: string | null
    output_json_path?: string | null
    output_json_exists: boolean
    use_yolo: boolean
    enable_selection: boolean
    enable_tts: boolean
    log_lines: string[]
}

export type PollMode = "realtime" | "slow" | "off"
