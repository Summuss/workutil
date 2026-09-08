/**
 * Extract a human-friendly bookmark name from a file or directory path.
 *
 * Windows "Copy as Path" wraps paths in double quotes, and paths may have
 * trailing slashes or backslashes.
 */
export function extractNameFromPath(rawPath: string): string {
  const unquoted = rawPath.trim().replace(/^["']|["']$/g, "").trim();
  if (!unquoted) {
    return "";
  }

  // Strip trailing slashes or backslashes
  const trimmed = unquoted.replace(/[/\\]+$/, "");
  if (!trimmed) {
    // Path was just "/" or "\\"
    return unquoted;
  }

  const segments = trimmed.split(/[/\\]/);
  const last = segments[segments.length - 1];
  return last ?? "";
}
