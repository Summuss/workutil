import { useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import type { Bookmark, BookmarkUpdatePayload } from "./types";

interface BookmarkItemProps {
  bookmark: Bookmark;
  onUpdate: (id: number, payload: BookmarkUpdatePayload) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

export function BookmarkItem({ bookmark, onUpdate, onDelete }: BookmarkItemProps) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(bookmark.name);
  const [path, setPath] = useState(bookmark.path);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startEditing() {
    setName(bookmark.name);
    setPath(bookmark.path);
    setError(null);
    setEditing(true);
  }

  function cancelEditing() {
    setEditing(false);
    setError(null);
  }

  async function handleSave(event: FormEvent) {
    event.preventDefault();
    const cleanName = name.trim();
    const cleanPath = path.trim().replace(/^["']|["']$/g, "");

    if (!cleanName || !cleanPath || saving) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onUpdate(bookmark.id, { name: cleanName, path: cleanPath });
      setEditing(false);
    } catch (cause) {
      setError(messageOf(cause, "更新失败"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm(`确定删除书签「${bookmark.name}」吗?`)) {
      return;
    }

    setDeleting(true);
    try {
      await onDelete(bookmark.id);
    } catch (cause) {
      alert(messageOf(cause, "删除失败"));
      setDeleting(false);
    }
  }

  if (editing) {
    return (
      <li className="rounded-md border border-slate-300 bg-white p-3 shadow-xs">
        <form onSubmit={(e) => void handleSave(e)} className="flex flex-col gap-2">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium text-slate-500">名称</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="rounded border border-slate-200 px-2.5 py-1 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
              autoFocus
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium text-slate-500">路径</label>
            <input
              type="text"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              className="rounded border border-slate-200 px-2.5 py-1 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
            />
          </div>

          {error !== null && <p className="text-xs text-red-600">{error}</p>}

          <div className="mt-1 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={cancelEditing}
              className="cursor-pointer rounded px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-100"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={saving || name.trim() === "" || path.trim() === ""}
              className="cursor-pointer rounded bg-slate-800 px-3 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {saving ? "保存中…" : "保存"}
            </button>
          </div>
        </form>
      </li>
    );
  }

  return (
    <li className="group flex items-center justify-between gap-3 rounded-md bg-white px-3 py-2.5 shadow-xs transition-colors hover:bg-slate-50/80">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium text-slate-800">
            {bookmark.name}
          </span>
          <span
            className={`inline-block rounded px-1.5 py-0.5 text-[10px] font-medium ${
              bookmark.is_directory
                ? "bg-amber-50 text-amber-700 border border-amber-200"
                : "bg-sky-50 text-sky-700 border border-sky-200"
            }`}
          >
            {bookmark.is_directory ? "文件夹" : "文件"}
          </span>
        </div>
        <p className="mt-0.5 truncate text-xs text-slate-400 font-mono" title={bookmark.path}>
          {bookmark.path}
        </p>
      </div>

      <div className="flex shrink-0 items-center gap-2 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
        <button
          type="button"
          onClick={startEditing}
          className="cursor-pointer text-xs text-slate-500 hover:text-slate-800"
        >
          编辑
        </button>
        <button
          type="button"
          onClick={() => void handleDelete()}
          disabled={deleting}
          className="cursor-pointer text-xs text-slate-400 hover:text-red-600 disabled:opacity-50"
        >
          {deleting ? "删除中…" : "删除"}
        </button>
      </div>
    </li>
  );
}
