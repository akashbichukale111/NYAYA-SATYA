import { useIssues } from '../hooks'
import { Card, SectionHeading, LoadingState, ErrorState, EmptyState, StatusPill } from '../components/primitives'

export function IssuesExplorer({ caseId }: { caseId: string }) {
  const issues = useIssues(caseId)

  return (
    <div>
      <SectionHeading title="Issues" subtitle="Questions that matter to the case, and whether claims support them." />
      {issues.isLoading && <LoadingState />}
      {issues.isError && <ErrorState error={issues.error} />}
      {issues.data && issues.data.length === 0 && (
        <EmptyState title="No issues yet." hint="Add an issue, or approve a claim→issue mapping proposed by the pipeline." />
      )}
      {issues.data && issues.data.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {issues.data.map((issue) => (
            <Card key={issue.id}>
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm text-parchment-100">{issue.question}</p>
                <StatusPill label={issue.status} />
              </div>
              {issue.description && <p className="mt-1.5 text-xs text-parchment-200/50">{issue.description}</p>}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
