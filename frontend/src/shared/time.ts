import { getLanguage, type Language } from "./i18n";

/**
 * A timestamp as it is shown, year included.
 *
 * "I wrote that around last month" is how things get found here, and a bare
 * 9/7 makes last year look like this year.
 */
export function formatTime(iso: string, lang?: Language): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  const currentLang = lang ?? getLanguage();
  const locale = currentLang === "ja" ? "ja-JP" : "zh-CN";
  return date.toLocaleString(locale, {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

