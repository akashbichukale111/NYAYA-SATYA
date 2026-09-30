import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type CaseSummary } from "./api";

interface Ctx {
  cases: CaseSummary[];
  caseId: string | null;
  setCaseId: (id: string) => void;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

const SelectedCaseContext = createContext<Ctx | null>(null);
const STORAGE_KEY = "hre.selected_case_id";

export function SelectedCaseProvider({ children }: { children: ReactNode }) {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [caseId, setCaseIdState] = useState<string | null>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .listCases()
      .then((list) => {
        setCases(list);
        setCaseIdState((prev) => {
          if (prev && list.some((c) => c.id === prev)) return prev;
          return list[0]?.id ?? null;
        });
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const setCaseId = (id: string) => {
    setCaseIdState(id);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* ignore */
    }
  };

  return (
    <SelectedCaseContext.Provider value={{ cases, caseId, setCaseId, loading, error, reload: load }}>
      {children}
    </SelectedCaseContext.Provider>
  );
}

export function useSelectedCase() {
  const ctx = useContext(SelectedCaseContext);
  if (!ctx) throw new Error("useSelectedCase must be used within SelectedCaseProvider");
  return ctx;
}
