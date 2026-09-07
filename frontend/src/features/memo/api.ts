import { del, get, patch, post } from "../../shared/api";
import type { ImageUpload, Memo } from "./types";

export function listMemos(): Promise<Memo[]> {
  return get<Memo[]>("/memos");
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

