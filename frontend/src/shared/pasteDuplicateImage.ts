import { t } from "./i18n";

/**
 * Session-level fingerprint of the most recently successfully pasted image.
 *
 * It is held in memory for the duration of the browser session — not in
 * localStorage, and not segregated by case or page (spec: 比对范围只到「上一张」,
 * 存在会话里, 不分 case、不分页面).
 */
let lastPastedFingerprint: string | null = null;

async function computeSha256(file: File): Promise<string | null> {
  try {
    if (
      typeof crypto === "undefined" ||
      !crypto.subtle ||
      typeof crypto.subtle.digest !== "function"
    ) {
      return null;
    }
    const buffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest("SHA-256", buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  } catch {
    // Silently skip the check if computing the digest throws for any reason.
    // Nothing must block pasting when crypto is unavailable or failing.
    return null;
  }
}

/**
 * Guards against the OS clipboard race where an image paste happens before the
 * screenshot tool finished writing to the clipboard, handing over the previous
 * image instead.
 *
 * When the first image in `files` matches the SHA-256 fingerprint of the last
 * successfully pasted image, prompts the user with `window.confirm`.
 *
 * Returns a callback to record successful completion if the paste should proceed,
 * or `null` if the user cancelled.
 */
export async function guardDuplicateImagePaste(
  files: File[],
): Promise<(() => Promise<void>) | null> {
  if (files.length === 0) {
    return () => Promise.resolve();
  }

  // When pasting multiple images at once, compare only the first one against
  // the previous paste. Selecting two different images in one go is ordinary
  // use and must not trigger internal comparisons.
  const firstFile = files[0];
  if (!firstFile) {
    return () => Promise.resolve();
  }
  const firstHash = await computeSha256(firstFile);

  if (firstHash !== null && firstHash === lastPastedFingerprint) {
    const confirmed = window.confirm(t("image.duplicate_paste_confirm"));
    if (!confirmed) {
      // User cancelled: do not update the last fingerprint.
      return null;
    }
  }

  return async () => {
    // When successful, update the session fingerprint to the last file of the batch.
    const lastFile = files[files.length - 1];
    if (lastFile) {
      const lastHash = await computeSha256(lastFile);
      if (lastHash !== null) {
        lastPastedFingerprint = lastHash;
      }
    }
  };
}
