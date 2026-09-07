import { useState } from "react";

import { MemoItem } from "./MemoItem";
import type { Memo } from "./types";

interface MemoListProps {
  memos: Memo[];
  loading: boolean;
  error: string | null;
  onUpdate: (updated: Memo) => void;
}

function Placeholder({ children }: { children: string }) {
  return <p className="py-8 text-center text-sm text-slate-400">{children}</p>;
}

/** The memos, newest first — the order the backend sends them in. */
export function MemoList({ memos, loading, error, onUpdate }: MemoListProps) {
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  function toggleExpand(id: number) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

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
          <MemoItem
            key={memo.id}
            memo={memo}
            isExpanded={expandedIds.has(memo.id)}
            onToggleExpand={() => toggleExpand(memo.id)}
            onUpdate={onUpdate}
          />
        ))}
      </ul>
    </>
  );
}
