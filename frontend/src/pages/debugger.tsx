import { useEffect, useRef, useState, type ChangeEvent } from "react"
import { toast } from "sonner"
import {
    BugIcon,
    FolderUpIcon,
    ImageIcon,
    PlayIcon,
    RefreshCcwIcon,
    SquareTerminalIcon,
    Trash2Icon,
    UploadIcon,
} from "lucide-react"

import {
    fetchDebuggerAgenticOcrStatus,
    debuggerFileUrl,
    deleteDebuggerSampleDoc,
    fetchDebuggerSampleDocs,
    runDebuggerAgenticOcr,
    uploadDebuggerSampleDocs,
} from "@/lib/api"
import type { DebuggerAgenticOcrStatus, DebuggerSampleDoc } from "@/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"


function formatBytes(size: number): string {
    if (size < 1024) return `${size} B`
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
    return `${(size / (1024 * 1024)).toFixed(1)} MB`
}


function formatDate(value: string): string {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "short",
        timeStyle: "short",
    }).format(date)
}


function getRunStatusLabel(status?: string | null): string {
    switch (status) {
        case "starting":
            return "Đang khởi động"
        case "running":
            return "Đang chạy"
        case "completed":
            return "Hoàn tất"
        case "failed":
            return "Thất bại"
        default:
            return "Chưa chạy"
    }
}


function getRunStatusClass(status?: string | null): string {
    switch (status) {
        case "starting":
        case "running":
            return "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400"
        case "completed":
            return "bg-green-500/10 text-green-600 dark:text-green-400"
        case "failed":
            return "bg-red-500/10 text-red-600 dark:text-red-400"
        default:
            return "bg-muted text-muted-foreground"
    }
}


