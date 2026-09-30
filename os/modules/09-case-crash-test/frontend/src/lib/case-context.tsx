import { createContext, useContext, useState, type ReactNode } from "react";

interface CaseContextValue {
  caseId: string | null;
  setCaseId: (id: string | null) => void;
  simulationId: string | null;
  setSimulationId: (id: string | null) => void;
}

const CaseContext = createContext<CaseContextValue | undefined>(undefined);

export function CaseProvider({ children }: { children: ReactNode }) {
  const [caseId, setCaseId] = useState<string | null>(
    () => localStorage.getItem("cct.activeCaseId"),
  );
  const [simulationId, setSimulationId] = useState<string | null>(null);

  const persistCaseId = (id: string | null) => {
    setCaseId(id);
    if (id) localStorage.setItem("cct.activeCaseId", id);
    else localStorage.removeItem("cct.activeCaseId");
  };

  return (
    <CaseContext.Provider
      value={{ caseId, setCaseId: persistCaseId, simulationId, setSimulationId }}
    >
      {children}
    </CaseContext.Provider>
  );
}

export function useCaseContext() {
  const ctx = useContext(CaseContext);
  if (!ctx) throw new Error("useCaseContext must be used within CaseProvider");
  return ctx;
}
