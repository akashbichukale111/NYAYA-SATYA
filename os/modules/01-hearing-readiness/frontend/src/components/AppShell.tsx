import { NavLink, Outlet } from "react-router-dom";
import { useI18n } from "../i18n";
import { useSelectedCase } from "../lib/selectedCase";
import { LoadingState, ErrorState } from "./StatusStates";

const NAV_ITEMS: { to: string; key: Parameters<ReturnType<typeof useI18n>["t"]>[0] }[] = [
  { to: "/", key: "nav.command_center" },
  { to: "/cases", key: "nav.cases" },
  { to: "/readiness", key: "nav.readiness" },
  { to: "/blockers", key: "nav.blockers" },
  { to: "/evidence", key: "nav.evidence" },
  { to: "/timeline", key: "nav.timeline" },
  { to: "/simulate", key: "nav.simulate" },
  { to: "/crash-test", key: "nav.crash_test" },
  { to: "/time-machine", key: "nav.time_machine" },
  { to: "/evaluation-lab", key: "nav.evaluation_lab" },
  { to: "/audit", key: "nav.audit" },
  { to: "/settings", key: "nav.settings" },
];

function CaseSwitcher() {
  const { cases, caseId, setCaseId, loading, error } = useSelectedCase();
  if (loading) return <div className="px-4 py-3 text-xs text-[var(--text-muted)]">Loading cases…</div>;
  if (error) return <div className="px-4 py-3 text-xs text-[var(--state-blocked)]">Could not load cases</div>;
  return (
    <select
      value={caseId ?? ""}
      onChange={(e) => setCaseId(e.target.value)}
      aria-label="Active case"
      className="w-full rounded-md border border-[var(--hairline)] bg-[var(--ink-800)] px-3 py-2 text-sm text-[var(--text-primary)] focus:border-[var(--brass-400)]"
    >
      {cases.map((c) => (
        <option key={c.id} value={c.id}>
          {c.title}
        </option>
      ))}
    </select>
  );
}

export default function AppShell() {
  const { t } = useI18n();
  const { loading, error, reload } = useSelectedCase();

  return (
    <div className="flex h-full">
      <aside className="flex w-64 shrink-0 flex-col border-r border-[var(--hairline)] bg-[var(--ink-900)]">
        <div className="border-b border-[var(--hairline)] px-5 py-5">
          <div className="font-serif text-lg leading-tight">Hearing Readiness Engine</div>
          <div className="mt-1 text-xs leading-snug text-[var(--text-muted)]">{t("app.tagline")}</div>
        </div>

        <div className="px-4 py-4">
          <div className="mb-1.5 text-xs uppercase tracking-wide text-[var(--text-muted)]">Active case</div>
          <CaseSwitcher />
        </div>

        <nav className="scrollbar-thin flex-1 overflow-y-auto px-2 py-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `mb-0.5 flex items-center rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-[var(--ink-700)] text-[var(--text-primary)]"
                    : "text-[var(--text-secondary)] hover:bg-[var(--ink-800)] hover:text-[var(--text-primary)]"
                }`
              }
            >
              {t(item.key)}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-[var(--hairline)] px-4 py-3 text-xs text-[var(--text-muted)]">
          {t("app.demo_mode")}
        </div>
      </aside>

      <main className="scrollbar-thin flex-1 overflow-y-auto">
        <div className="mx-auto max-w-5xl px-8 py-8">
          {loading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message={error} onRetry={reload} />
          ) : (
            <Outlet />
          )}
        </div>
      </main>
    </div>
  );
}
