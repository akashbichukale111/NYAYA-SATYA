import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useCase } from './hooks'
import { CaseExplorer } from './screens/CaseExplorer'
import { CommandCenter } from './screens/CommandCenter'
import { EvidenceExplorer } from './screens/EvidenceExplorer'
import { ClaimsExplorer } from './screens/ClaimsExplorer'
import { IssuesExplorer } from './screens/IssuesExplorer'
import { DependencyGraphView } from './screens/DependencyGraphView'
import { DocumentsScreen } from './screens/DocumentsScreen'
import { ReviewQueueScreen } from './screens/ReviewQueueScreen'
import { AuditScreen } from './screens/AuditScreen'
import { TimeMachineScreen } from './screens/TimeMachineScreen'
import { EvaluationScreen } from './screens/EvaluationScreen'
import { SettingsScreen } from './screens/SettingsScreen'
import { LoadingState, ErrorState } from './components/primitives'

const NAV_ITEMS = [
  { id: 'command-center', label: 'Command Center' },
  { id: 'evidence', label: 'Evidence' },
  { id: 'claims', label: 'Claims' },
  { id: 'issues', label: 'Issues' },
  { id: 'graph', label: 'Dependency Graph' },
  { id: 'documents', label: 'Documents' },
  { id: 'review', label: 'Review Queue' },
  { id: 'time-machine', label: 'Time Machine' },
  { id: 'audit', label: 'Audit' },
  { id: 'evaluation', label: 'Evaluation Lab' },
] as const

type ViewId = (typeof NAV_ITEMS)[number]['id'] | 'settings'

export default function App() {
  const [caseId, setCaseId] = useState<string | null>(null)
  const [view, setView] = useState<ViewId>('command-center')
  const [rbacVersion, setRbacVersion] = useState(0)

  const activeCase = useCase(caseId)

  if (!caseId) {
    return (
      <div className="mx-auto min-h-screen max-w-5xl px-6 py-10">
        <Header onSettings={() => {}} showSettings={false} />
        <CaseExplorer onOpenCase={(id) => { setCaseId(id); setView('command-center') }} />
      </div>
    )
  }

  return (
    <div key={rbacVersion} className="flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col border-r border-ink-800 bg-ink-900/40 px-3 py-5">
        <button
          onClick={() => setCaseId(null)}
          className="focus-ring mb-4 flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs text-parchment-200/50 hover:text-parchment-100"
        >
          ← All cases
        </button>
        <nav className="flex-1 space-y-0.5">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              onClick={() => setView(item.id)}
              className={`focus-ring block w-full rounded-md px-3 py-2 text-left text-sm transition ${
                view === item.id ? 'bg-ink-800 text-parchment-50' : 'text-parchment-200/60 hover:bg-ink-800/50 hover:text-parchment-100'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <button
          onClick={() => setView('settings')}
          className={`focus-ring mt-2 block w-full rounded-md px-3 py-2 text-left text-sm transition ${
            view === 'settings' ? 'bg-ink-800 text-parchment-50' : 'text-parchment-200/60 hover:bg-ink-800/50 hover:text-parchment-100'
          }`}
        >
          Settings
        </button>
      </aside>

      <main className="min-w-0 flex-1 overflow-y-auto px-8 py-8">
        {activeCase.isLoading && <LoadingState label="Loading case…" />}
        {activeCase.isError && <ErrorState error={activeCase.error} />}
        {activeCase.data && (
          <AnimatePresence mode="wait">
            <motion.div
              key={view}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.15 }}
            >
              {view === 'command-center' && (
                <CommandCenter activeCase={activeCase.data} onNavigate={(v) => setView(v as ViewId)} />
              )}
              {view === 'evidence' && <EvidenceExplorer caseId={caseId} />}
              {view === 'claims' && <ClaimsExplorer caseId={caseId} />}
              {view === 'issues' && <IssuesExplorer caseId={caseId} />}
              {view === 'graph' && <DependencyGraphView caseId={caseId} />}
              {view === 'documents' && <DocumentsScreen caseId={caseId} />}
              {view === 'review' && <ReviewQueueScreen caseId={caseId} />}
              {view === 'time-machine' && <TimeMachineScreen caseId={caseId} />}
              {view === 'audit' && <AuditScreen caseId={caseId} />}
              {view === 'evaluation' && <EvaluationScreen caseId={caseId} />}
              {view === 'settings' && <SettingsScreen onChange={() => setRbacVersion((v) => v + 1)} />}
            </motion.div>
          </AnimatePresence>
        )}
      </main>
    </div>
  )
}

function Header({ showSettings }: { onSettings: () => void; showSettings: boolean }) {
  return (
    <header className="mb-8 flex items-center justify-between">
      <div>
        <h1 className="font-serif text-2xl text-parchment-50">Evidence Dependency Engine</h1>
        <p className="mt-1 text-sm text-parchment-200/50">
          Know exactly which evidence supports which claim — and what breaks when that evidence disappears.
        </p>
      </div>
      {showSettings && null}
    </header>
  )
}
