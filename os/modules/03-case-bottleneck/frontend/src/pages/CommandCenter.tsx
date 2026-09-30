import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { CaseSummary } from "../types/domain";
import { ErrorBanner, Spinner } from "../components/Badges";

export function CommandCenter() {
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.listCases().then(setCases).catch((e) => setError(e instanceof ApiError ? e.message : String(e)));
  }, []);

  const totalOpen = cases?.reduce((sum, c) => sum + c.open_bottlenecks, 0) ?? 0;
  const investigated = cases?.filter((c) => c.total_bottlenecks > 0).length ?? 0;
  const uninvestigated = cases?.filter((c) => c.total_bottlenecks === 0).length ?? 0;
  const needsAttention = cases?.filter((c) => c.open_bottlenecks > 0) ?? [];

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Command Center</div>
          <div className="page-subtitle">Find what is actually stopping a case from moving forward.</div>
        </div>
      </div>

      {error && <ErrorBanner message={error} />}
      {!cases && !error && <Spinner />}

      {cases && (
        <>
          <div className="grid-2">
            <div className="card">
              <div className="small faint">Open bottlenecks across all cases</div>
              <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4 }}>{totalOpen}</div>
            </div>
            <div className="card">
              <div className="small faint">Cases investigated / not yet run</div>
              <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4 }}>
                {investigated} <span className="faint" style={{ fontSize: 16 }}>/ {uninvestigated} pending</span>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="row between" style={{ marginBottom: 10 }}>
              <strong className="small">Cases with open bottlenecks</strong>
            </div>
            {needsAttention.length === 0 ? (
              <div className="empty-state">
                No case has been investigated yet. Open a case and click &ldquo;Why is this case stuck?&rdquo; to start.
              </div>
            ) : (
              needsAttention.map((c) => (
                <div key={c.id} className="case-list-item" onClick={() => navigate(`/cases/${c.id}`)}>
                  <div>
                    <div className="case-list-title">{c.title}</div>
                    <div className="case-list-desc">{c.description}</div>
                  </div>
                  <span className="badge badge-HIGH">{c.open_bottlenecks} open</span>
                </div>
              ))
            )}
          </div>

          <div className="card">
            <button className="primary" onClick={() => navigate("/cases")}>Browse all cases</button>
          </div>
        </>
      )}
    </div>
  );
}
