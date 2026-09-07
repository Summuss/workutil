import { get, patch, post } from "../../shared/api";
import type { Memo } from "./types";

export function listMemos(): Promise<Memo[]> {
  return get<Memo[]>("/memos");
}

export function createMemo(body: string): Promise<Memo> {
  return post<Memo>("/memos", { body });
}

export function updateMemo(id: number, body: string): Promise<Memo> {
  return patch<Memo>(`/memos/${id}`, { body });
}
