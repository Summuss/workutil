import { useCallback } from "react";

import { useLoad } from "../../shared/useLoad";
import {
  createBookmark,
  deleteBookmark,
  listBookmarks,
  updateBookmark,
} from "./api";
import { BookmarkForm } from "./BookmarkForm";
import { BookmarkItem } from "./BookmarkItem";
import type {
  Bookmark,
  BookmarkCreatePayload,
  BookmarkUpdatePayload,
} from "./types";

export function BookmarkPage() {
  const {
    value: loaded,
    setValue: setBookmarks,
    loading,
    error,
    setError,
  } = useLoad<Bookmark[]>(() => listBookmarks());
  const bookmarks = loaded ?? [];

  const handleRegister = useCallback(
    async (payload: BookmarkCreatePayload) => {
      const created = await createBookmark(payload);
      setBookmarks((current) => [created, ...(current ?? [])]);
      setError(null);
    },
    [setBookmarks, setError],
  );

  const handleUpdate = useCallback(
    async (id: number, payload: BookmarkUpdatePayload) => {
      const updated = await updateBookmark(id, payload);
      setBookmarks((current) =>
        (current ?? []).map((b) => (b.id === id ? updated : b)),
      );
    },
    [setBookmarks],
  );

  const handleDelete = useCallback(
    async (id: number) => {
      await deleteBookmark(id);
      setBookmarks((current) => (current ?? []).filter((b) => b.id !== id));
    },
    [setBookmarks],
  );

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-6">
      <BookmarkForm onRegister={handleRegister} />

      {error !== null && <p className="text-xs text-red-600">{error}</p>}

      {bookmarks.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-400">
          {loading ? "载入中…" : "还没有书签。在上方粘贴路径登记第一个。"}
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {bookmarks.map((bookmark) => (
            <BookmarkItem
              key={bookmark.id}
              bookmark={bookmark}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
            />
          ))}
        </ul>
      )}
    </main>
  );
}
