import type { RootCauseCandidate } from "../types/domain";

export function RootCauseChain({ candidate }: { candidate: RootCauseCandidate }) {
  return (
    <div className="chain">
      {candidate.chain.map((step, i) => (
        <div className="chain-step" key={i}>
          <div className="chain-rail">
            <div className="chain-node" />
            {i < candidate.chain.length - 1 && <div className="chain-line" />}
          </div>
          <div className="chain-body">
            <div className="chain-step-label">{step.step}</div>
            <div className="chain-step-desc">{step.description}</div>
            {step.evidence && step.evidence.length > 0 && (
              <div className="chain-step-evidence">evidence: {step.evidence.join(", ")}</div>
            )}
            {step.confidence && (
              <div className="small muted" style={{ marginTop: 2 }}>confidence: {step.confidence}</div>
            )}
            {step.debate && (
              <div className="card-flat" style={{ marginTop: 8 }}>
                <div className="small faint" style={{ marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Multi-agent debate — no forced consensus
                </div>
                <div className="stack">
                  {step.debate.map((d, j) => (
                    <div key={j} className="small">
                      <strong>{d.agent}:</strong> {d.claim}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
