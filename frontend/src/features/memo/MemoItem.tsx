import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";

import { messageOf } from "../../shared/api";
import { t } from "../../shared/i18n";
import {
  ChevronDownIcon,
  ChevronUpIcon,
  EditIcon,
  PinIcon,
  TrashIcon,
} from "../../shared/icons";
import { formatTime } from "../../shared/time";
import { useImageAttachments } from "../../shared/useImageAttachments";
import { deleteMemo, pinMemo, unpinMemo, updateMemo } from "./api";
import { firstLine } from "./firstLine";
import { HighlightText } from "./HighlightText";
import { Markdown } from "../../shared/Markdown";
import type { Memo } from "./types";

interface MemoItemProps {
  memo: Memo;
  isExpanded: boolean;
  searchQuery?: string;
  onToggleExpand: () => void;
  onUpdate: (updated: Memo) => void;
  onDelete: (id: number) => void;
}

const META_TEXT = { fontFamily: "var(--mono)", color: "var(--text-faint)" } as const;

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
  const [pinning, setPinning] = useState(false);
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

  // Memoized: this is a ref callback (`ref={focusEnd}` below), and React
  // re-fires a ref callback whenever its identity changes between renders —
  // an unmemoized version here would re-focus and snap the caret to the end
  // on every keystroke while editing.
  const focusEnd = useCallback((element: HTMLTextAreaElement | null) => {
    textareaRef.current = element;
    if (element) {
      element.focus();
      element.setSelectionRange(element.value.length, element.value.length);
    }
  }, []);

  async function handleTogglePin() {
    if (pinning) {
      return;
    }
    setPinning(true);
    setError(null);
    try {
      const updated = memo.pinned_at ? await unpinMemo(memo.id) : await pinMemo(memo.id);
      onUpdate(updated);
    } catch (cause) {
      setError(messageOf(cause, t("common.action_failed")));
    } finally {
      setPinning(false);
    }
  }

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
      <li className="card px-4 py-3">
        <div className="flex items-center justify-between gap-3">
          <span className="flex min-w-0 items-center gap-2">
            <span
              className="truncate"
              style={{ fontFamily: "var(--mono)", fontSize: "13.5px", color: "var(--text)" }}
            >
              {firstLine(memo.body)}
            </span>
            {memo.image_count > 0 && (
              <span
                className="shrink-0 rounded-full px-2 py-0.5 text-[10.5px]"
                style={{ fontFamily: "var(--mono)", background: "var(--hover-wash)", color: "var(--text-muted)" }}
              >
                {t("memo.image_count", { count: memo.image_count })}
              </span>
            )}
            {isUnsaved && (
              <span className="shrink-0 text-[11px]" style={{ color: "var(--warn)" }}>
                {t("memo.unsaved")}
              </span>
            )}
          </span>
          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={() => void handleTogglePin()}
              disabled={pinning}
              className="icon-btn"
              style={memo.pinned_at ? { color: "var(--accent)" } : undefined}
              title={memo.pinned_at ? t("memo.unpin") : t("memo.pin")}
            >
              <PinIcon filled={Boolean(memo.pinned_at)} />
            </button>
            <button
              type="button"
              onClick={onToggleExpand}
              className="icon-btn"
              title={t("memo.expand")}
            >
              <ChevronDownIcon />
            </button>
          </div>
        </div>

        {/* Outside the button on purpose: a snippet is the line you came to
            copy, and text inside a button cannot be dragged over. */}
        {snippets.length > 0 && (
          <div
            className="mt-2 flex flex-col gap-1 pl-2.5"
            style={{ borderLeft: "2px solid var(--border)", fontFamily: "var(--mono)" }}
          >
            {snippets.map((snippet, index) => (
              <div key={index} className="truncate text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <HighlightText text={snippet} query={searchQuery ?? ""} />
              </div>
            ))}
            {unshown > 0 && (
              <div className="text-xs" style={{ color: "var(--text-faint)" }}>
                {t("memo.search_more_matches", { count: unshown })}
              </div>
            )}
          </div>
        )}
      </li>
    );
  }

  return (
    <li className="card px-4 py-3.5">
      <div className="flex items-center justify-between pb-2.5" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2 text-[11px]" style={META_TEXT}>
          <span>{t("memo.created_at", { time: formatTime(memo.created_at) })}</span>
          {isModified && <span>{t("memo.updated_at", { time: formatTime(memo.updated_at) })}</span>}
          {memo.image_count > 0 && <span>{t("memo.image_count_with_dot", { count: memo.image_count })}</span>}
          {isUnsaved && <span style={{ color: "var(--warn)" }}>{t("memo.unsaved_with_dot")}</span>}
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => void handleTogglePin()}
            disabled={pinning}
            className="icon-btn"
            style={memo.pinned_at ? { color: "var(--accent)" } : undefined}
            title={memo.pinned_at ? t("memo.unpin") : t("memo.pin")}
          >
            <PinIcon filled={Boolean(memo.pinned_at)} />
          </button>
          {!editing && (
            <button type="button" onClick={() => setEditing(true)} className="icon-btn" title={t("common.edit")}>
              <EditIcon />
            </button>
          )}
          <button
            type="button"
            onClick={() => void handleDelete()}
            disabled={deleting}
            className="icon-btn icon-btn-danger"
            title={t("common.delete")}
          >
            <TrashIcon />
          </button>
          <button type="button" onClick={onToggleExpand} className="icon-btn" title={t("memo.collapse")}>
            <ChevronUpIcon />
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
            className="field-input resize-y leading-relaxed"
            style={{ fontFamily: "var(--mono)", fontSize: "13px" }}
          />

          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs" style={{ color: "var(--danger)" }}>
              {error}
            </span>
            <div className="flex items-center gap-2.5">
              <span className="text-[11px]" style={META_TEXT}>
                {saving ? t("common.saving") : t("memo.ctrl_enter_save_esc_close")}
              </span>
              <button
                type="button"
                onClick={() => setEditing(false)}
                className="btn-ghost"
                style={{ fontSize: "11.5px", padding: "5px 12px", borderRadius: "6px" }}
              >
                {t("common.cancel")}
              </button>
              <button
                type="button"
                onClick={() => void save()}
                disabled={saving || draft.trim() === ""}
                className="btn-primary"
                style={{ fontSize: "11.5px", padding: "5px 12px", borderRadius: "6px" }}
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
          {error && (
            <p className="mb-2 text-xs" style={{ color: "var(--danger)" }}>
              {error}
            </p>
          )}
          <Markdown content={memo.body} />
        </div>
      )}
    </li>
  );
}
