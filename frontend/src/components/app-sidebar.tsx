import * as React from "react"
import { NavLink, useLocation } from "react-router-dom"

import { NavMain } from "@/components/nav-main"
import { NavSecondary } from "@/components/nav-secondary"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import {
  LayoutDashboardIcon,
  ScrollTextIcon,
  BarChart3Icon,
  ScanEyeIcon,
  CircleHelpIcon,
  MoonIcon,
  SunIcon,
  RefreshCcwIcon
} from "lucide-react"
import { useTheme } from "@/components/theme-provider"
import { usePollMode } from "@/lib/poll-context"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { PollMode } from "@/types"

const navItems = [
  { title: "Dashboard", url: "/", icon: LayoutDashboardIcon },
  { title: "Lịch sử", url: "/history", icon: ScrollTextIcon },
  { title: "Phân tích", url: "/analytics", icon: BarChart3Icon },
]

export function AppSidebar({
  ...props
}: React.ComponentProps<typeof Sidebar>) {
  const location = useLocation()
  const { theme, setTheme } = useTheme()
  const { pollMode, setPollMode } = usePollMode()

  const navMain = navItems.map((item) => ({
    ...item,
    isActive:
      item.url === "/"
        ? location.pathname === "/"
        : location.pathname.startsWith(item.url),
  }))

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader className="h-16 border-b border-sidebar-border/50 px-4 justify-center">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:p-0! bg-transparent hover:bg-transparent"
            >
              <NavLink to="/" className="flex items-center gap-2">
                <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground shrink-0">
                  <ScanEyeIcon className="size-4!" />
                </div>
                <span className="text-base font-bold tracking-tight">ShopMonitor</span>
              </NavLink>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={navMain} />
        <NavSecondary
          items={[
            {
              title:
                theme === "dark" ? "Chế độ sáng" : "Chế độ tối",
              url: "#",
              icon: theme === "dark" ? SunIcon : MoonIcon,
              onClick: () =>
                setTheme(theme === "dark" ? "light" : "dark"),
            },
            { title: "Trợ giúp", url: "#", icon: CircleHelpIcon },
          ]}
          className="mt-auto"
        />
      </SidebarContent>
      <SidebarFooter className="p-4 pt-0">
        <label className="text-xs text-muted-foreground font-medium mb-1 pl-1">Tự động làm mới</label>
        <Select value={pollMode} onValueChange={(val: PollMode) => setPollMode(val)}>
          <SelectTrigger className="w-full h-11 text-[14px] bg-sidebar-accent/50 hover:bg-sidebar-accent border-sidebar-border/30 rounded-lg">
            <div className="flex items-center gap-2">
              <RefreshCcwIcon className="size-4 text-muted-foreground mr-1" />
              <SelectValue placeholder="Tự động tải" />
            </div>
          </SelectTrigger>
          <SelectContent align="center">
            <SelectItem value="realtime">5 giây (Nhanh)</SelectItem>
            <SelectItem value="slow">30 giây (Chậm)</SelectItem>
            <SelectItem value="off">Tắt tự động</SelectItem>
          </SelectContent>
        </Select>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
