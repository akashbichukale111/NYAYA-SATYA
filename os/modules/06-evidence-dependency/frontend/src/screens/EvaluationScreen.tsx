import { useEvaluation } from '../hooks'
import { Card, SectionHeading, LoadingState, ErrorState, StatusPill } from '../components/primitives'

const CHECK_LABELS: Record<string, string> = {
  provenance_completeness: 'Provenance completeness',
  claim_traceability: 'Claim traceability',
  issue_mapping_coverage: 'Issue mapping coverage',
  dependency_consistency: 'Dependency consistency',
  case_isolation: 'Case isolation',
  contradiction_detection: 'Contradiction detection',
}

export function EvaluationScreen({ caseId }: { caseId: string }) {
  const evaluation = useEvaluation(caseId)

  return (
    <div className="space-y-6">
      <SectionHeading
        title="Evaluation Lab"
        subtitle="Deterministic checks against this case's real, current data. No invented percentages — only PASS, FAIL, or NOT_RUN."
      />

      {evaluation.isLoading && <LoadingState />}
      {evaluation.isError && <ErrorState error={evaluation.error} />}

      {evaluation.data && (
        <>
          <div className="grid grid-cols-3 gap-3">
            <Card className="text-center">
              <p className="font-serif text-2xl text-signal-verified">{evaluation.data.summary.pass_count}</p>
              <p className="text-xs text-parchment-200/40">Pass</p>
            </Card>
            <Card className="text-center">
              <p className="font-serif text-2xl text-signal-conflict">{evaluation.data.summary.fail_count}</p>
              <p className="text-xs text-parchment-200/40">Fail</p>
            </Card>
            <Card className="text-center">
              <p className="font-serif text-2xl text-parchment-200/50">{evaluation.data.summary.not_run_count}</p>
              <p className="text-xs text-parchment-200/40">Not run</p>
            </Card>
          </div>

          <div className="space-y-2">
            {Object.entries(evaluation.data.checks).map(([key, result]) => (
              <div key={key} className="flex items-center justify-between rounded-md border border-ink-700 bg-ink-900/40 px-4 py-2.5">
                <span className="text-sm text-parchment-100">{CHECK_LABELS[key] ?? key}</span>
                <StatusPill label={result} />
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
