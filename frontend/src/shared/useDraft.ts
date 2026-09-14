import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Structural equality helper for primitive types and simple JSON-serializable objects.
 */
function isEqual<T>(a: T, b: T): boolean {
  if (a === b) return true;
  if (
    typeof a === "object" &&
    a !== null &&
    typeof b === "object" &&
    b !== null
  ) {
    return JSON.stringify(a) === JSON.stringify(b);
  }
  return false;
}

interface StoredDraft<T> {
  draft: T;
  savedAt: T;
}

function readStorage<T>(key: string, saved: T): T | null {
  if (!key || typeof window === "undefined" || !window.localStorage) {
    return null;
  }
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as StoredDraft<T>;
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      "draft" in parsed &&
      "savedAt" in parsed
    ) {
      if (isEqual(parsed.savedAt, saved)) {
        return parsed.draft;
      }
      // Draft is stale: savedAt does not match the currently saved content
      // (modified in another tab, deleted, or expired). Clean up immediately.
      localStorage.removeItem(key);
    }
  } catch {
    // localStorage may be unavailable or blocked
  }
  return null;
}

function writeStorage<T>(key: string, draft: T, savedAt: T): void {
  if (!key || typeof window === "undefined" || !window.localStorage) {
    return;
  }
  try {
    const stored: StoredDraft<T> = { draft, savedAt };
    localStorage.setItem(key, JSON.stringify(stored));
  } catch {
    // ignore storage failures
  }
}

function removeStorage(key: string): void {
  if (!key || typeof window === "undefined" || !window.localStorage) {
    return;
  }
  try {
    localStorage.removeItem(key);
  } catch {
    // ignore storage failures
  }
}

export interface DraftHandle<T> {
  draft: T;
  setDraft: (next: T | ((current: T) => T)) => void;
  isDirty: boolean;
  discard: () => void;
  commit: () => void;
}

/**
 * Shared draft persistence across refreshes and page switches.
 *
 * A draft represents one unsaved edit session. It survives closing the editor,
 * switching pages, and refreshing the browser, until it is saved (`commit()`)
 * or explicitly discarded (`discard()`).
 *
 * Stale drafts self-clean: the draft is saved alongside `savedAt` (the saved
 * content when the draft was written). If the saved content no longer matches
 * `savedAt` (e.g. edited in another tab), the draft is silently dropped.
 */
export function useDraft<T>(key: string, saved: T): DraftHandle<T> {
  const [draft, setDraftState] = useState<T>(() => {
    const stored = readStorage<T>(key, saved);
    return stored !== null ? stored : saved;
  });

  const prevKeyRef = useRef(key);
  const prevSavedRef = useRef(saved);

  useEffect(() => {
    const keyChanged = prevKeyRef.current !== key;
    const savedChanged = !isEqual(prevSavedRef.current, saved);

    prevKeyRef.current = key;
    prevSavedRef.current = saved;

    if (keyChanged || savedChanged) {
      const stored = readStorage<T>(key, saved);
      setDraftState(stored !== null ? stored : saved);
    }
  }, [key, saved]);

  const isDirty = !isEqual(draft, saved);

  const setDraft = useCallback(
    (next: T | ((current: T) => T)) => {
      setDraftState((current) => {
        const resolved =
          typeof next === "function"
            ? (next as (current: T) => T)(current)
            : next;

        if (isEqual(resolved, saved)) {
          removeStorage(key);
        } else {
          writeStorage(key, resolved, saved);
        }
        return resolved;
      });
    },
    [key, saved],
  );

  const discard = useCallback(() => {
    removeStorage(key);
    setDraftState(saved);
  }, [key, saved]);

  const commit = useCallback(() => {
    removeStorage(key);
  }, [key]);

  return {
    draft,
    setDraft,
    isDirty,
    discard,
    commit,
  };
}
