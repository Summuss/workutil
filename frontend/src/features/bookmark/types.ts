export interface Bookmark {
  id: number;
  name: string;
  path: string;
  is_directory: boolean;
  created_at: string;
  updated_at: string;
}

export interface BookmarkCreatePayload {
  name: string;
  path: string;
}

export interface BookmarkUpdatePayload {
  name?: string;
  path?: string;
}
