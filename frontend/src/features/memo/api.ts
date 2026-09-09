import { del, get, patch, post } from "../../shared/api";
import type { ImageUpload } from "../../shared/images";
import type { Memo } from "./types";

export function listMemos(query?: string): Promise<Memo[]> {
  const params =
    query && query.trim() ? `?q=${encodeURIComponent(query.trim())}` : "";
  return get<Memo[]>(`/memos${params}`);
}

export function getMemo(id: number): Promise<Memo> {
  return get<Memo>(`/memos/${id}`);
}

export function createMemo(
  body: string,
  images: ImageUpload[] = [],
): Promise<Memo> {
  return post<Memo>("/memos", { body, images });
}

export function updateMemo(
  id: number,
  body: string,
  images: ImageUpload[] = [],
): Promise<Memo> {
  return patch<Memo>(`/memos/${id}`, { body, images });
}


export function deleteMemo(id: number): Promise<void> {
  return del(`/memos/${id}`);
}

export function pinMemo(id: number): Promise<Memo> {
  return post<Memo>(`/memos/${id}/pin`);
}

export function unpinMemo(id: number): Promise<Memo> {
  return del<Memo>(`/memos/${id}/pin`);
}

