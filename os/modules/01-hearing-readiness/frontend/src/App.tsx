import { Routes, Route } from "react-router-dom";
import AppShell from "./components/AppShell";
import CommandCenterPage from "./pages/CommandCenterPage";
import CasesPage from "./pages/CasesPage";
import ReadinessPage from "./pages/ReadinessPage";
import BlockersPage from "./pages/BlockersPage";
import BlockerDetailPage from "./pages/BlockerDetailPage";
import EvidencePage from "./pages/EvidencePage";
import TimelinePage from "./pages/TimelinePage";
import SimulatePage from "./pages/SimulatePage";
import CrashTestPage from "./pages/CrashTestPage";
import TimeMachinePage from "./pages/TimeMachinePage";
import EvaluationLabPage from "./pages/EvaluationLabPage";
import AuditPage from "./pages/AuditPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<CommandCenterPage />} />
        <Route path="cases" element={<CasesPage />} />
        <Route path="readiness" element={<ReadinessPage />} />
        <Route path="blockers" element={<BlockersPage />} />
        <Route path="blockers/:blockerId" element={<BlockerDetailPage />} />
        <Route path="evidence" element={<EvidencePage />} />
        <Route path="timeline" element={<TimelinePage />} />
        <Route path="simulate" element={<SimulatePage />} />
        <Route path="crash-test" element={<CrashTestPage />} />
        <Route path="time-machine" element={<TimeMachinePage />} />
        <Route path="evaluation-lab" element={<EvaluationLabPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
