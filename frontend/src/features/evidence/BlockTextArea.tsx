import { useState, type KeyboardEvent } from "react";

interface BlockTextAreaProps {
  initial: string;
  busy: boolean;
  hint: string;
  placeholder?: string;
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
 */
export function BlockTextArea({
  initial,
  busy,
  hint,
  placeholder,
  autoFocus = false,
  onCommit,
  onCancel,
}: BlockTextAreaProps) {
  const [draft, setDraft] = useState(initial);

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
