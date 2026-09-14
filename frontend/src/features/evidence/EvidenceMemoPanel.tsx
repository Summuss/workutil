import { useEffect, useRef, useState } from "react";

import { messageOf } from "../../shared/api";
import { useI18n } from "../../shared/i18n";
import {
  ChevronDownIcon,
  ChevronUpIcon,
  PinIcon,
  SearchIcon,
  XIcon,
} from "../../shared/icons";
import { Markdown } from "../../shared/Markdown";
import { formatTime } from "../../shared/time";
import { listMemos } from "../memo/api";
import { firstLine } from "../memo/firstLine";
import { HighlightText } from "../memo/HighlightText";
import type { Memo } from "../memo/types";

interface EvidenceMemoPanelProps {
  onClose: () => void;
}

/**
 * Collapsible read-only memo side panel inside the Evidence detail view (ADR-0013).
 *
 * Squeezes the evidence content horizontally without causing any page-level
 * horizontal scroll. Provides quick reference and text selection/copying from
 * memos while verifying test cases.
 *
 * No edit, create, delete, or pinning operations are offered in this view.
 */
export function EvidenceMemoPanel({ onClose }: EvidenceMemoPanelProps) {
  const { t } = useI18n();
  const [memos, setMemos] = useState<Memo[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());

  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    searchInputRef.current?.focus();
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 150);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    listMemos(debouncedQuery)
      .then((loaded) => {
        if (active) {
          setMemos(loaded);
          setError(null);
        }
      })
      .catch((cause) => {
        if (active) {
          setError(messageOf(cause, t("common.load_failed")));
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [debouncedQuery, t]);

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

  function handleSearchKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    // When focus is inside the search input, Esc first clears search query;
    // a second Esc closes the panel.
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      if (searchQuery.trim() !== "") {
        setSearchQuery("");
      } else {
        onClose();
      }
    }
  }

  return (
    <aside
      aria-label="Memo side panel"
      className="flex w-[360px] shrink-0 flex-col h-full min-h-0 border-l"
      style={{ borderColor: "var(--border)", background: "var(--bg)" }}
    >
      {/* Pinned header: title + close button + debounced search */}
      <div
        className="shrink-0 flex flex-col gap-2.5 px-4 pt-4 pb-3 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex items-center justify-between">
          <span
            className="text-xs font-semibold"
            style={{ color: "var(--text-muted)", fontFamily: "var(--mono)" }}
          >
            {t("evidence.memo_panel_title")}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="icon-btn"
            title={t("common.cancel")}
          >
            <XIcon size={13} />
          </button>
        </div>

        <div
          className="flex items-center gap-2 rounded-lg px-2.5 py-1.5"
          style={{ border: "1px solid var(--border)", background: "var(--surface)" }}
        >
          <SearchIcon size={12} style={{ color: "var(--text-faint)" }} className="shrink-0" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder={t("evidence.memo_panel_search_placeholder")}
            className="min-w-0 flex-1 border-none bg-transparent text-xs outline-none"
            style={{ color: "var(--text)" }}
          />
          {searchQuery.trim() !== "" && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              title={t("memo.search_clear_title")}
              className="icon-btn shrink-0"
            >
              <XIcon size={10} />
            </button>
          )}
        </div>
      </div>

      {/* Scrollable list container - MUST have min-h-0 per design.md §3.4 */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-3 flex flex-col gap-2.5">
        {loading && memos.length === 0 ? (
          <p className="py-8 text-center text-xs" style={{ color: "var(--text-faint)" }}>
            {t("common.loading")}
          </p>
        ) : error !== null ? (
          <p className="py-8 text-center text-xs" style={{ color: "var(--danger)" }}>
            {error}
          </p>
        ) : memos.length === 0 ? (
          <p className="py-8 text-center text-xs" style={{ color: "var(--text-faint)" }}>
            {t("evidence.memo_panel_empty")}
          </p>
        ) : (
          memos.map((memo) => {
            const isExpanded = expandedIds.has(memo.id);
            const snippets = memo.snippets ?? [];

            if (!isExpanded) {
              return (
                <div
                  key={memo.id}
                  className="card px-3 py-2.5 cursor-pointer select-none transition-colors hover:border-[var(--border-strong)]"
                  onClick={() => toggleExpand(memo.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex min-w-0 items-center gap-1.5 flex-1">
                      {memo.pinned_at && (
                        <span className="shrink-0" style={{ color: "var(--accent)" }}>
                          <PinIcon filled size={11} />
                        </span>
                      )}
                      <span
                        className="truncate text-xs"
                        style={{ fontFamily: "var(--mono)", color: "var(--text)" }}
                      >
                        {firstLine(memo.body)}
                      </span>
                    </span>

                    <div className="flex items-center gap-1 shrink-0">
                      {memo.image_count > 0 && (
                        <span
                          className="shrink-0 rounded-full px-1.5 py-0.5 text-[10px]"
                          style={{
                            fontFamily: "var(--mono)",
                            background: "var(--hover-wash)",
                            color: "var(--text-muted)",
                          }}
                        >
                          {t("memo.image_count", { count: memo.image_count })}
                        </span>
                      )}
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleExpand(memo.id);
                        }}
                        className="icon-btn shrink-0"
                        title={t("memo.expand")}
                      >
                        <ChevronDownIcon size={12} />
                      </button>
                    </div>
                  </div>

                  {snippets.length > 0 && (
                    <div
                      className="mt-1.5 flex flex-col gap-1 pl-2 text-[11px]"
                      style={{ borderLeft: "2px solid var(--border)", fontFamily: "var(--mono)" }}
                    >
                      {snippets.map((snippet, index) => (
                        <div
                          key={index}
                          className="truncate leading-relaxed"
                          style={{ color: "var(--text-muted)" }}
                        >
                          <HighlightText text={snippet} query={debouncedQuery} />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            }

            return (
              <div key={memo.id} className="card px-3 py-2.5">
                <div
                  className="flex items-center justify-between pb-1.5"
                  style={{ borderBottom: "1px solid var(--border)" }}
                >
                  <div
                    className="flex items-center gap-1.5 text-[10.5px]"
                    style={{ fontFamily: "var(--mono)", color: "var(--text-faint)" }}
                  >
                    {memo.pinned_at && (
                      <span style={{ color: "var(--accent)" }}>
                        <PinIcon filled size={11} />
                      </span>
                    )}
                    <span>{formatTime(memo.created_at)}</span>
                    {memo.image_count > 0 && (
                      <span>{t("memo.image_count_with_dot", { count: memo.image_count })}</span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleExpand(memo.id)}
                    className="icon-btn shrink-0"
                    title={t("memo.collapse")}
                  >
                    <ChevronUpIcon size={12} />
                  </button>
                </div>

                {/* Crucial: no onClick handler anywhere around the Markdown body,
                    allowing drag-selection to work cleanly without being cancelled on mouseup. */}
                <div className="mt-2.5 select-text text-xs leading-relaxed">
                  <Markdown content={memo.body} />
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
