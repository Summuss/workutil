import { useState, type ClipboardEvent, type KeyboardEvent } from "react";

import { useI18n } from "../../shared/i18n";
import { imageDropHandlers } from "../../shared/images";
import { carriesTable, pastedText, type PastedText } from "./clipboard";

interface BlockTextAreaProps {
  initial: string;
  value?: string;
  onChange?: (value: string) => void;
  isDirty?: boolean;
  onDiscard?: () => void;
  busy: boolean;
  hint: string;
  placeholder?: string;
  /** Given, screenshots pasted or dropped here become image blocks instead of
      going nowhere. The composer takes them; the box that edits an existing
      text block does not, because a block does not change kind. */
  onImages?: (files: File[]) => void;
  /** Given, a paste that could be a query result goes straight to the server
      to be cut up, instead of landing in the box as a wall of tabs. Same rule
      as `onImages`: the composer takes them, an editor does not. */
  onTable?: (paste: PastedText) => void;
  /** For an editor, which was opened on purpose. The composer stays put: it
      sits below the blocks, and taking the cursor there on load would scroll a
      long case past the thing you opened it to read. */
  autoFocus?: boolean;
  onCommit: (text: string) => Promise<boolean>;
  onCancel?: () => void;
}

/**
 * The box a text block is written in — both the new one and an old one.
 *
 * Ctrl+Enter commits, the same chord memo is saved with; Escape leaves, when
 * there is something to leave to. Like `InlineEdit`, it does not close itself
 * on a refusal: what was typed stays on screen next to the reason.
 *
 * It is also the one box you keep pasting into, whichever kind of thing is on
 * the clipboard: a screenshot becomes an image block and a query result a
 * table, both the moment they arrive, while ordinary text lands here to be
 * looked over and committed. Which of the three a paste is comes down to what
 * the clipboard is carrying rather than to aiming at a different box first
 * (spec User Stories 8).
 */
export function BlockTextArea({
  initial,
  value,
  onChange,
  isDirty = false,
  onDiscard,
  busy,
  hint,
  placeholder,
  onImages,
  onTable,
  autoFocus = false,
  onCommit,
  onCancel,
}: BlockTextAreaProps) {
  const { t } = useI18n();
  const [internalDraft, setInternalDraft] = useState(initial);
  const draft = value !== undefined ? value : internalDraft;
  const setDraft = onChange ?? setInternalDraft;
  const images = imageDropHandlers<HTMLTextAreaElement>(onImages);

  /**
   * A paste, sent wherever it belongs — or left alone to land in the box.
   *
   * A possible table is asked about *before* images, and that order is the
   * whole point. design.md §6 F5 says "有图片 flavor → image" first, which
   * reads as obvious until you copy a range out of Excel: it puts three things
   * on the clipboard — the TSV, the `<table>` markup, and a PNG picture of the
   * cells. Checking images first turns a spreadsheet into a screenshot, which
   * is the one outcome this whole kind exists to prevent (spec User Stories
   * 10). An image flavour means "this is a picture" only when there is nothing
   * better beside it.
   *
   * The narrow question `carriesTable` asks is what keeps that safe. A
   * screenshot carries no tabs and no markup, so it still goes to images; so
   * does an image copied off a web page, whose text is a URL and whose markup
   * is an `<img>`.
   *
   * Images then come from the shared handler rather than being worked out
   * again here: which half of a `DataTransfer` holds them is decided in one
   * place on purpose, because getting it wrong fails silently
   * (`shared/images.ts`).
   *
   * Either way it is only ever a *could*. The server settles what the text is,
   * and says so in the confirmation under the block it makes.
   */
  function handlePaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    if (onTable && carriesTable(event.clipboardData)) {
      event.preventDefault();
      onTable(pastedText(event.clipboardData));
      return;
    }
    images.onPaste(event);
  }

  async function commit() {
    if (busy) {
      return;
    }
    if (await onCommit(draft)) {
      // One rule: a box that committed goes back to what it started as. The
      // composer thereby empties in place and keeps the cursor, which is what
      // makes "keep pasting" work; an editor is closed by whoever opened it
      // and never shows this.
      if (onChange === undefined) {
        setInternalDraft(initial);
      }
    }
  }

  function handleDiscard() {
    if (isDirty) {
      if (!window.confirm(t("common.discard_draft_confirm"))) {
        return;
      }
    }
    onDiscard?.();
    onCancel?.();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // metaKey so the same muscle memory works on macOS.
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      void commit();
    }
    if (event.key === "Escape" && onCancel !== undefined) {
      event.preventDefault();
      onCancel();
    }
  }

  return (
    <div className="flex flex-col gap-1.5">
      <textarea
        autoFocus={autoFocus}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={handleKeyDown}
        onPaste={handlePaste}
        onDrop={images.onDrop}
        onDragOver={images.onDragOver}
        rows={4}
        spellCheck={false}
        placeholder={placeholder}
        className="field-input resize-y leading-relaxed"
        style={{ fontFamily: "var(--mono)", fontSize: "13px" }}
      />
      {onCancel !== undefined ? (
        <div className="flex items-center justify-between">
          <span className="text-xs" style={{ color: "var(--text-faint)" }}>
            {busy ? t("common.saving") : hint}
          </span>
          <div className="flex items-center gap-2">
            {onDiscard !== undefined && (
              <button
                type="button"
                onClick={handleDiscard}
                className="btn-ghost"
                style={{ fontSize: "11.5px", padding: "4px 10px", borderRadius: "6px" }}
              >
                {t("common.discard")}
              </button>
            )}
            <button
              type="button"
              onClick={() => void commit()}
              disabled={busy || draft.trim() === ""}
              className="btn-primary"
              style={{ fontSize: "11.5px", padding: "4px 10px", borderRadius: "6px" }}
            >
              {busy ? t("common.saving") : t("common.save")}
            </button>
          </div>
        </div>
      ) : (
        <p className="text-right text-xs" style={{ color: "var(--text-faint)" }}>
          {busy ? t("common.saving") : hint}
        </p>
      )}
    </div>
  );
}
