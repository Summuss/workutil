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
  image_count: number;
}

export interface ImageUpload {
  id: string;
  data: string;
  filename: string;
}

