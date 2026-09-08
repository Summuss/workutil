import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { t } from "../../shared/i18n";

interface MemoSearchBarProps {
  onChange: (query: string) => void;
}

/**
 * The box that narrows the list below it.
 *
 * The text belongs to this component alone. Handing it down again from above
 * would mean a round trip through the parent on every keystroke, and anything
 * typed while that trip was in the air would be overwritten on the way back.
 */
export function MemoSearchBar({ onChange }: MemoSearchBarProps) {
  const [query, setQuery] = useState("");
  const searched = useRef("");

  // Searching on every keystroke refetches in the middle of a word.
  useEffect(() => {
    if (query === searched.current) {
      return;
    }
    const timer = setTimeout(() => {
      searched.current = query;
      onChange(query);
    }, 150);

    return () => clearTimeout(timer);
  }, [query, onChange]);

  // Getting out of a search is not something to wait 150ms for.
  function clear() {
    setQuery("");
    searched.current = "";
    onChange("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Escape") {
      clear();
    }
  }

  return (
    <div className="relative flex items-center">
      <svg
        className="pointer-events-none absolute left-3 h-4 w-4 text-slate-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
        />
      </svg>
      <input
        type="text"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("memo.search_placeholder")}
        className="w-full rounded-md border border-slate-200 bg-white py-2 pr-8 pl-9 text-xs text-slate-900 placeholder:text-slate-400 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300"
      />
      {query.trim() !== "" && (
        <button
          type="button"
          onClick={clear}
          title={t("memo.search_clear_title")}
          className="absolute right-2.5 flex h-4 w-4 cursor-pointer items-center justify-center rounded-full text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-600"
        >
          ✕
        </button>
      )}
    </div>
  );
}

