import { useEffect, useState } from "react";
import { NavLink } from "react-router";

import { get } from "./shared/api";
import { useI18n, type Language } from "./shared/i18n";
import { SettingsIcon } from "./shared/icons";

const LINK_CLASS = "rounded-md px-3 py-1.5 text-[13.5px] transition-colors";

const LANGUAGES: { id: Language; label: string }[] = [
  { id: "zh", label: "中文" },
  { id: "ja", label: "日本語" },
];

/**
 * The bar that gets you between features.
 *
 * One compact row on purpose: every pixel it takes pushes the memo box further
 * down, and being able to just start typing is what F1 is for.
 */
export function AppNav() {
  const { language, setLanguage, t } = useI18n();
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    get<{ version: string }>("/version")
      .then((data) => {
        if (data?.version) {
          setVersion(data.version);
        }
      })
      .catch(() => {});
  }, []);

  return (
    <header
      className="flex h-[52px] shrink-0 items-center justify-between px-8"
      style={{ borderBottom: "1px solid var(--border)", background: "var(--surface)" }}
    >
      <nav className="flex items-center gap-9">
        <div className="flex items-baseline gap-1.5">
          <span
            className="text-sm font-semibold tracking-wide"
            style={{ fontFamily: "var(--mono)", color: "oklch(0.35 0.01 260)" }}
          >
            workutil
          </span>
          {version && (
            <span
              className="text-[11px]"
              style={{ fontFamily: "var(--mono)", color: "var(--text-faint)" }}
            >
              v{version}
            </span>
          )}
        </div>
        <div className="flex gap-1">
          <NavLink
            to="/"
            end
            style={({ isActive }) => ({
              background: isActive ? "var(--accent-tint)" : "transparent",
              color: isActive ? "var(--accent-strong)" : "var(--text-muted)",
              fontWeight: isActive ? 600 : 400,
            })}
            className={LINK_CLASS}
          >
            {t("nav.memo")}
          </NavLink>
          <NavLink
            to="/evidence"
            style={({ isActive }) => ({
              background: isActive ? "var(--accent-tint)" : "transparent",
              color: isActive ? "var(--accent-strong)" : "var(--text-muted)",
              fontWeight: isActive ? 600 : 400,
            })}
            className={LINK_CLASS}
          >
            {t("nav.evidence")}
          </NavLink>
          <NavLink
            to="/bookmarks"
            style={({ isActive }) => ({
              background: isActive ? "var(--accent-tint)" : "transparent",
              color: isActive ? "var(--accent-strong)" : "var(--text-muted)",
              fontWeight: isActive ? 600 : 400,
            })}
            className={LINK_CLASS}
          >
            {t("nav.bookmarks")}
          </NavLink>
          <NavLink
            to="/todos"
            style={({ isActive }) => ({
              background: isActive ? "var(--accent-tint)" : "transparent",
              color: isActive ? "var(--accent-strong)" : "var(--text-muted)",
              fontWeight: isActive ? 600 : 400,
            })}
            className={LINK_CLASS}
          >
            {t("nav.todo")}
          </NavLink>
        </div>
      </nav>

      <div className="flex items-center gap-3">
        <div
          className="flex items-center gap-0.5 rounded-lg p-[3px]"
          style={{ background: "var(--hover-wash)", fontFamily: "var(--mono)" }}
          role="radiogroup"
          aria-label="Language"
        >
          {LANGUAGES.map((lang) => {
            const active = language === lang.id;
            return (
              <button
                key={lang.id}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setLanguage(lang.id)}
                className="cursor-pointer rounded-md px-2.5 py-1.5 text-[11.5px] transition-colors"
                style={{
                  background: active ? "var(--surface)" : "transparent",
                  color: active ? "var(--text)" : "var(--text-faint)",
                  fontWeight: active ? 600 : 400,
                  boxShadow: active ? "0 1px 2px rgba(20,20,30,0.08)" : "none",
                }}
              >
                {lang.label}
              </button>
            );
          })}
        </div>

        <NavLink
          to="/settings"
          aria-label={t("nav.settings")}
          title={t("nav.settings")}
          style={({ isActive }) => ({
            background: isActive ? "var(--accent-tint)" : "transparent",
            color: isActive ? "var(--accent-strong)" : "var(--text-muted)",
          })}
          className="flex items-center justify-center rounded-md p-1.5 transition-colors hover:text-[var(--text)]"
        >
          <SettingsIcon size={16} />
        </NavLink>
      </div>
    </header>
  );
}
