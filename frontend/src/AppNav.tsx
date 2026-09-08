import { NavLink } from "react-router";

import { useI18n, type Language } from "./shared/i18n";

const LINK_BASE =
  "rounded-md px-2.5 py-1 text-xs transition-colors focus:outline-none focus:ring-1 focus:ring-slate-300";

function linkClass({ isActive }: { isActive: boolean }) {
  return isActive
    ? `${LINK_BASE} bg-white font-medium text-slate-900 shadow-sm`
    : `${LINK_BASE} text-slate-500 hover:bg-white/60 hover:text-slate-800`;
}

/**
 * The bar that gets you between features.
 *
 * One compact row on purpose: every pixel it takes pushes the memo box further
 * down, and being able to just start typing is what F1 is for.
 */
export function AppNav() {
  const { language, setLanguage, t } = useI18n();

  return (
    <header className="border-b border-slate-200 bg-slate-100/80">
      <nav className="mx-auto flex max-w-3xl items-center gap-1 px-6 py-1.5">
        <span className="mr-2 text-xs font-semibold tracking-wide text-slate-400">
          workutil
        </span>
        <NavLink to="/" end className={linkClass}>
          {t("nav.memo")}
        </NavLink>
        <NavLink to="/evidence" className={linkClass}>
          {t("nav.evidence")}
        </NavLink>
        <NavLink to="/bookmarks" className={linkClass}>
          {t("nav.bookmarks")}
        </NavLink>
        <NavLink to="/todos" className={linkClass}>
          {t("nav.todo")}
        </NavLink>

        <div className="ml-auto flex items-center">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            className="cursor-pointer rounded border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-600 focus:outline-none focus:ring-1 focus:ring-slate-300"
            aria-label="Language"
          >
            <option value="zh">中文</option>
            <option value="ja">日本語</option>
          </select>
        </div>
      </nav>
    </header>
  );
}

