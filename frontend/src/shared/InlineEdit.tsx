import { useEffect, useRef, useState, type KeyboardEvent } from "react";

interface InlineEditProps {
  initial: string;
  className: string;
  placeholder?: string;
  busy: boolean;
  onCommit: (value: string) => Promise<void>;
  onCancel: () => void;
}

/**
 * A field that replaces the thing it is editing: Enter commits, Escape leaves.
 *
 * Deliberately not committed on blur, and deliberately not closed by itself
 * when a commit fails. A refused value has to stay on screen, still editable,
 * next to the reason it was refused — which is the whole point of catching an
 * illegal sheet name as it is typed. Whoever renders this closes it once the
 * commit has actually gone through.
 */
export function InlineEdit({
  initial,
  className,
  placeholder,
  busy,
  onCommit,
  onCancel,
}: InlineEditProps) {
  const [draft, setDraft] = useState(initial);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    input.current?.focus();
    input.current?.select();
  }, []);

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      void onCommit(draft);
    }
    if (event.key === "Escape") {
      event.preventDefault();
      onCancel();
    }
  }

  return (
    <input
      ref={input}
      type="text"
      value={draft}
      disabled={busy}
      placeholder={placeholder}
      onChange={(event) => setDraft(event.target.value)}
      onKeyDown={handleKeyDown}
      className={className}
    />
  );
}
