import type { CSSProperties } from "react"

export const CATEGORY_OPTIONS = [
    { value: "", label: "Tất cả" },
    { value: "dairy", label: "Sữa" },
    { value: "snack", label: "Bánh kẹo" },
    { value: "beverage", label: "Nước uống" },
    { value: "bakery", label: "Bánh mì" },
    { value: "condiment", label: "Gia vị" },
    { value: "personal_care", label: "Chăm sóc cá nhân" },
    { value: "household", label: "Đồ gia dụng" },
    { value: "other", label: "Khác" },
] as const

export const CATEGORY_COLORS: Record<string, string> = {
    dairy: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
    beverage: "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400",
    snack: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
    bakery: "bg-orange-500/10 text-orange-600 dark:text-orange-400",
    condiment: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
    personal_care: "bg-[#DB2777]/10 text-[#DB2777] dark:text-[#DB2777]",
    household: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
    other: "bg-slate-500/10 text-slate-600 dark:text-slate-400",
}

export const CATEGORY_CHART_COLORS: Record<string, string> = {
    dairy: "#2563EB",
    beverage: "#0891B2",
    snack: "#D97706",
    bakery: "#C4A77D",
    condiment: "#7C3AED",
    personal_care: "#DB2777",
    household: "#4F46E5",
    other: "#8A8A7A",
    unknown: "#8A8A7A",
}

const CATEGORY_BADGE_STYLES: Record<string, CSSProperties> = {
    personal_care: {
        backgroundColor: "rgb(219 39 119 / 0.12)",
        color: "#DB2777",
    },
}

export function getCategoryLabel(category?: string | null): string {
    if (!category) {
        return "Chưa phân loại"
    }
    return CATEGORY_OPTIONS.find((option) => option.value === category)?.label || category
}

export function getCategoryBadgeStyle(category?: string | null): CSSProperties | undefined {
    if (!category) {
        return undefined
    }
    return CATEGORY_BADGE_STYLES[category]
}
