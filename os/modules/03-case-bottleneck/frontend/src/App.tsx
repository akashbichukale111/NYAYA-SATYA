import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { CommandCenter } from "./pages/CommandCenter";
import { CaseList } from "./pages/CaseList";
import { CaseDetail } from "./pages/CaseDetail";
import { api } from "./api/client";

export default function App() {
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const location = useLocation();

  useEffect(() => {
    api.health().then(() => setApiOk(true)).catch(() => setApiOk(false));
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          Case Bottleneck Engine
          <span className="brand-tag">Find what is actually stopping a case.</span>
        </div>

        <div className="nav-group-label">Overview</div>
        <NavLink to="/" end className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>Command Center</NavLink>
        <NavLink to="/cases" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>Cases</NavLink>

        <div className="nav-group-label">Status</div>
        <div className="nav-link" style={{ cursor: "default" }}>
          <span style={{
            width: 7, height: 7, borderRadius: "50%",
            background: apiOk === null ? "var(--unknown)" : apiOk ? "var(--confirmed)" : "var(--critical)",
          }} />
          {apiOk === null ? "Checking backend…" : apiOk ? "Backend connected" : "Backend unreachable"}
        </div>

        <div className="nav-group-label">Roadmap (not built)</div>
        <div className="nav-link disabled">Time Machine</div>
        <div className="nav-link disabled">Case Handoff</div>
        <div className="nav-link disabled">Evaluation Lab</div>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/" element={<CommandCenter />} />
          <Route path="/cases" element={<CaseList />} />
          <Route path="/cases/:caseId" element={<CaseDetail />} />
        </Routes>
      </main>
    </div>
  );
}
