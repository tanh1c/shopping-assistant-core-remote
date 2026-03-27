import { BrowserRouter, Routes, Route, Outlet } from "react-router-dom"
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { Toaster } from "@/components/ui/sonner"
import { PollProvider } from "@/lib/poll-context"
import DashboardPage from "@/pages/dashboard"
import HistoryPage from "@/pages/history"
import AnalyticsPage from "@/pages/analytics"
import DebuggerPage from "@/pages/debugger"

function AppLayout() {
  return (
    <PollProvider>
      <SidebarProvider>
        <AppSidebar variant="inset" />
        <SidebarInset>
          <SiteHeader />
          <div className="flex flex-1 flex-col pt-4 md:pt-6">
            <div className="@container/main flex flex-1 flex-col gap-4 md:gap-6">
              <div className="flex-1 pb-10">
                <Outlet />
              </div>
            </div>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </PollProvider>
  )
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/debugger" element={<DebuggerPage />} />
        </Route>
      </Routes>
      <Toaster richColors position="top-right" />
    </BrowserRouter>
  )
}

export default App
