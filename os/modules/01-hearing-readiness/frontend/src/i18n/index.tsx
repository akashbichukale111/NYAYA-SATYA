import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import en, { type TranslationKey } from "./en";
import hi from "./hi";
import mr from "./mr";

export type Language = "en" | "hi" | "mr";

const DICTS: Record<Language, Partial<Record<TranslationKey, string>>> = { en, hi, mr };

export const LANGUAGE_LABELS: Record<Language, string> = {
  en: "English",
  hi: "हिन्दी (partial)",
  mr: "मराठी (partial)",
};

interface I18nContextValue {
  lang: Language;
  setLang: (l: Language) => void;
  t: (key: TranslationKey) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Language>("en");

  const value = useMemo<I18nContextValue>(() => {
    const dict = DICTS[lang];
    return {
      lang,
      setLang,
      // Always falls back to English rather than showing a raw key or
      // blank string -- a missing translation should degrade gracefully,
      // never break the UI.
      t: (key) => dict[key] ?? en[key] ?? key,
    };
  }, [lang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
