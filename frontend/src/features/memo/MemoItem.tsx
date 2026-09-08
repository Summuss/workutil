import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { messageOf } from "../../shared/api";
import { t } from "../../shared/i18n";
import { formatTime } from "../../shared/time";
import { useImageAttachments } from "../../shared/useImageAttachments";
import { deleteMemo, updateMemo } from "./api";
import { firstLine } from "./firstLine";
import { HighlightText } from "./HighlightText";
import { MemoMarkdown } from "./MemoMarkdown";
import { ConvertToTodoModal } from "./ConvertToTodoModal";
import type { Memo } from "./types";

interface MemoItemProps {
  memo: Memo;
  isExpanded: boolean;
  searchQuery?: string;
  onToggleExpand: () => void;
  onUpdate: (updated: Memo) => void;
  onDelete: (id: number) => void;
}

/**
 * One memo in the list: a single line, or the whole thing.
 *
 * Expanded, the body is shown once — rendered, and inert. Editing starts from
 * the 编辑 button, not from clicking the text: copying a stack trace back out
 * of a memo is a daily move, and a click that starts an edit eats the drag
 * that was selecting it. Both states are still one card with no navigation,
 * which is what spec 编辑与删除 19 is actually about.
 */
export function MemoItem({
  memo,
  isExpanded,
  searchQuery,
  onToggleExpand,
  onUpdate,
  onDelete,
}: MemoItemProps) {
  const [draft, setDraft] = useState(memo.body);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showConvertToTodo, setShowConvertToTodo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // The draft survives server updates if the user is currently editing:
  // background polling or another tab's update must not stomp on keystrokes.
  useEffect(() => {
    if (!editing) {
      changeDraft(memo.body);
    }
  }, [memo.body, editing]);

  // What the textarea holds right now, readable from inside an await. State
  // alone would be the value captured when the request went out.
  const latestDraft = useRef(memo.body);

  function changeDraft(next: string) {
    latestDraft.current = next;
    setDraft(next);
  }

  const {
    handlePaste,
    handleDrop,
    handleDragOver,
    getImagesForSave,
    forgetSavedImages,
  } = useImageAttachments(textareaRef, changeDraft);

  // Both stamps come from one clock reading when a memo is written, so they
  // are equal until an edit lands.
  const isModified = memo.updated_at !== memo.created_at;
  const isUnsaved = draft !== memo.body;

  const focusEnd = (element: HTMLTextAreaElement | null) => {
    textareaRef.current = element;
    if (element) {
      element.focus();
      element.setSelectionRange(element.value.length, element.value.length);
    }
  };

  async function save() {
    const pending = draft;
    if (pending.trim() === "" || saving) {
      return;
    }

    const imagesToSave = getImagesForSave(pending);

    setSaving(true);
    setError(null);
    try {
      const updated = await updateMemo(memo.id, pending.trim(), imagesToSave);
      onUpdate(updated);
      forgetSavedImages(pending);
      // Keystrokes landed while the request was in flight are still worth
      // saving, so leave them — and stay in the editor with them.
      if (latestDraft.current === pending) {
        changeDraft(updated.body);
        setEditing(false);
      }
    } catch (cause) {
      setError(messageOf(cause, t("memo.save_failed")));
    } finally {
      setSaving(false);
    }
  }


  async function handleDelete() {
    if (deleting) {
      return;
    }
    if (!window.confirm(t("memo.delete_confirm"))) {
      return;
    }

    setDeleting(true);
    setError(null);
    try {
      await deleteMemo(memo.id);
      onDelete(memo.id);
    } catch (cause) {
      setError(messageOf(cause, t("memo.delete_failed")));
      setDeleting(false);
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
    const snippets = memo.snippets ?? [];
    const unshown = (memo.snippet_total ?? snippets.length) - snippets.length;

    return (
      <li className="py-2.5">
        <button
          type="button"
          onClick={onToggleExpand}
          className="group flex w-full cursor-pointer items-center justify-between text-left font-mono text-sm text-slate-700 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-400"
        >
          <span className="flex items-center gap-2 truncate">
            <span className="truncate">{firstLine(memo.body)}</span>
            {memo.image_count > 0 && (
              <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 font-sans text-xs text-slate-500">
                {t("memo.image_count", { count: memo.image_count })}
              </span>
            )}
          </span>
          <span className="ml-2 shrink-0 text-xs text-slate-400 opacity-0 transition-opacity group-focus-visible:opacity-100 group-hover:opacity-100">
            {isUnsaved ? t("memo.unsaved") : t("memo.expand")}
          </span>
        </button>

        {/* Outside the button on purpose: a snippet is the line you came to
            copy, and text inside a button cannot be dragged over. */}
        {snippets.length > 0 && (
          <div className="mt-1.5 flex flex-col gap-1 border-l-2 border-slate-200 pl-2.5 font-mono">
            {snippets.map((snippet, index) => (
              <div key={index} className="truncate text-xs leading-relaxed text-slate-500">
                <HighlightText text={snippet} query={searchQuery ?? ""} />
              </div>
            ))}
            {unshown > 0 && (
              <div className="text-xs text-slate-400">
                {t("memo.search_more_matches", { count: unshown })}
              </div>
            )}
          </div>
        )}
      </li>
    );
  }

  return (
    <li className="py-3">
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-xs">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span>{t("memo.created_at", { time: formatTime(memo.created_at) })}</span>
            {isModified && <span>{t("memo.updated_at", { time: formatTime(memo.updated_at) })}</span>}
            {memo.image_count > 0 && <span>{t("memo.image_count_with_dot", { count: memo.image_count })}</span>}
            {isUnsaved && <span className="text-amber-600">{t("memo.unsaved_with_dot")}</span>}
          </div>
          <div className="flex items-center gap-3">
            {!editing && (
              <>
                <button
                  type="button"
                  onClick={() => setShowConvertToTodo(true)}
                  className="cursor-pointer text-slate-400 hover:text-slate-600"
                >
                  {t("memo.to_todo")}
                </button>
                <button
                  type="button"
                  onClick={() => setEditing(true)}
                  className="cursor-pointer text-slate-400 hover:text-slate-600"
                >
                  {t("common.edit")}
                </button>
              </>
            )}
            <button
              type="button"
              onClick={() => void handleDelete()}
              disabled={deleting}
              className="cursor-pointer text-slate-400 hover:text-red-600 disabled:opacity-50"
            >
              {deleting ? t("common.deleting") : t("common.delete")}
            </button>
            <button
              type="button"
              onClick={onToggleExpand}
              className="cursor-pointer text-slate-400 hover:text-slate-600"
            >
              {t("memo.collapse")}
            </button>
          </div>
        </div>

        {editing ? (
          <div className="mt-3">
            <textarea
              ref={focusEnd}
              value={draft}
              onChange={(event) => changeDraft(event.target.value)}
              onKeyDown={handleEditorKeyDown}
              onPaste={handlePaste}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              rows={Math.min(20, Math.max(3, draft.split("\n").length))}
              spellCheck={false}
              placeholder={t("memo.edit_placeholder")}
              className="w-full resize-y rounded-md border border-slate-200 bg-slate-50/50 p-2.5 font-mono text-xs leading-relaxed text-slate-900 outline-none focus:border-slate-400 focus:bg-white focus:ring-1 focus:ring-slate-300"
            />

            <div className="mt-2 flex min-h-5 items-center justify-between text-xs">
              <span className="text-red-600">{error}</span>
              <div className="flex items-center gap-3">
                <span className="text-slate-400">
                  {saving ? t("common.saving") : t("memo.ctrl_enter_save_esc_close")}
                </span>
                <button
                  type="button"
                  onClick={() => void save()}
                  disabled={saving || draft.trim() === ""}
                  className="cursor-pointer rounded-sm bg-slate-800 px-3 py-1 text-xs text-white hover:bg-slate-700 disabled:opacity-50"
                >
                  {t("common.save")}
                </button>
              </div>
            </div>
          </div>
        ) : (
          // Nothing here reacts to a click: dragging across a stack trace to
          // copy it must stay a selection.
          <div className="mt-3">
            {error && <p className="mb-2 text-xs text-red-600">{error}</p>}
            <MemoMarkdown content={memo.body} />
          </div>
        )}
      </div>

      {showConvertToTodo && (
        <ConvertToTodoModal
          memo={memo}
          onClose={() => setShowConvertToTodo(false)}
        />
      )}
    </li>
  );
}
