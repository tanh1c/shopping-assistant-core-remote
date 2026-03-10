export interface LogEntry {
    log_id: string
    timestamp: string
    image_base64?: string | null
    detected_object: string
    ocr_text: string
    price: string
    confidence_score: number
    status: string
    warning_flag: boolean
    category?: string | null
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

export type PollMode = "realtime" | "slow" | "off"
