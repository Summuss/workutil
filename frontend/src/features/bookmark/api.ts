import { del, get, patch, post } from "../../shared/api";
import type {
  Bookmark,
  BookmarkCreatePayload,
  BookmarkGroup,
  BookmarkGroupCreatePayload,
  BookmarkGroupUpdatePayload,
  BookmarkListResponse,
  BookmarkUpdatePayload,
  MoveDirection,
} from "./types";

export function listBookmarks(): Promise<BookmarkListResponse> {
  return get<BookmarkListResponse>("/bookmarks");
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

export function moveBookmark(
  id: number,
  to: MoveDirection,
): Promise<Bookmark[]> {
  return post<Bookmark[]>(`/bookmarks/${id}/move`, { to });
}

export function createBookmarkGroup(
  payload: BookmarkGroupCreatePayload,
): Promise<BookmarkGroup> {
  return post<BookmarkGroup>("/bookmark-groups", payload);
}

export function updateBookmarkGroup(
  id: number,
  payload: BookmarkGroupUpdatePayload,
): Promise<BookmarkGroup> {
  return patch<BookmarkGroup>(`/bookmark-groups/${id}`, payload);
}

export function deleteBookmarkGroup(id: number): Promise<void> {
  return del(`/bookmark-groups/${id}`);
}

export function moveBookmarkGroup(
  id: number,
  to: MoveDirection,
): Promise<BookmarkGroup[]> {
  return post<BookmarkGroup[]>(`/bookmark-groups/${id}/move`, { to });
}
