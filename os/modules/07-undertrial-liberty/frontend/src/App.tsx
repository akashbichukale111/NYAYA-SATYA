import { BrowserRouter, Routes, Route } from "react-router-dom";
import CasesPage from "./pages/CasesPage";
import CaseDetailPage from "./pages/CaseDetailPage";
import SettingsTab from "./pages/SettingsTab";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CasesPage />} />
        <Route path="/cases/:caseId" element={<CaseDetailPage />} />
        <Route path="/settings" element={<SettingsTab />} />
      </Routes>
    </BrowserRouter>
  );
}
