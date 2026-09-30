import { Navigate, Route, Routes } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useSession } from './lib/session'
import { Layout } from './components/Layout'
import { PageContainer } from './components/PageContainer'
import { SignInPage } from './pages/SignInPage'
import { CommandCenterPage } from './pages/CommandCenterPage'
import { CasesPage } from './pages/CasesPage'
import { CaseDetailPage } from './pages/CaseDetailPage'
import { DocumentsTab } from './pages/FilingPackageTabs'
import { RequirementsTab, ChecklistTab } from './pages/RequirementsChecklistTabs'
import { DefectsTab } from './pages/DefectsTab'
import { ObjectionsTab, CorrectionsTab } from './pages/ObjectionsCorrectionsTabs'
import { ReviewQueueTab, AuditTab } from './pages/ReviewAuditTabs'

function RequireSession({ children }: { children: ReactNode }) {
  const { user } = useSession()
  if (!user) return <Navigate to="/sign-in" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/sign-in" element={<SignInPage />} />
      <Route
        path="/"
        element={
          <RequireSession>
            <Layout />
          </RequireSession>
        }
      >
        <Route index element={<CommandCenterPage />} />
        <Route path="cases" element={<CasesPage />} />
        <Route path="cases/:caseId" element={<CaseDetailPage />} />
        <Route path="packages/:packageId/documents" element={<PageContainer><DocumentsTab /></PageContainer>} />
        <Route path="packages/:packageId/requirements" element={<PageContainer><RequirementsTab /></PageContainer>} />
        <Route path="packages/:packageId/checklist" element={<PageContainer><ChecklistTab /></PageContainer>} />
        <Route path="packages/:packageId/defects" element={<PageContainer><DefectsTab /></PageContainer>} />
        <Route path="packages/:packageId/objections" element={<PageContainer><ObjectionsTab /></PageContainer>} />
        <Route path="packages/:packageId/corrections" element={<PageContainer><CorrectionsTab /></PageContainer>} />
        <Route path="packages/:packageId/review-queue" element={<PageContainer><ReviewQueueTab /></PageContainer>} />
        <Route path="packages/:packageId/audit" element={<PageContainer><AuditTab /></PageContainer>} />
      </Route>
    </Routes>
  )
}
