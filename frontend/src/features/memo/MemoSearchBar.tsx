import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { t } from "../../shared/i18n";
import { SearchIcon, XIcon } from "../../shared/icons";

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
    <div
      className="flex items-center gap-2.5 rounded-lg px-3.5 py-2.5"
      style={{ border: "1px solid var(--border)", background: "var(--surface)" }}
    >
      <SearchIcon style={{ color: "var(--text-faint)" }} className="shrink-0" />
      <input
        type="text"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("memo.search_placeholder")}
        className="min-w-0 flex-1 border-none bg-transparent text-[13px] outline-none"
        style={{ color: "var(--text)" }}
      />
      {query.trim() !== "" && (
        <button
          type="button"
          onClick={clear}
          title={t("memo.search_clear_title")}
          className="icon-btn"
        >
          <XIcon size={11} />
        </button>
      )}
    </div>
  );
}
