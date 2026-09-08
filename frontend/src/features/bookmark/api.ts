import { del, get, patch, post } from "../../shared/api";
import type {
  Bookmark,
  BookmarkCheckResponse,
  BookmarkCreatePayload,
  BookmarkGroup,
  BookmarkGroupCreatePayload,
  BookmarkGroupOpenResponse,
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

export function openBookmark(id: number): Promise<void> {
  return post<void>(`/bookmarks/${id}/open`);
}

export function revealBookmark(id: number): Promise<void> {
  return post<void>(`/bookmarks/${id}/reveal`);
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

export function openBookmarkGroup(id: number): Promise<BookmarkGroupOpenResponse> {
  return post<BookmarkGroupOpenResponse>(`/bookmark-groups/${id}/open`);
}

export function checkBookmarks(ids?: number[]): Promise<BookmarkCheckResponse> {
  return post<BookmarkCheckResponse>("/bookmarks/check", ids ? { ids } : undefined);
}

