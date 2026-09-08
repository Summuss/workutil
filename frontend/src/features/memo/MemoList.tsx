import { useState } from "react";

import { t } from "../../shared/i18n";
import { MemoItem } from "./MemoItem";
import type { Memo } from "./types";

interface MemoListProps {
  memos: Memo[];
  loading: boolean;
  error: string | null;
  searchQuery?: string;
  onUpdate: (updated: Memo) => void;
  onDelete: (id: number) => void;
}

function Placeholder({ children }: { children: string }) {
  return (
    <p className="py-8 text-center text-[13px]" style={{ color: "var(--text-faint)" }}>
      {children}
    </p>
  );
}

/** The memos, newest first — the order the backend sends them in. */
export function MemoList({
  memos,
  loading,
  error,
  searchQuery,
  onUpdate,
  onDelete,
}: MemoListProps) {
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
      return (
        <p className="py-8 text-center text-[13px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      );
    }
    if (loading) {
      return <Placeholder>{t("common.loading")}</Placeholder>;
    }
    if (searchQuery && searchQuery.trim() !== "") {
      return (
        <Placeholder>
          {t("memo.search_empty", { query: searchQuery.trim() })}
        </Placeholder>
      );
    }
    return <Placeholder>{t("memo.empty_state")}</Placeholder>;
  }

  // Anything already written shows, even if the rest is still loading or the
  // load failed — a memo just saved must never be hidden behind a spinner.
  return (
    <>
      {error !== null && (
        <p className="pb-2 text-[13px]" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}
      <ul className="flex flex-col gap-2">
        {memos.map((memo) => (
          <MemoItem
            key={memo.id}
            memo={memo}
            isExpanded={expandedIds.has(memo.id)}
            searchQuery={searchQuery}
            onToggleExpand={() => toggleExpand(memo.id)}
            onUpdate={onUpdate}
            onDelete={onDelete}
          />
        ))}
      </ul>
    </>
  );
}
