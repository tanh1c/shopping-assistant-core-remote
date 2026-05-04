import type {
    DebuggerAgenticOcrStatus,
    DebuggerSampleDoc,
    DebuggerUploadResponse,
    LogEntry,
    Stats,
} from "@/types"

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") || ""

// ── Input types for CRUD ──
export interface CreateLogInput {
    detected_object: string
    ocr_text?: string
    price?: string
    confidence_score?: number
    category?: string
    expiry_date?: string
    warning_flag?: boolean
    warning_reason?: string
    source_image?: string
    price_tag_text_normalized?: string
    product_name_source?: string
    selected_crop_name?: string
    selection_reason?: string
}

export interface UpdateLogInput {
    detected_object?: string
    ocr_text?: string
    price?: string
    confidence_score?: number
    category?: string
    expiry_date?: string
    warning_flag?: boolean
    warning_reason?: string
    status?: string
    source_image?: string
    price_tag_text_normalized?: string
    product_name_source?: string
    selected_crop_name?: string
    selection_reason?: string
}

// ── Fetch helpers ──
export async function fetchLogs(params?: {
    limit?: number
    warning_only?: boolean
}): Promise<LogEntry[]> {
    const sp = new URLSearchParams()
    if (params?.limit) sp.set("limit", String(params.limit))
    if (params?.warning_only) sp.set("warning_only", "true")
    const res = await fetch(`${BASE}/api/logs?${sp}`)
    if (!res.ok) throw new Error("Failed to fetch logs")
    return res.json()
}

export async function fetchLog(logId: string): Promise<LogEntry> {
    const res = await fetch(`${BASE}/api/logs/${logId}`)
    if (!res.ok) throw new Error("Log not found")
    return res.json()
}

export async function fetchStats(): Promise<Stats> {
    const res = await fetch(`${BASE}/api/stats`)
    if (!res.ok) throw new Error("Failed to fetch stats")
    return res.json()
}

export async function deleteLog(logId: string): Promise<void> {
    const res = await fetch(`${BASE}/api/logs/${logId}`, { method: "DELETE" })
    if (!res.ok) throw new Error("Failed to delete")
}

export async function createLog(data: CreateLogInput): Promise<LogEntry> {
    const res = await fetch(`${BASE}/api/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            source_image: data.source_image,
            ai_analysis: {
                detected_object: data.detected_object,
                ocr_text: data.ocr_text || "",
                price: data.price || "",
                confidence_score: data.confidence_score ?? 0.9,
                price_tag_text_normalized: data.price_tag_text_normalized,
                product_name_source: data.product_name_source,
                selected_crop_name: data.selected_crop_name,
                selection_reason: data.selection_reason,
            },
            category: data.category,
            expiry_date: data.expiry_date,
            warning_flag: data.warning_flag,
            warning_reason: data.warning_reason,
        }),
    })
    if (!res.ok) throw new Error("Failed to create log")
    const result = await res.json()
    return fetchLog(result.log_id)
}

export async function updateLog(
    logId: string,
    data: UpdateLogInput
): Promise<LogEntry> {
    const res = await fetch(`${BASE}/api/logs/${logId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error("Failed to update log")
    return res.json()
}

export async function fetchDebuggerSampleDocs(): Promise<DebuggerSampleDoc[]> {
    const res = await fetch(`${BASE}/api/debugger/sample-docs`)
    if (!res.ok) throw new Error("Failed to fetch debugger sample docs")
    return res.json()
}

export async function uploadDebuggerSampleDocs(files: File[]): Promise<DebuggerUploadResponse> {
    const formData = new FormData()
    files.forEach((file) => formData.append("files", file))

    const res = await fetch(`${BASE}/api/debugger/sample-docs/upload`, {
        method: "POST",
        body: formData,
    })
    if (!res.ok) {
        const message = await res.text()
        throw new Error(message || "Failed to upload debugger sample docs")
    }
    return res.json()
}

export async function deleteDebuggerSampleDoc(filename: string): Promise<DebuggerUploadResponse> {
    const res = await fetch(`${BASE}/api/debugger/sample-docs/${encodeURIComponent(filename)}`, {
        method: "DELETE",
    })
    if (!res.ok) throw new Error("Failed to delete debugger sample doc")
    return res.json()
}

export function debuggerFileUrl(previewUrl: string): string {
    if (!previewUrl) return ""
    if (/^https?:\/\//.test(previewUrl)) return previewUrl
    return `${BASE}${previewUrl}`
}

export async function fetchDebuggerAgenticOcrStatus(): Promise<DebuggerAgenticOcrStatus> {
    const res = await fetch(`${BASE}/api/debugger/agentic-ocr/status`)
    if (!res.ok) throw new Error("Failed to fetch agentic OCR status")
    return res.json()
}

export async function runDebuggerAgenticOcr(options?: {
    use_yolo: boolean
    enable_selection: boolean
    enable_tts: boolean
}): Promise<DebuggerAgenticOcrStatus> {
    const res = await fetch(`${BASE}/api/debugger/agentic-ocr/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            use_yolo: options?.use_yolo ?? true,
            enable_selection: options?.enable_selection ?? true,
            enable_tts: options?.enable_tts ?? true,
        }),
    })
    if (!res.ok) {
        try {
            const payload = await res.json()
            throw new Error(payload.detail || "Failed to start agentic OCR")
        } catch (error) {
            if (error instanceof Error) {
                throw error
            }
            throw new Error("Failed to start agentic OCR")
        }
    }
    return res.json()
}
