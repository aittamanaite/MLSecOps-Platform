import { Routes, Route } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { InspectorPage } from './pages/InspectorPage'
import { BatchPage } from './pages/BatchPage'
import { AlertsPage } from './pages/AlertsPage'
import { StatusPage } from './pages/StatusPage'
import { SettingsPage } from './pages/SettingsPage'

export function AppRouter() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/inspect" element={<InspectorPage />} />
        <Route path="/batch" element={<BatchPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/status" element={<StatusPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </AppShell>
  )
}
