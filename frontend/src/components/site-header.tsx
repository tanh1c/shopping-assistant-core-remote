import { useLocation } from "react-router-dom"
import { Separator } from "@/components/ui/separator"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { ScanEyeIcon } from "lucide-react"

const pageTitles: Record<string, string> = {
  "/": "Dashboard",
  "/history": "Lịch sử quét",
  "/analytics": "Phân tích",
}

export function SiteHeader() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || "Shopping Monitor"

  return (
    <header className="flex h-16 shrink-0 items-center justify-between gap-2 border-b px-4 lg:px-6 sticky top-0 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 z-30 transition-[width,height] ease-linear">
      <div className="flex items-center gap-2">
        <SidebarTrigger className="-ml-1" />
        <Separator
          orientation="vertical"
          className="mr-2 hidden md:block"
        />
        <h1 className="text-base font-semibold hidden md:flex items-center tracking-tight text-foreground/90">{title}</h1>
      </div>

      {/* mobile brand */}
      <div className="md:hidden flex items-center gap-2">
        <div className="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <ScanEyeIcon className="size-3.5" />
        </div>
        <span className="text-sm font-bold tracking-tight">ShopMonitor</span>
      </div>
    </header>
  )
}
