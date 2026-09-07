import { useEffect, useState, type KeyboardEvent } from "react";

interface MemoSearchBarProps {
  value: string;
  onChange: (query: string) => void;
}

export function MemoSearchBar({ value, onChange }: MemoSearchBarProps) {
  const [internalValue, setInternalValue] = useState(value);

  useEffect(() => {
    setInternalValue(value);
  }, [value]);

  // Debounce search input by 150ms to keep typing responsive
  useEffect(() => {
    const timer = setTimeout(() => {
      if (internalValue !== value) {
        onChange(internalValue);
      }
    }, 150);

    return () => clearTimeout(timer);
  }, [internalValue, value, onChange]);

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Escape") {
      setInternalValue("");
      onChange("");
    }
  }

  function handleClear() {
    setInternalValue("");
    onChange("");
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
        value={internalValue}
        onChange={(e) => setInternalValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="搜索 Memo… (关键词、正文任意位置，按 Esc 清空)"
        className="w-full rounded-md border border-slate-200 bg-white py-2 pr-8 pl-9 text-xs text-slate-900 placeholder:text-slate-400 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300"
      />
      {internalValue.trim() !== "" && (
        <button
          type="button"
          onClick={handleClear}
          title="清空搜索 (Esc)"
          className="absolute right-2.5 flex h-4 w-4 cursor-pointer items-center justify-center rounded-full text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-600"
        >
          ✕
        </button>
      )}
    </div>
  );
}
