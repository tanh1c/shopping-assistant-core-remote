import { useEffect, useState } from "react"
import { fetchLogs, fetchStats } from "@/lib/api"
import type { LogEntry, Stats } from "@/types"
import {
    Card,
    CardAction,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
    ChartContainer,
    ChartTooltip,
    ChartTooltipContent,
    ChartLegend,
    ChartLegendContent,
    type ChartConfig,
} from "@/components/ui/chart"
import {
    PackageIcon,
    ShieldAlertIcon,
    BrainIcon,
    TrophyIcon,
    TrendingUpIcon,
} from "lucide-react"
import {
    PieChart,
    Pie,
    Cell,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
} from "recharts"
import { CATEGORY_CHART_COLORS, getCategoryLabel } from "@/lib/categories"

export default function AnalyticsPage() {
    const [logs, setLogs] = useState<LogEntry[]>([])
    const [stats, setStats] = useState<Stats | null>(null)
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        Promise.all([fetchLogs({ limit: 100 }), fetchStats()])
            .then(([l, s]) => {
                setLogs(l)
                setStats(s)
            })
            .finally(() => setIsLoading(false))
    }, [])

    // Category breakdown
    const catCounts: Record<string, number> = {}
    logs.forEach((l) => {
        const cat = l.category || "unknown"
        catCounts[cat] = (catCounts[cat] || 0) + 1
    })
    const catData = Object.entries(catCounts)
        .sort(([, a], [, b]) => b - a)
        .map(([name, count]) => ({
            name,
            label: getCategoryLabel(name),
            count,
            fill: CATEGORY_CHART_COLORS[name] || "#888",
        }))

    const pieConfig: ChartConfig = Object.fromEntries(
        catData.map((c) => [c.name, { label: c.label, color: c.fill }])
    )

    // Confidence distribution
    const high = logs.filter((l) => l.confidence_score >= 0.9).length
    const mid = logs.filter(
        (l) => l.confidence_score >= 0.7 && l.confidence_score < 0.9
    ).length
    const low = logs.filter((l) => l.confidence_score < 0.7).length
    const confData = [
        { range: "≥90%", count: high, fill: "var(--color-chart-1)" },
        { range: "70-89%", count: mid, fill: "var(--color-chart-3)" },
        { range: "<70%", count: low, fill: "var(--color-chart-5)" },
    ]
    const barConfig: ChartConfig = {
        count: { label: "Số lượng", color: "var(--color-chart-1)" },
    }

    const warnPct = stats
        ? Math.round((stats.warning_count / Math.max(stats.total_logs, 1)) * 100)
        : 0

    return (
        <div className="space-y-4 md:space-y-6">
            <div className="px-4 lg:px-6">
                <h1 className="text-2xl font-bold tracking-tight">Phân tích</h1>
                <p className="text-sm text-muted-foreground">
                    Thống kê và phân tích dữ liệu mua sắm
                </p>
            </div>

            {/* stat cards */}
            <div className="grid grid-cols-2 gap-2 px-4 *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
                {isLoading ? (
                    Array.from({ length: 4 }).map((_, i) => (
                        <Card key={i} className="@container/card">
                            <CardHeader>
                                <Skeleton className="h-3 w-20" />
                                <Skeleton className="h-8 w-24" />
                            </CardHeader>
                            <CardFooter>
                                <Skeleton className="h-3 w-32" />
                            </CardFooter>
                        </Card>
                    ))
                ) : stats ? (
                    <>
                        <Card className="@container/card">
                            <CardHeader>
                                <CardDescription className="flex items-center gap-1.5">
                                    <PackageIcon className="size-3.5 text-blue-600" />
                                    Tổng quét
                                </CardDescription>
                                <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                                    {stats.total_logs}
                                </CardTitle>
                                <CardAction>
                                    <Badge variant="outline">
                                        <TrendingUpIcon />
                                        {stats.total_logs}
                                    </Badge>
                                </CardAction>
                            </CardHeader>
                            <CardFooter className="text-sm">
                                <div className="text-muted-foreground">
                                    sản phẩm đã nhận dạng
                                </div>
                            </CardFooter>
                        </Card>
                        <Card className="@container/card">
                            <CardHeader>
                                <CardDescription className="flex items-center gap-1.5">
                                    <ShieldAlertIcon className="size-3.5 text-red-600" />
                                    Cảnh báo
                                </CardDescription>
                                <CardTitle className="text-2xl font-semibold tabular-nums text-red-600 @[250px]/card:text-3xl">
                                    {stats.warning_count}
                                </CardTitle>
                                <CardAction>
                                    <Badge variant="outline">{warnPct}% tổng quét</Badge>
                                </CardAction>
                            </CardHeader>
                            <CardFooter className="text-sm">
                                <div className="text-muted-foreground">sản phẩm cần chú ý</div>
                            </CardFooter>
                        </Card>
                        <Card className="@container/card">
                            <CardHeader>
                                <CardDescription className="flex items-center gap-1.5">
                                    <BrainIcon className="size-3.5 text-green-600" />
                                    Tin cậy TB
                                </CardDescription>
                                <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
                                    {Math.round(stats.avg_confidence * 100)}%
                                </CardTitle>
                                <CardAction>
                                    <Badge variant="outline">
                                        <TrendingUpIcon />
                                        Tốt
                                    </Badge>
                                </CardAction>
                            </CardHeader>
                            <CardFooter className="text-sm">
                                <div className="text-muted-foreground">
                                    độ chính xác trung bình
                                </div>
                            </CardFooter>
                        </Card>
                        <Card className="@container/card">
                            <CardHeader>
                                <CardDescription className="flex items-center gap-1.5">
                                    <TrophyIcon className="size-3.5 text-amber-600" />
                                    Top sản phẩm
                                </CardDescription>
                                <CardTitle className="text-base sm:text-xl font-semibold truncate @[250px]/card:text-2xl">
                                    {stats.top_product || "N/A"}
                                </CardTitle>
                            </CardHeader>
                            <CardFooter className="text-sm">
                                <div className="text-muted-foreground">
                                    sản phẩm quét nhiều nhất
                                </div>
                            </CardFooter>
                        </Card>
                    </>
                ) : null}
            </div>

            {/* charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 px-4 lg:px-6">
                {/* pie chart */}
                <Card>
                    <CardHeader>
                        <CardTitle>Phân bổ sản phẩm</CardTitle>
                        <CardDescription>Theo nhóm thực phẩm</CardDescription>
                    </CardHeader>
                    <div className="p-4 pt-0">
                        {isLoading ? (
                            <Skeleton className="h-[250px] w-full rounded-lg" />
                        ) : (
                            <ChartContainer config={pieConfig} className="h-[280px] w-full">
                                <PieChart>
                                    <ChartTooltip content={<ChartTooltipContent />} />
                                    <Pie
                                        data={catData}
                                        dataKey="count"
                                        nameKey="label"
                                        cx="50%"
                                        cy="50%"
                                        outerRadius={90}
                                        innerRadius={50}
                                        paddingAngle={2}
                                    >
                                        {catData.map((d, i) => (
                                            <Cell key={i} fill={d.fill} />
                                        ))}
                                    </Pie>
                                    <ChartLegend content={<ChartLegendContent />} />
                                </PieChart>
                            </ChartContainer>
                        )}
                    </div>
                </Card>

                {/* bar chart */}
                <Card>
                    <CardHeader>
                        <CardTitle>Phân bổ độ tin cậy</CardTitle>
                        <CardDescription>
                            Mức AI Confidence Score
                        </CardDescription>
                    </CardHeader>
                    <div className="p-4 pt-0">
                        {isLoading ? (
                            <Skeleton className="h-[250px] w-full rounded-lg" />
                        ) : (
                            <ChartContainer config={barConfig} className="h-[280px] w-full">
                                <BarChart data={confData}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                    <XAxis dataKey="range" />
                                    <YAxis allowDecimals={false} />
                                    <ChartTooltip content={<ChartTooltipContent />} />
                                    <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                                        {confData.map((d, i) => (
                                            <Cell key={i} fill={d.fill} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ChartContainer>
                        )}
                    </div>
                </Card>
            </div>
        </div>
    )
}
