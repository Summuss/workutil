/**
 * A memo as the backend sends it.
 *
 * There is no title: the line shown in the list is cut from the body here, in
 * the UI. See `firstLine`.
 */
export interface Memo {
  id: number;
  body: string;
  created_at: string;
  updated_at: string;
  pinned_at: string | null;
  image_count: number;
  snippets?: string[];
  /** How many places matched — can exceed what `snippets` shows. */
  snippet_total?: number;
}
