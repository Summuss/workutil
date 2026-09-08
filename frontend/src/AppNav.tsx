import { NavLink } from "react-router";

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
  return (
    <header className="border-b border-slate-200 bg-slate-100/80">
      <nav className="mx-auto flex max-w-3xl items-center gap-1 px-6 py-1.5">
        <span className="mr-2 text-xs font-semibold tracking-wide text-slate-400">
          workutil
        </span>
        <NavLink to="/" end className={linkClass}>
          Memo
        </NavLink>
        <NavLink to="/evidence" className={linkClass}>
          Evidence
        </NavLink>
        <NavLink to="/bookmarks" className={linkClass}>
          Bookmarks
        </NavLink>
      </nav>
    </header>
  );
}
