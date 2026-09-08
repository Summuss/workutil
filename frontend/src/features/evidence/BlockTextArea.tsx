import { useState, type ClipboardEvent, type KeyboardEvent } from "react";

import { imageDropHandlers } from "../../shared/images";
import { carriesTable, pastedText, type PastedText } from "./clipboard";

interface BlockTextAreaProps {
  initial: string;
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
  busy,
  hint,
  placeholder,
  onImages,
  onTable,
  autoFocus = false,
  onCommit,
  onCancel,
}: BlockTextAreaProps) {
  const [draft, setDraft] = useState(initial);
  const images = imageDropHandlers<HTMLTextAreaElement>(onImages);

  /**
   * A paste, sent wherever it belongs — or left alone to land in the box.
   *
   * Images first, and asked of the shared handler rather than worked out again
   * here: which half of a `DataTransfer` holds them is decided in one place on
   * purpose, because getting it wrong fails silently (`shared/images.ts`).
   * Taking a paste is exactly what calling `preventDefault` means, so that is
   * the answer this reads.
   *
   * What is left could be a query result — only ever a *could*. The server
   * settles it, and says so in the confirmation under the block it makes.
   */
  function handlePaste(event: ClipboardEvent<HTMLTextAreaElement>) {
    images.onPaste(event);
    if (event.defaultPrevented) {
      return;
    }
    if (onTable && carriesTable(event.clipboardData)) {
      event.preventDefault();
      onTable(pastedText(event.clipboardData));
    }
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
      setDraft(initial);
    }
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
    <div className="flex flex-col gap-1">
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
        className="w-full resize-y rounded-md border border-slate-300 bg-white p-2.5 font-mono text-xs leading-relaxed text-slate-900 outline-none placeholder:text-slate-400 focus:border-slate-400 focus:ring-1 focus:ring-slate-200"
      />
      <p className="text-right text-xs text-slate-400">
        {busy ? "保存中…" : hint}
      </p>
    </div>
  );
}
