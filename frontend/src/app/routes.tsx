import { Navigate, Route, Routes } from 'react-router-dom'

import { DashboardRoute } from '@/pages/dashboard/DashboardPage'
import { IntakeRoute } from '@/pages/intake/IntakePage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardRoute />} />
      <Route path="/intake" element={<IntakeRoute />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
