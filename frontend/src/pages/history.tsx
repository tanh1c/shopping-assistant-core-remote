import { useEffect, useState } from "react"
import { fetchLogs, deleteLog, updateLog } from "@/lib/api"
import type { LogEntry } from "@/types"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from "@/components/ui/dialog"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
    SearchIcon,
    AlertTriangleIcon,
    Trash2,
    PackageIcon,
    MoreHorizontal,
    Pencil,
} from "lucide-react"
import { toast } from "sonner"
import { CATEGORY_COLORS, CATEGORY_OPTIONS, getCategoryBadgeStyle, getCategoryLabel } from "@/lib/categories"

function confClass(c: number) {
    if (c >= 0.9) return "bg-green-500"
    if (c >= 0.7) return "bg-amber-500"
    return "bg-red-500"
}

export default function HistoryPage() {
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [search, setSearch] = useState("")
    const [warnOnly, setWarnOnly] = useState(false)
    const [selected, setSelected] = useState<LogEntry | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [deleteConfirm, setDeleteConfirm] = useState<LogEntry | null>(null)
    const [editDialog, setEditDialog] = useState<LogEntry | null>(null)
    const [editForm, setEditForm] = useState<Partial<LogEntry>>({})

    const loadLogs = async () => {
        setIsLoading(true)
        try {
            const data = await fetchLogs({ limit: 100 })
            setLogs(data)
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        loadLogs()
    }, [])

    const filtered = logs.filter((l) => {
        if (warnOnly && !l.warning_flag) return false
        if (search) {
            const q = search.toLowerCase()
            if (
                !l.detected_object.toLowerCase().includes(q) &&
                !(l.category || "").toLowerCase().includes(q)
            )
                return false
        }
        return true
    })

    const handleDelete = async (log: LogEntry) => {
        try {
            await deleteLog(log.log_id)
            toast.success("Đã xóa sản phẩm thành công")
            loadLogs()
        } catch {
            toast.error("Không thể xóa sản phẩm")
        }
        setDeleteConfirm(null)
    }

    const handleUpdate = async () => {
        if (!editDialog) return
        try {
            const payload: any = { ...editForm }
            if (payload.category === null) payload.category = undefined
            await updateLog(editDialog.log_id, payload)
            toast.success("Cập nhật hoạt động thành công")
            loadLogs()
            setEditDialog(null)
        } catch {
            toast.error("Lỗi khi cập nhật sản phẩm")
        }
    }

    return (
        <div className="space-y-4 md:space-y-6">
            <div className="flex items-center justify-between px-4 lg:px-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight">Lịch sử quét</h1>
                    <p className="text-sm text-muted-foreground">
                        Toàn bộ {logs.length} lượt quét sản phẩm
                    </p>
                </div>
            </div>

            {/* toolbar */}
            <div className="flex flex-col sm:flex-row flex-wrap sm:items-center gap-3 px-4 lg:px-6">
                <div className="relative flex-1 w-full sm:max-w-xs min-w-[200px]">
                    <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
                    <Input
                        placeholder="Tìm sản phẩm..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="pl-9"
                    />
                </div>
                <button
                    onClick={() => setWarnOnly(!warnOnly)}
                    className={`inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors cursor-pointer ${warnOnly
                        ? "border-red-300 bg-red-50 text-red-600 dark:border-red-800 dark:bg-red-950/40 dark:text-red-400"
                        : "border-border text-muted-foreground hover:text-foreground hover:bg-muted/50"
                        }`}
                >
                    <AlertTriangleIcon className="size-3" />
                    Chỉ cảnh báo
                </button>
            </div>

            {/* desktop table */}
            <div className="hidden md:block px-4 lg:px-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Toàn bộ Lịch sử</CardTitle>
                        <CardDescription>Danh sách chi tiết các mặt hàng đã được hệ thống ghi nhận.</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Thời gian</TableHead>
                                    <TableHead>Sản phẩm</TableHead>
                                    <TableHead className="hidden sm:table-cell">Loại</TableHead>
                                    <TableHead className="hidden md:table-cell">Giá</TableHead>
                                    <TableHead className="hidden lg:table-cell">Nguồn</TableHead>
                                    <TableHead className="hidden sm:table-cell">AI %</TableHead>
                                    <TableHead>Trạng thái</TableHead>
                                    <TableHead>
                                        <span className="sr-only">Thao tác</span>
                                    </TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {isLoading
                                    ? Array.from({ length: 5 }).map((_, i) => (
                                        <TableRow key={i}>
                                            {Array.from({ length: 8 }).map((_, j) => (
                                                <TableCell key={j}>
                                                    <Skeleton className="h-4 w-16" />
                                                </TableCell>
                                            ))}
                                        </TableRow>
                                    ))
                                    : filtered.map((log) => (
                                        <TableRow
                                            key={log.log_id}
                                            onClick={() => setSelected(log)}
                                            className={`cursor-pointer transition-colors ${log.warning_flag
                                                ? "bg-red-50/60 dark:bg-red-950/20 border-l-2 border-l-red-500"
                                                : ""
                                                }`}
                                        >
                                            <TableCell className="whitespace-nowrap font-mono text-sm">
                                                {log.timestamp.slice(11, 16)}
                                                <br />
                                                <span className="text-[11px] text-muted-foreground">
                                                    {log.timestamp.slice(5, 10)}
                                                </span>
                                            </TableCell>
                                            <TableCell>
                                                <div className="font-medium">
                                                    {log.detected_object}
                                                </div>
                                                {log.ocr_text && (
                                                    <div className="text-[11px] font-mono text-muted-foreground truncate max-w-[200px]">
                                                        {log.ocr_text}
                                                    </div>
                                                )}
                                            </TableCell>
                                            <TableCell className="hidden sm:table-cell">
                                                {log.category && (
                                                    <Badge
                                                        variant="secondary"
                                                        className={`text-[10px] font-semibold ${CATEGORY_COLORS[log.category] || ""}`}
                                                        style={getCategoryBadgeStyle(log.category)}
                                                    >
                                                        {getCategoryLabel(log.category)}
                                                    </Badge>
                                                )}
                                            </TableCell>
                                            <TableCell className="font-mono text-sm hidden md:table-cell">
                                                {log.price || "—"}
                                            </TableCell>
                                            <TableCell className="font-mono text-xs hidden lg:table-cell text-muted-foreground">
                                                {log.source_image || log.selected_crop_name || "—"}
                                            </TableCell>
                                            <TableCell className="hidden sm:table-cell">
                                                <div className="w-14 space-y-0.5">
                                                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                                                        <div
                                                            className={`h-full rounded-full ${confClass(log.confidence_score)}`}
                                                            style={{
                                                                width: `${log.confidence_score * 100}%`,
                                                            }}
                                                        />
                                                    </div>
                                                    <span className="font-mono text-[11px] font-semibold text-muted-foreground">
                                                        {Math.round(log.confidence_score * 100)}%
                                                    </span>
                                                </div>
                                            </TableCell>
                                            <TableCell>
                                                {log.warning_flag ? (
                                                    <Badge variant="destructive" className="text-[10px]">
                                                        <AlertTriangleIcon className="size-3 mr-1" />
                                                        Cảnh báo
                                                    </Badge>
                                                ) : (
                                                    <Badge
                                                        variant="secondary"
                                                        className="text-[10px] bg-green-500/10 text-green-600 dark:text-green-400"
                                                    >
                                                        OK
                                                    </Badge>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                <DropdownMenu>
                                                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                                                        <Button aria-haspopup="true" size="icon" variant="ghost">
                                                            <MoreHorizontal className="h-4 w-4" />
                                                            <span className="sr-only">Toggle menu</span>
                                                        </Button>
                                                    </DropdownMenuTrigger>
                                                    <DropdownMenuContent align="end">
                                                        <DropdownMenuLabel>Hành động</DropdownMenuLabel>
                                                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); setSelected(log); }}>
                                                            <SearchIcon className="mr-2 h-4 w-4" /> Chi tiết
                                                        </DropdownMenuItem>
                                                        <DropdownMenuItem onClick={(e) => { e.stopPropagation(); setEditDialog(log); setEditForm(log); }}>
                                                            <Pencil className="mr-2 h-4 w-4" /> Sửa
                                                        </DropdownMenuItem>
                                                        <DropdownMenuSeparator />
                                                        <DropdownMenuItem className="text-red-600 focus:bg-red-50 focus:text-red-600" onClick={(e) => { e.stopPropagation(); setDeleteConfirm(log); }}>
                                                            <Trash2 className="mr-2 h-4 w-4" /> Xóa
                                                        </DropdownMenuItem>
                                                    </DropdownMenuContent>
                                                </DropdownMenu>
                                            </TableCell>
                                        </TableRow>
                                    ))}
                                {!isLoading && filtered.length === 0 && (
                                    <TableRow>
                                        <TableCell
                                            colSpan={8}
                                            className="text-center py-12 text-muted-foreground"
                                        >
                                            Không tìm thấy sản phẩm
                                        </TableCell>
                                    </TableRow>
                                )}
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>

            {/* mobile list */}
            <div className="md:hidden space-y-2 px-4">
                {isLoading
                    ? Array.from({ length: 5 }).map((_, i) => (
                        <div
                            key={i}
                            className="flex items-center gap-3 rounded-xl border px-3 py-2.5"
                        >
                            <Skeleton className="size-9 rounded-lg shrink-0" />
                            <div className="flex-1 space-y-1.5">
                                <Skeleton className="h-3.5 w-3/4" />
                                <Skeleton className="h-2.5 w-1/2" />
                            </div>
                        </div>
                    ))
                    : filtered.map((log) => (
                        <div
                            key={log.log_id}
                            onClick={() => setSelected(log)}
                            className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 cursor-pointer transition-colors hover:bg-muted/40 ${log.warning_flag
                                ? "border-red-200 bg-red-50/50 dark:border-red-900/40 dark:bg-red-950/20"
                                : ""
                                }`}
                        >
                            <div
                                className={`flex size-9 items-center justify-center rounded-lg shrink-0 ${log.warning_flag
                                    ? "bg-red-500/10 text-red-600"
                                    : "bg-primary/10 text-primary"
                                    }`}
                            >
                                {log.warning_flag ? (
                                    <AlertTriangleIcon className="size-4" />
                                ) : (
                                    <PackageIcon className="size-4" />
                                )}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm font-medium truncate">
                                    {log.detected_object}
                                </p>
                                <div className="flex items-center gap-2 mt-0.5">
                                    <span className="font-mono text-[11px] text-muted-foreground">
                                        {log.timestamp.slice(11, 16)}
                                    </span>
                                    {log.category && (
                                        <Badge
                                            variant="secondary"
                                            className={`text-[9px] h-4 ${CATEGORY_COLORS[log.category] || ""}`}
                                            style={getCategoryBadgeStyle(log.category)}
                                        >
                                            {getCategoryLabel(log.category)}
                                        </Badge>
                                    )}
                                    <span className="font-mono text-[11px] text-muted-foreground ml-auto">
                                        {log.price || "—"}
                                    </span>
                                </div>
                            </div>
                        </div>
                    ))}
                {!isLoading && filtered.length === 0 && (
                    <div className="text-center py-16 text-muted-foreground bg-muted/20 rounded-xl border border-dashed">
                        <p className="text-sm">Chưa có dữ liệu</p>
                    </div>
                )}
            </div>

            {/* detail dialog */}
            <Dialog
                open={!!selected}
                onOpenChange={(o) => !o && setSelected(null)}
            >
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>{selected?.detected_object}</DialogTitle>
                        <DialogDescription className="sr-only">Chi tiết lượt quét sản phẩm</DialogDescription>
                    </DialogHeader>
                    {selected && (
                        <div className="space-y-4 text-sm">
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <p className="text-muted-foreground text-xs">Thời gian</p>
                                    <p className="font-mono">{selected.timestamp}</p>
                                </div>
                                <div>
                                    <p className="text-muted-foreground text-xs">Loại</p>
                                    <p>{getCategoryLabel(selected.category)}</p>
                                </div>
                                <div>
                                    <p className="text-muted-foreground text-xs">Giá</p>
                                    <p className="font-mono">{selected.price || "N/A"}</p>
                                </div>
                                <div>
                                    <p className="text-muted-foreground text-xs">Ảnh nguồn</p>
                                    <p className="font-mono">
                                        {selected.source_image || "N/A"}
                                    </p>
                                </div>
                            </div>
                            {selected.price_tag_text_normalized && (
                                <div>
                                    <p className="text-muted-foreground text-xs mb-1">
                                        Price Tag Đã Chuẩn Hóa
                                    </p>
                                    <p className="text-xs bg-muted rounded p-2 break-all">
                                        {selected.price_tag_text_normalized}
                                    </p>
                                </div>
                            )}
                            {(selected.product_name_source || selected.selected_crop_name) && (
                                <div className="grid grid-cols-2 gap-3">
                                    <div>
                                        <p className="text-muted-foreground text-xs">Nguồn tên</p>
                                        <p className="font-mono text-xs break-all">
                                            {selected.product_name_source || "N/A"}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-muted-foreground text-xs">Crop được chọn</p>
                                        <p className="font-mono text-xs break-all">
                                            {selected.selected_crop_name || "N/A"}
                                        </p>
                                    </div>
                                </div>
                            )}
                            {selected.selection_reason && (
                                <div>
                                    <p className="text-muted-foreground text-xs mb-1">
                                        Lý do chọn tag
                                    </p>
                                    <p className="text-xs bg-muted rounded p-2">
                                        {selected.selection_reason}
                                    </p>
                                </div>
                            )}
                            {selected.warning_reason && (
                                <div className="rounded-lg border border-red-200 bg-red-50 dark:border-red-900/50 dark:bg-red-950/30 p-3">
                                    <p className="text-xs font-semibold text-red-600 dark:text-red-400">
                                        Lý do cảnh báo
                                    </p>
                                    <p className="text-xs mt-1">{selected.warning_reason}</p>
                                </div>
                            )}
                            <div className="flex gap-2">
                                <Button
                                    variant="destructive"
                                    className="flex-1"
                                    onClick={() => {
                                        setDeleteConfirm(selected)
                                        setSelected(null)
                                    }}
                                >
                                    <Trash2 className="size-4 mr-2" />
                                    Xóa
                                </Button>
                            </div>
                        </div>
                    )}
                </DialogContent>
            </Dialog>

            {/* delete confirm dialog */}
            <Dialog
                open={!!deleteConfirm}
                onOpenChange={(o) => !o && setDeleteConfirm(null)}
            >
                <DialogContent className="max-w-sm">
                    <DialogHeader>
                        <DialogTitle>Xác nhận xóa</DialogTitle>
                        <DialogDescription className="sr-only">Xác nhận xóa sản phẩm khỏi lịch sử</DialogDescription>
                    </DialogHeader>
                    <p className="text-sm text-muted-foreground">
                        Bạn có chắc muốn xóa{" "}
                        <strong>{deleteConfirm?.detected_object}</strong>?
                    </p>
                    <div className="flex gap-2 mt-4">
                        <Button
                            variant="outline"
                            className="flex-1"
                            onClick={() => setDeleteConfirm(null)}
                        >
                            Hủy
                        </Button>
                        <Button
                            variant="destructive"
                            className="flex-1"
                            onClick={() => deleteConfirm && handleDelete(deleteConfirm)}
                        >
                            Xóa
                        </Button>
                    </div>
                </DialogContent>
            </Dialog>

            <EditDialog
                open={!!editDialog}
                onOpenChange={(open) => !open && setEditDialog(null)}
                log={editDialog}
                editForm={editForm}
                setEditForm={setEditForm}
                onSave={handleUpdate}
            />
        </div>
    )
}

function EditDialog({
    open,
    onOpenChange,
    log,
    editForm,
    setEditForm,
    onSave,
}: {
    open: boolean
    onOpenChange: (open: boolean) => void
    log: LogEntry | null
    editForm: Partial<LogEntry>
    setEditForm: (val: Partial<LogEntry>) => void
    onSave: () => void
}) {
    if (!log) return null
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Chỉnh sửa: {log.detected_object}</DialogTitle>
                    <DialogDescription className="sr-only">Chỉnh sửa thông tin lịch sử quét</DialogDescription>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid gap-2">
                        <label className="text-sm font-medium">Tên sản phẩm</label>
                        <Input
                            value={editForm.detected_object || ""}
                            onChange={(e) => setEditForm({ ...editForm, detected_object: e.target.value })}
                        />
                    </div>
                    <div className="grid gap-2">
                        <label className="text-sm font-medium">Giá</label>
                        <Input
                            value={editForm.price || ""}
                            onChange={(e) => setEditForm({ ...editForm, price: e.target.value })}
                        />
                    </div>
                    <div className="grid gap-2">
                        <label className="text-sm font-medium">Phân loại</label>
                        <select
                            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                            value={editForm.category || ""}
                            onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                        >
                            {CATEGORY_OPTIONS.map((c) => (
                                <option key={c.value} value={c.value} className="text-background">{c.label || "Chưa phân loại"}</option>
                            ))}
                        </select>
                    </div>
                    <div className="grid gap-2">
                        <label className="flex items-center gap-2 text-sm font-medium cursor-pointer">
                            <input
                                type="checkbox"
                                checked={!!editForm.warning_flag}
                                onChange={(e) => setEditForm({ ...editForm, warning_flag: e.target.checked })}
                                className="accent-red-600 size-4"
                            />
                            Bật cảnh báo
                        </label>
                    </div>
                    {editForm.warning_flag && (
                        <div className="grid gap-2">
                            <label className="text-sm font-medium text-red-600">Lý do cảnh báo</label>
                            <Input
                                value={editForm.warning_reason || ""}
                                onChange={(e) => setEditForm({ ...editForm, warning_reason: e.target.value })}
                                placeholder="Nhập lý do cảnh báo..."
                            />
                        </div>
                    )}
                </div>
                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Hủy
                    </Button>
                    <Button onClick={onSave}>
                        Lưu thay đổi
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    )
}
