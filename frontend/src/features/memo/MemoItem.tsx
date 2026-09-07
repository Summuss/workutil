import { useCallback, useRef, useState, type KeyboardEvent } from "react";

import { messageOf } from "../../shared/api";
import { updateMemo } from "./api";
import { firstLine } from "./firstLine";
import { MemoMarkdown } from "./MemoMarkdown";
import type { Memo } from "./types";

interface MemoItemProps {
  memo: Memo;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onUpdate: (updated: Memo) => void;
}

/**
 * When a memo was written, year included.
 *
 * "I wrote that around last month" is how things get found here (spec 浏览),
 * and a bare 9/7 makes last year look like this year.
 */
function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

/**
 * One memo in the list: a single line, or the whole thing.
 *
 * Expanded, the body is shown once — rendered. Clicking it turns that same
 * block into the textarea, so the click that would put the cursor somewhere is
 * the click that starts the edit; there is no viewing state to leave first
 * (spec 编辑与删除 19).
 */
export function MemoItem({
  memo,
  isExpanded,
  onToggleExpand,
  onUpdate,
}: MemoItemProps) {
  const [draft, setDraft] = useState(memo.body);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // What the textarea holds right now, readable from inside an await. State
  // alone would be the value captured when the request went out.
  const latestDraft = useRef(memo.body);

  function changeDraft(next: string) {
    latestDraft.current = next;
    setDraft(next);
  }

  // Both stamps come from one clock reading when a memo is written, so they
  // are equal until an edit lands.
  const isModified = memo.updated_at !== memo.created_at;
  const isUnsaved = draft !== memo.body;

  const focusEnd = useCallback((element: HTMLTextAreaElement | null) => {
    element?.focus();
    element?.setSelectionRange(element.value.length, element.value.length);
  }, []);

  async function save() {
    const pending = draft;
    if (pending.trim() === "" || saving) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const updated = await updateMemo(memo.id, pending.trim());
      onUpdate(updated);
      // Keystrokes landed while the request was in flight are still worth
      // saving, so leave them — and stay in the editor with them.
      if (latestDraft.current === pending) {
        changeDraft(updated.body);
        setEditing(false);
      }
    } catch (cause) {
      setError(messageOf(cause, "保存失败"));
    } finally {
      setSaving(false);
    }
  }

  function handleEditorKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // metaKey so the same muscle memory works on macOS.
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      void save();
      return;
    }
    // Back to the rendered body. The draft is kept, not thrown away — the
    // header says so — because Escape is too easy to hit by accident.
    if (event.key === "Escape") {
      event.preventDefault();
      setEditing(false);
    }
  }

  if (!isExpanded) {
    return (
      <li>
        <button
          type="button"
          onClick={onToggleExpand}
          className="group flex w-full cursor-pointer items-center justify-between py-2.5 text-left font-mono text-sm text-slate-700 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
        >
          <span className="truncate">{firstLine(memo.body)}</span>
          <span className="ml-2 shrink-0 text-xs text-slate-400 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
            {isUnsaved ? "未保存" : "展开"}
          </span>
        </button>
      </li>
    );
  }

  return (
    <li className="py-3">
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span>创建于 {formatTime(memo.created_at)}</span>
            {isModified && <span>· 修改于 {formatTime(memo.updated_at)}</span>}
            {isUnsaved && <span className="text-amber-600">· 未保存</span>}
          </div>
          <button
            type="button"
            onClick={onToggleExpand}
            className="cursor-pointer text-slate-400 hover:text-slate-600"
          >
            收起
          </button>
        </div>

        {editing ? (
          <div className="mt-3">
            <textarea
              ref={focusEnd}
              value={draft}
              onChange={(event) => changeDraft(event.target.value)}
              onKeyDown={handleEditorKeyDown}
              rows={Math.min(20, Math.max(3, draft.split("\n").length))}
              spellCheck={false}
              placeholder="修改内容…"
              className="w-full resize-y rounded-md border border-slate-200 bg-slate-50/50 p-2.5 font-mono text-xs leading-relaxed text-slate-900 outline-none focus:border-slate-400 focus:bg-white focus:ring-1 focus:ring-slate-300"
            />
            <div className="mt-2 flex min-h-5 items-center justify-between text-xs">
              <span className="text-red-600">{error}</span>
              <div className="flex items-center gap-3">
                <span className="text-slate-400">
                  {saving ? "保存中…" : "Ctrl+Enter 保存 · Esc 收起编辑"}
                </span>
                <button
                  type="button"
                  onClick={() => void save()}
                  disabled={saving || draft.trim() === ""}
                  className="cursor-pointer rounded-sm bg-slate-800 px-3 py-1 text-xs text-white hover:bg-slate-700 disabled:opacity-50"
                >
                  保存
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div
            role="button"
            tabIndex={0}
            aria-label="编辑正文"
            onClick={(event) => {
              // A link in the body should be followed, not edited.
              if (event.target instanceof Element && event.target.closest("a")) {
                return;
              }
              setEditing(true);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                setEditing(true);
              }
            }}
            className="mt-3 cursor-text rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-slate-400"
          >
            <MemoMarkdown content={memo.body} />
          </div>
        )}
      </div>
    </li>
  );
}
