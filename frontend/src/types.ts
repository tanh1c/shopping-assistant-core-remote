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

export type PollMode = "realtime" | "slow" | "off"
