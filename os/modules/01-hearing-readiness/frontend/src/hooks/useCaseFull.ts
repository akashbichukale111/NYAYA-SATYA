import { useCallback, useEffect, useState } from "react";
import { api, type CaseFull, type ReadinessSnapshot } from "../lib/api";

export function useCaseFull(caseId: string | null) {
  const [data, setData] = useState<CaseFull | null>(null);
  const [readiness, setReadiness] = useState<ReadinessSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    if (!caseId) {
      setData(null);
      setReadiness(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    Promise.all([api.getCase(caseId), api.getReadiness(caseId)])
      .then(([full, ready]) => {
        setData(full);
        setReadiness(ready);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [caseId]);

  useEffect(reload, [reload]);

  return { data, readiness, loading, error, reload };
}
