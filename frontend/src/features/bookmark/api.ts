import { del, get, patch, post } from "../../shared/api";
import type {
  Bookmark,
  BookmarkCreatePayload,
  BookmarkUpdatePayload,
} from "./types";

export function listBookmarks(): Promise<Bookmark[]> {
  return get<Bookmark[]>("/bookmarks");
}

export function createBookmark(payload: BookmarkCreatePayload): Promise<Bookmark> {
  return post<Bookmark>("/bookmarks", payload);
}

export function updateBookmark(
  id: number,
  payload: BookmarkUpdatePayload,
): Promise<Bookmark> {
  return patch<Bookmark>(`/bookmarks/${id}`, payload);
}

export function deleteBookmark(id: number): Promise<void> {
  return del(`/bookmarks/${id}`);
}
