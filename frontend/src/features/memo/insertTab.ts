/**
 * Inserts a literal tab character into a textarea while preserving native undo.
 *
 * Uses `document.execCommand("insertText", false, "\t")` to preserve browser
 * Ctrl+Z history. If execCommand returns false or throws (e.g. unsupported or
 * mocked in tests), falls back to manual string slicing with the provided
 * state setter.
 */
export function insertTab(
  textarea: HTMLTextAreaElement,
  fallbackSetState: (value: string) => void,
): void {
  let ok = false;
  try {
    if (typeof document !== "undefined" && typeof document.execCommand === "function") {
      ok = document.execCommand("insertText", false, "\t");
    }
  } catch {
    ok = false;
  }

  if (!ok) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const val = textarea.value;
    const next = val.slice(0, start) + "\t" + val.slice(end);
    fallbackSetState(next);
    queueMicrotask(() => {
      textarea.selectionStart = textarea.selectionEnd = start + 1;
    });
  }
}
