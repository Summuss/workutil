import { firstLine } from "./firstLine";
import type { Memo } from "./types";

interface MemoListProps {
  memos: Memo[];
  loading: boolean;
  error: string | null;
}

function Placeholder({ children }: { children: string }) {
  return <p className="py-8 text-center text-sm text-slate-400">{children}</p>;
}

/** The memos, newest first — the order the backend sends them in. */
export function MemoList({ memos, loading, error }: MemoListProps) {
  if (memos.length === 0) {
    if (error !== null) {
      return <p className="py-8 text-center text-sm text-red-600">{error}</p>;
    }
    if (loading) {
      return <Placeholder>载入中…</Placeholder>;
    }
    return <Placeholder>还没有记录。写点什么,按 Ctrl+Enter。</Placeholder>;
  }

  // Anything already written shows, even if the rest is still loading or the
  // load failed — a memo just saved must never be hidden behind a spinner.
  return (
    <>
      {error !== null && <p className="pb-2 text-sm text-red-600">{error}</p>}
      <ul className="divide-y divide-slate-200">
        {memos.map((memo) => (
          <li
            key={memo.id}
            className="truncate py-2.5 font-mono text-sm text-slate-700"
          >
            {firstLine(memo.body)}
          </li>
        ))}
      </ul>
    </>
  );
}
