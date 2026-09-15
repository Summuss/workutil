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

/** Fixes up a draft on its way back out of storage. See `useDraft`. */
export type RestoreDraft<T> = (stored: T) => T;

/**
 * Drop a draft whose owner has just gone.
 *
 * The `savedAt` rule cleans up after itself for drafts of something that still
 * exists — but a composer drafts against the empty string, which never stops
 * matching, so the key for a deleted case would sit there for good. Deleting
 * the thing is the moment to say so, the same way a deleted block drops its.
 */
export function forgetDraft(key: string): void {
  removeStorage(key);
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
 *
 * `restore` runs on what comes back out of storage and nothing else. Some of a
 * draft may not survive the trip — a memo body can name screenshots that were
 * only ever in memory — and dropping those is a question about the thing being
 * drafted, not about drafting, so the answer belongs at the call site.
 */
export function useDraft<T>(
  key: string,
  saved: T,
  restore?: RestoreDraft<T>,
): DraftHandle<T> {
  const restoreRef = useRef(restore);
  restoreRef.current = restore;

  const takeStored = useCallback((forKey: string, against: T): T | null => {
    const stored = readStorage<T>(forKey, against);
    if (stored === null) {
      return null;
    }
    const fixUp = restoreRef.current;
    return fixUp ? fixUp(stored) : stored;
  }, []);

  const [draft, setDraftState] = useState<T>(() => {
    const stored = takeStored(key, saved);
    return stored !== null ? stored : saved;
  });

  const prevKeyRef = useRef(key);
  const prevSavedRef = useRef(saved);
  // The draft as it stands right now, readable from the effect below without
  // being one of its dependencies — that effect must not re-run on every
  // keystroke.
  const draftRef = useRef(draft);
  draftRef.current = draft;

  useEffect(() => {
    const previousKey = prevKeyRef.current;
    const previousSaved = prevSavedRef.current;
    prevKeyRef.current = key;
    prevSavedRef.current = saved;

    if (previousKey !== key) {
      const stored = takeStored(key, saved);
      setDraftState(stored !== null ? stored : saved);
      return;
    }

    if (!isEqual(previousSaved, saved)) {
      // The saved value moved underneath an open draft. Follow it only when
      // there was nothing unsaved to lose — keystrokes that landed while a
      // save was in flight are still worth keeping, and stomping them here is
      // exactly what the effect this hook replaced used to get wrong. A draft
      // that outlives the value it was written against is caught on the next
      // load instead, where `savedAt` no longer matches and `readStorage`
      // drops it.
      if (isEqual(draftRef.current, previousSaved)) {
        setDraftState(saved);
      }
    }
  }, [key, saved, takeStored]);

  // Persistence is an effect rather than something the state updater does on
  // the way past. An updater has to be pure — React may call it twice or throw
  // its result away — and writing from inside one also races `commit()`: the
  // removal runs first, then the queued updater puts the key straight back.
  useEffect(() => {
    if (!key) {
      return;
    }
    if (isEqual(draft, saved)) {
      removeStorage(key);
    } else {
      writeStorage(key, draft, saved);
    }
  }, [key, draft, saved]);

  const isDirty = !isEqual(draft, saved);

  const setDraft = useCallback((next: T | ((current: T) => T)) => {
    setDraftState((current) =>
      typeof next === "function" ? (next as (current: T) => T)(current) : next,
    );
  }, []);

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
