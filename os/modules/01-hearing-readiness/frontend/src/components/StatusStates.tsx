import { useI18n } from "../i18n";

export function LoadingState({ label }: { label?: string }) {
  const { t } = useI18n();
  return (
    <div className="flex items-center gap-3 py-10 text-[var(--text-secondary)]">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-[var(--hairline)] border-t-[var(--brass-400)]" />
      <span>{label ?? t("common.loading")}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useI18n();
  return (
    <div className="rounded-lg border border-[var(--state-blocked)]/40 bg-[var(--state-blocked)]/10 px-4 py-4 text-sm">
      <div className="font-medium text-[var(--state-blocked)]">{t("common.error")}</div>
      <div className="mt-1 text-[var(--text-secondary)]">{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded border border-[var(--hairline)] px-3 py-1 text-xs hover:bg-[var(--ink-700)]"
        >
          {t("common.retry")}
        </button>
      )}
    </div>
  );
}

export function EmptyState({ message }: { message?: string }) {
  const { t } = useI18n();
  return (
    <div className="rounded-lg border border-dashed border-[var(--hairline)] px-4 py-8 text-center text-sm text-[var(--text-muted)]">
      {message ?? t("common.no_data")}
    </div>
  );
}
