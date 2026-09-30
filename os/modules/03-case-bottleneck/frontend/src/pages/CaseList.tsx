import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { CaseSummary } from "../types/domain";
import { ErrorBanner, Spinner } from "../components/Badges";

export function CaseList() {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.listCases().then(setCases).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, []);

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Cases</div>
          <div className="page-subtitle">
            Synthetic demo cases A–J (Section 57) — each isolates one specific bottleneck behaviour.
          </div>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}
      {!cases && !error && <Spinner />}

      {cases?.map((c) => (
        <div key={c.id} className="case-list-item" onClick={() => navigate(`/cases/${c.id}`)}>
          <div>
            <div className="case-list-title">
              {c.title} <span className="faint mono small">· {c.demo_scenario ? `Scenario ${c.demo_scenario}` : c.case_type}</span>
            </div>
            <div className="case-list-desc">{c.description}</div>
          </div>
          <div className="row">
            {c.total_bottlenecks > 0 ? (
              <span className="small muted">{c.open_bottlenecks} open / {c.total_bottlenecks} total</span>
            ) : (
              <span className="small faint">not yet investigated</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
