const STORAGE_KEY = "workutil_last_evidence_path";

/**
 * Where the nav bar's Evidence link goes back to.
 *
 * The case being worked in is in the URL, so Back returns to it — but only if
 * you came back by Back. Clicking Evidence in the nav bar is the other way
 * home, and it led to the list: the right door when you are starting something,
 * the wrong one every time you had stepped out of a half-finished workbook to
 * look something up. This remembers the last case actually open so that link
 * can go there instead.
 *
 * The list is still one click away, on the 「返回列表」 link the evidence page
 * already carries in its header — which is why this trade is worth making in
 * this direction and not the other.
 *
 * Only ever a convenience: every reader tolerates a missing or unreadable
 * value, and an evidence that has since been deleted is forgotten by whoever
 * discovers it is gone.
 */
export function rememberEvidencePath(path: string): void {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }
  try {
    localStorage.setItem(STORAGE_KEY, path);
  } catch {
    // localStorage may be unavailable or blocked
  }
}

export function lastEvidencePath(): string | null {
  if (typeof window === "undefined" || !window.localStorage) {
    return null;
  }
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    // Anything that is not an evidence path is not something to navigate to:
    // the key is shared with whatever an older version wrote there.
    return stored !== null && stored.startsWith("/evidence/") ? stored : null;
  } catch {
    return null;
  }
}

export function forgetEvidencePath(): void {
  if (typeof window === "undefined" || !window.localStorage) {
    return;
  }
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // localStorage may be unavailable or blocked
  }
}

/** Forget the remembered path if it points into this evidence. */
export function forgetEvidence(evidenceId: number): void {
  const stored = lastEvidencePath();
  if (stored !== null && stored.startsWith(`/evidence/${evidenceId}/`)) {
    forgetEvidencePath();
  }
}
