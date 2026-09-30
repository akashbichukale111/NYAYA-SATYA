import { NavLink, Route, Routes, Navigate } from "react-router-dom";
import { CaseProvider, useCaseContext } from "./lib/case-context";
import { RoleSwitcher } from "./components/RoleSwitcher";
import CommandCenter from "./pages/CommandCenter";
import CaseGraphPage from "./pages/CaseGraphPage";
import ScenarioBuilder from "./pages/ScenarioBuilder";
import SimulationResultPage from "./pages/SimulationResultPage";
import CounterfactualLab from "./pages/CounterfactualLab";
import ReviewQueuePage from "./pages/ReviewQueuePage";
import TimeMachinePage from "./pages/TimeMachinePage";
import AuditPage from "./pages/AuditPage";
import EvaluationLabPage from "./pages/EvaluationLabPage";

const NAV = [
  { to: "/", label: "Command Center", end: true },
  { to: "/graph", label: "Case Graph" },
  { to: "/scenarios", label: "Scenario Builder" },
  { to: "/simulation", label: "Simulation Result" },
  { to: "/counterfactual", label: "Counterfactual Lab" },
  { to: "/time-machine", label: "Time Machine" },
  { to: "/review-queue", label: "Review Queue" },
  { to: "/audit", label: "Audit" },
  { to: "/evaluation", label: "Evaluation Lab" },
];

function Shell() {
  const { caseId } = useCaseContext();
  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-brand-border bg-brand-panel/40 px-4 py-6">
        <div className="mb-8">
          <p className="text-xs uppercase tracking-widest text-slate-500">Case Crash Test</p>
          <p className="text-sm font-semibold text-slate-200">&amp; Resilience Lab</p>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-accent/10 text-brand-accent" : "text-slate-400 hover:bg-slate-800/70 hover:text-slate-200"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-8 border-t border-brand-border pt-4 text-xs text-slate-500">
          {caseId ? (
            <>
              <p className="text-slate-400">Active case</p>
              <p className="truncate font-mono text-slate-300">{caseId}</p>
            </>
          ) : (
            <p>No case selected</p>
          )}
        </div>
        <div className="mt-6 border-t border-brand-border pt-4">
          <RoleSwitcher />
        </div>
        <p className="mt-6 text-[11px] leading-snug text-slate-600">
          Structural dependency simulation only. Never a legal outcome predictor.
        </p>
      </aside>
      <main className="flex-1 overflow-y-auto px-8 py-6">
        <Routes>
          <Route path="/" element={<CommandCenter />} />
          <Route path="/graph" element={<CaseGraphPage />} />
          <Route path="/scenarios" element={<ScenarioBuilder />} />
          <Route path="/simulation" element={<SimulationResultPage />} />
          <Route path="/counterfactual" element={<CounterfactualLab />} />
          <Route path="/time-machine" element={<TimeMachinePage />} />
          <Route path="/review-queue" element={<ReviewQueuePage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/evaluation" element={<EvaluationLabPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <CaseProvider>
      <Shell />
    </CaseProvider>
  );
}
