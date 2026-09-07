/**
 * A screenshot on its way to the server, still only a data URL.
 *
 * Mirrors `ImageUpload` in `backend/app/core/images.py`. It lives in `shared/`
 * because Memo and Evidence both paste screenshots and share this one wire
 * shape — the mechanism, not the concept (ADR-0001).
 */
export interface ImageUpload {
  /** The `temp:` token standing in for this image in the text, until saved. */
  id: string;
  data: string;
  filename: string;
}