export default function DebuggerPage() {
    const fileInputRef = useRef<HTMLInputElement | null>(null)
    const [files, setFiles] = useState<DebuggerSampleDoc[]>([])
    const [selectedFiles, setSelectedFiles] = useState<File[]>([])
    const [sampleDocsPath, setSampleDocsPath] = useState("ai-pipeline/sample_docs")
    const [isLoading, setIsLoading] = useState(true)
    const [isUploading, setIsUploading] = useState(false)
    const [deletingFile, setDeletingFile] = useState<string | null>(null)
    const [agenticStatus, setAgenticStatus] = useState<DebuggerAgenticOcrStatus | null>(null)
    const [isStatusLoading, setIsStatusLoading] = useState(true)
    const [isStartingRun, setIsStartingRun] = useState(false)
    const [runOptions, setRunOptions] = useState({
        use_yolo: true,
        enable_selection: true,
        enable_tts: true,
    })

    const loadFiles = async () => {
        setIsLoading(true)
        try {
            const nextFiles = await fetchDebuggerSampleDocs()
            setFiles(nextFiles)
        } catch {
            toast.error("Không thể tải danh sách ảnh debugger")
        } finally {
            setIsLoading(false)
        }
    }

    const loadRunStatus = async (silent = false) => {
        if (!silent) {
            setIsStatusLoading(true)
        }
        try {
            const status = await fetchDebuggerAgenticOcrStatus()
            setAgenticStatus(status)
            setRunOptions({
                use_yolo: status.use_yolo,
                enable_selection: status.enable_selection,
                enable_tts: status.enable_tts,
            })
        } catch {
            if (!silent) {
                toast.error("Không thể tải trạng thái run_agentic_ocr.py")
            }
        } finally {
            if (!silent) {
                setIsStatusLoading(false)
            }
        }
    }

    useEffect(() => {
        loadFiles()
        loadRunStatus()
    }, [])

    useEffect(() => {
        if (!agenticStatus?.is_running) {
            return
        }

        const timer = window.setInterval(() => {
            loadRunStatus(true)
        }, 3000)

        return () => window.clearInterval(timer)
    }, [agenticStatus?.is_running])

    const handleChooseFiles = (event: ChangeEvent<HTMLInputElement>) => {
        const nextFiles = Array.from(event.target.files || [])
        setSelectedFiles(nextFiles)
    }

    const handleUpload = async () => {
        if (selectedFiles.length === 0) {
            toast.error("Hãy chọn ít nhất một ảnh để tải lên")
            return
        }

        setIsUploading(true)
        try {
            const response = await uploadDebuggerSampleDocs(selectedFiles)
            setFiles(response.files)
            setSampleDocsPath(response.sample_docs_path)
            setSelectedFiles([])
            if (fileInputRef.current) {
                fileInputRef.current.value = ""
            }
            toast.success(`Đã tải lên ${response.upload_count} ảnh vào sample_docs`)
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Upload ảnh thất bại")
        } finally {
            setIsUploading(false)
        }
    }

    const handleDelete = async (filename: string) => {
        setDeletingFile(filename)
        try {
            const response = await deleteDebuggerSampleDoc(filename)
            setFiles(response.files)
            setSampleDocsPath(response.sample_docs_path)
            toast.success(`Đã xóa ${filename}`)
        } catch {
            toast.error("Không thể xóa ảnh debugger")
        } finally {
            setDeletingFile(null)
        }
    }

    const handleRunAgenticOcr = async () => {
        setIsStartingRun(true)
        try {
            const status = await runDebuggerAgenticOcr(runOptions)
            setAgenticStatus(status)
            toast.success("Đã bắt đầu chạy run_agentic_ocr.py")
        } catch (error) {
            toast.error(error instanceof Error ? error.message : "Không thể chạy run_agentic_ocr.py")
        } finally {
            setIsStartingRun(false)
        }
    }

    return (
        <div className="space-y-4 md:space-y-6">
            <div className="px-4 lg:px-6">
                <h1 className="text-2xl font-bold tracking-tight">Debugger</h1>
                <p className="text-sm text-muted-foreground">
                    Tải ảnh test vào <span className="font-mono">ai-pipeline/sample_docs</span> trực tiếp từ dashboard.
                </p>
            </div>

            <div className="grid gap-4 px-4 lg:px-6 xl:grid-cols-[1.05fr_1.4fr]">
                <div className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <FolderUpIcon className="size-5 text-primary" />
                                Upload Ảnh Debug
                            </CardTitle>
                            <CardDescription>
                                Chấp nhận <span className="font-mono">.jpg</span>, <span className="font-mono">.jpeg</span>, <span className="font-mono">.png</span>, <span className="font-mono">.webp</span>.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <label className="block rounded-2xl border border-dashed border-border bg-muted/20 p-6 text-center transition-colors hover:border-primary/40 hover:bg-primary/5">
                                <div className="mx-auto mb-3 flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                                    <UploadIcon className="size-5" />
                                </div>
                                <p className="text-sm font-medium">Chọn ảnh để đưa vào sample_docs</p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                    Bạn có thể chọn nhiều ảnh cùng lúc để test batch bằng <span className="font-mono">run_agentic_ocr.py</span>.
                                </p>
                                <Input
                                    ref={fileInputRef}
                                    type="file"
                                    multiple
                                    accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
                                    className="mt-4"
                                    onChange={handleChooseFiles}
                                />
                            </label>

                            <div className="flex flex-wrap items-center gap-2">
                                <Badge variant="secondary" className="rounded-full">
                                    {selectedFiles.length} file đã chọn
                                </Badge>
                                {sampleDocsPath && (
                                    <Badge variant="outline" className="rounded-full font-mono text-[11px]">
                                        {sampleDocsPath}
                                    </Badge>
                                )}
                            </div>

                            {selectedFiles.length > 0 && (
                                <div className="space-y-2 rounded-xl border bg-muted/20 p-3">
                                    {selectedFiles.map((file) => (
                                        <div key={`${file.name}-${file.size}`} className="flex items-center justify-between gap-3 text-sm">
                                            <div className="min-w-0">
                                                <p className="truncate font-medium">{file.name}</p>
                                                <p className="text-xs text-muted-foreground">{formatBytes(file.size)}</p>
                                            </div>
                                            <ImageIcon className="size-4 shrink-0 text-muted-foreground" />
                                        </div>
                                    ))}
                                </div>
                            )}

                            <div className="flex flex-wrap gap-2">
                                <Button onClick={handleUpload} disabled={isUploading || selectedFiles.length === 0}>
                                    <UploadIcon className="mr-2 size-4" />
                                    {isUploading ? "Đang tải lên..." : "Tải ảnh vào sample_docs"}
                                </Button>
                                <Button variant="outline" onClick={loadFiles} disabled={isUploading}>
                                    <RefreshCcwIcon className="mr-2 size-4" />
                                    Tải lại danh sách
                                </Button>
                            </div>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <SquareTerminalIcon className="size-5 text-primary" />
                                Chạy Batch Agentic OCR
                            </CardTitle>
                            <CardDescription>
                                Bấm nút để backend chạy <span className="font-mono">python run_agentic_ocr.py</span> trên toàn bộ ảnh trong <span className="font-mono">sample_docs</span>, rồi tự sync kết quả lên dashboard.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {isStatusLoading && !agenticStatus ? (
                                <div className="space-y-3">
                                    <Skeleton className="h-5 w-40" />
                                    <Skeleton className="h-24 w-full rounded-xl" />
                                </div>
                            ) : (
                                <>
                                    <div className="flex flex-wrap items-center gap-2">
                                        <Badge className={`rounded-full ${getRunStatusClass(agenticStatus?.status)}`}>
                                            {getRunStatusLabel(agenticStatus?.status)}
                                        </Badge>
                                        {agenticStatus?.output_json_exists && (
                                            <Badge variant="outline" className="rounded-full">
                                                output.json đã có
                                            </Badge>
                                        )}
                                        {agenticStatus?.pid && (
                                            <Badge variant="outline" className="rounded-full font-mono">
                                                PID {agenticStatus.pid}
                                            </Badge>
                                        )}
                                        <Badge variant="outline" className="rounded-full">
                                            YOLO: {agenticStatus?.use_yolo ? "On" : "Off"}
                                        </Badge>
                                        <Badge variant="outline" className="rounded-full">
                                            Selection: {agenticStatus?.enable_selection ? "On" : "Off"}
                                        </Badge>
                                        <Badge variant="outline" className="rounded-full">
                                            TTS: {agenticStatus?.enable_tts ? "On" : "Off"}
                                        </Badge>
                                    </div>

                                    <div className="rounded-xl border bg-muted/20 p-3 text-sm">
                                        <p className="font-medium">{agenticStatus?.message || "Chưa có trạng thái"}</p>
                                        <div className="mt-2 grid gap-2 text-xs text-muted-foreground">
                                            {agenticStatus?.started_at && (
                                                <p>Bắt đầu: <span className="font-mono">{formatDate(agenticStatus.started_at)}</span></p>
                                            )}
                                            {agenticStatus?.finished_at && (
                                                <p>Kết thúc: <span className="font-mono">{formatDate(agenticStatus.finished_at)}</span></p>
                                            )}
                                            {agenticStatus?.runner_script && (
                                                <p>Runner: <span className="font-mono break-all">{agenticStatus.runner_script}</span></p>
                                            )}
                                            {agenticStatus?.output_json_path && (
                                                <p>Output: <span className="font-mono break-all">{agenticStatus.output_json_path}</span></p>
                                            )}
                                        </div>
                                    </div>

                                    <div className="grid gap-3 rounded-xl border bg-muted/20 p-4">
                                        <div className="flex items-center justify-between gap-3">
                                            <div className="min-w-0">
                                                <Label htmlFor="debugger-use-yolo" className="font-medium">Dùng YOLO</Label>
                                                <p className="mt-1 text-xs text-muted-foreground">
                                                    Detect và crop nhiều price tag trước khi OCR.
                                                </p>
                                            </div>
                                            <Switch
                                                id="debugger-use-yolo"
                                                checked={runOptions.use_yolo}
                                                disabled={isStartingRun || !!agenticStatus?.is_running}
                                                onCheckedChange={(checked) =>
                                                    setRunOptions((prev) => ({ ...prev, use_yolo: Boolean(checked) }))
                                                }
                                            />
                                        </div>

                                        <div className="flex items-center justify-between gap-3">
                                            <div className="min-w-0">
                                                <Label htmlFor="debugger-enable-selection" className="font-medium">Chọn candidate bằng AI</Label>
                                                <p className="mt-1 text-xs text-muted-foreground">
                                                    Cho LLM chọn đúng price tag khớp với sản phẩm trong ảnh.
                                                </p>
                                            </div>
                                            <Switch
                                                id="debugger-enable-selection"
                                                checked={runOptions.enable_selection}
                                                disabled={isStartingRun || !!agenticStatus?.is_running}
                                                onCheckedChange={(checked) =>
                                                    setRunOptions((prev) => ({ ...prev, enable_selection: Boolean(checked) }))
                                                }
                                            />
                                        </div>

                                        <div className="flex items-center justify-between gap-3">
                                            <div className="min-w-0">
                                                <Label htmlFor="debugger-enable-tts" className="font-medium">Bật TTS</Label>
                                                <p className="mt-1 text-xs text-muted-foreground">
                                                    Tạo audio đầu ra sau khi pipeline chọn kết quả cuối.
                                                </p>
                                            </div>
                                            <Switch
                                                id="debugger-enable-tts"
                                                checked={runOptions.enable_tts}
                                                disabled={isStartingRun || !!agenticStatus?.is_running}
                                                onCheckedChange={(checked) =>
                                                    setRunOptions((prev) => ({ ...prev, enable_tts: Boolean(checked) }))
                                                }
                                            />
                                        </div>
                                    </div>

                                    <div className="flex flex-wrap gap-2">
                                        <Button
                                            onClick={handleRunAgenticOcr}
                                            disabled={isStartingRun || !!agenticStatus?.is_running}
                                        >
                                            <PlayIcon className="mr-2 size-4" />
                                            {isStartingRun
                                                ? "Đang gửi lệnh chạy..."
                                                : agenticStatus?.is_running
                                                    ? "Batch đang chạy..."
                                                    : "Chạy run_agentic_ocr.py"}
                                        </Button>
                                        <Button variant="outline" onClick={() => loadRunStatus()} disabled={isStartingRun}>
                                            <RefreshCcwIcon className="mr-2 size-4" />
                                            Tải lại trạng thái
                                        </Button>
                                    </div>

                                    <div className="space-y-2">
                                        <p className="text-sm font-medium">Log chạy gần nhất</p>
                                        <div className="max-h-80 overflow-auto rounded-xl border bg-black/95 p-3 font-mono text-xs leading-5 text-green-300">
                                            {agenticStatus?.log_lines?.length ? (
                                                <pre className="whitespace-pre-wrap break-words">
                                                    {agenticStatus.log_lines.join("\n")}
                                                </pre>
                                            ) : (
                                                <p className="text-muted-foreground">Chưa có log nào.</p>
                                            )}
                                        </div>
                                    </div>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </div>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <BugIcon className="size-5 text-primary" />
                            Ảnh Hiện Có Trong Debugger
                        </CardTitle>
                        <CardDescription>
                            Đây là danh sách ảnh đang nằm trong <span className="font-mono">sample_docs</span> để test pipeline batch.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? (
                            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                                {Array.from({ length: 6 }).map((_, index) => (
                                    <div key={index} className="space-y-2 rounded-2xl border p-3">
                                        <Skeleton className="aspect-[4/3] w-full rounded-xl" />
                                        <Skeleton className="h-4 w-2/3" />
                                        <Skeleton className="h-3 w-1/2" />
                                    </div>
                                ))}
                            </div>
                        ) : files.length === 0 ? (
                            <div className="rounded-2xl border border-dashed bg-muted/20 p-10 text-center">
                                <p className="text-sm font-medium">Chưa có ảnh debugger</p>
                                <p className="mt-1 text-xs text-muted-foreground">
                                    Upload ảnh ở khung bên trái để đẩy thẳng vào sample_docs.
                                </p>
                            </div>
                        ) : (
                            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                                {files.map((file) => (
                                    <div key={file.name} className="overflow-hidden rounded-2xl border bg-card">
                                        <div className="aspect-[4/3] overflow-hidden bg-muted/20">
                                            <img
                                                src={debuggerFileUrl(file.preview_url)}
                                                alt={file.name}
                                                className="h-full w-full object-cover"
                                                loading="lazy"
                                            />
                                        </div>
                                        <div className="space-y-3 p-3">
                                            <div className="min-w-0">
                                                <p className="truncate text-sm font-medium">{file.name}</p>
                                                <div className="mt-1 flex flex-wrap gap-2 text-xs text-muted-foreground">
                                                    <span>{formatBytes(file.size_bytes)}</span>
                                                    <span>{formatDate(file.modified_at)}</span>
                                                </div>
                                            </div>
                                            <div className="flex gap-2">
                                                <Button asChild variant="outline" size="sm" className="flex-1">
                                                    <a
                                                        href={debuggerFileUrl(file.preview_url)}
                                                        target="_blank"
                                                        rel="noreferrer"
                                                    >
                                                        <ImageIcon className="mr-2 size-4" />
                                                        Xem
                                                    </a>
                                                </Button>
                                                <Button
                                                    variant="destructive"
                                                    size="sm"
                                                    className="flex-1"
                                                    onClick={() => handleDelete(file.name)}
                                                    disabled={deletingFile === file.name}
                                                >
                                                    <Trash2Icon className="mr-2 size-4" />
                                                    {deletingFile === file.name ? "Đang xóa..." : "Xóa"}
                                                </Button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
