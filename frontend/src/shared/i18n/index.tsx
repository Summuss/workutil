import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import jaTranslations from "./ja.json";
import zhTranslations from "./zh.json";

export type Language = "zh" | "ja";

export const STORAGE_KEY = "workutil_language";

const translations: Record<Language, Record<string, string>> = {
  zh: zhTranslations,
  ja: jaTranslations,
};

export function detectLanguage(): Language {
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "zh" || saved === "ja") {
        return saved;
      }
    } catch {
      // localStorage may be unavailable or blocked
    }
  }

  if (typeof navigator !== "undefined" && navigator.language) {
    const lang = navigator.language.toLowerCase();
    if (lang.startsWith("ja")) {
      return "ja";
    }
    if (lang.startsWith("zh")) {
      return "zh";
    }
  }

  return "zh";
}

let activeLanguage: Language = detectLanguage();

if (typeof document !== "undefined") {
  document.documentElement.lang = activeLanguage;
}

export function getLanguage(): Language {
  return activeLanguage;
}

export function setLanguage(next: Language): void {
  activeLanguage = next;
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // ignore storage failures
    }
  }
  if (typeof document !== "undefined") {
    document.documentElement.lang = next;
  }
}

export function t(
  key: string,
  params?: Record<string, string | number>,
): string {
  const dict = translations[activeLanguage];
  let value = dict?.[key];
  if (value === undefined) {
    return `[${key}]`;
  }
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      value = value.replaceAll(`{${k}}`, String(v));
    }
  }
  return value;
}

interface I18nContextValue {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);


export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLangState] = useState<Language>(() => {
    const initial = detectLanguage();
    setLanguage(initial);
    return initial;
  });

  const handleSetLanguage = useCallback((next: Language) => {
    setLanguage(next);
    setLangState(next);
  }, []);

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage: handleSetLanguage,
      t,
    }),
    [language, handleSetLanguage],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return ctx;
}
