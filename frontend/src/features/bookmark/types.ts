export interface Bookmark {
  id: number;
  name: string;
  path: string;
  is_directory: boolean;
  group_id: number | null;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface BookmarkGroup {
  id: number;
  name: string;
  order: number;
  created_at: string;
  updated_at: string;
  bookmarks: Bookmark[];
}

export interface BookmarkListResponse {
  groups: BookmarkGroup[];
  loose: Bookmark[];
}

export type MoveDirection = "up" | "down" | "top" | "bottom";

export interface BookmarkCreatePayload {
  name: string;
  path: string;
  group_id?: number | null;
}

export interface BookmarkUpdatePayload {
  name?: string;
  path?: string;
  group_id?: number | null;
}

export interface BookmarkGroupCreatePayload {
  name: string;
}

export interface BookmarkGroupUpdatePayload {
  name: string;
}
