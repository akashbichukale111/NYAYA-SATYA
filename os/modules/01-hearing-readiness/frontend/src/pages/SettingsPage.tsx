import { useI18n, LANGUAGE_LABELS, type Language } from "../i18n";
import { useLowBandwidth } from "../lib/lowBandwidth";
import { PageHeader, Panel } from "../components/Panel";

export default function SettingsPage() {
  const { lang, setLang, t } = useI18n();
  const { lowBandwidth, setLowBandwidth } = useLowBandwidth();

  return (
    <div>
      <PageHeader title="Settings" />

      <Panel title={t("settings.language")} className="mb-6">
        <div className="flex gap-2">
          {(Object.keys(LANGUAGE_LABELS) as Language[]).map((l) => (
            <button
              key={l}
              onClick={() => setLang(l)}
              className={`rounded-md border px-3 py-1.5 text-sm ${
                lang === l ? "border-[var(--brass-500)] bg-[var(--ink-800)]" : "border-[var(--hairline)] hover:bg-[var(--ink-800)]"
              }`}
            >
              {LANGUAGE_LABELS[l]}
            </button>
          ))}
        </div>
        <p className="mt-3 text-xs text-[var(--text-muted)]">
          Hindi and Marathi are partially translated to demonstrate the localization architecture end-to-end.
          Full coverage of every string is planned, not yet implemented.
        </p>
      </Panel>

      <Panel title={t("settings.low_bandwidth")}>
        <label className="flex cursor-pointer items-center gap-3">
          <input type="checkbox" checked={lowBandwidth} onChange={(e) => setLowBandwidth(e.target.checked)} />
          <span className="text-sm">{t("settings.low_bandwidth_desc")}</span>
        </label>
      </Panel>
    </div>
  );
}
