import { useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import type {
  Bookmark,
  BookmarkGroup,
  BookmarkStatus,
  BookmarkUpdatePayload,
  MoveDirection,
} from "./types";

interface BookmarkItemProps {
  bookmark: Bookmark;
  status: BookmarkStatus;
  groups: BookmarkGroup[];
  at: number;
  count: number;
  onUpdate: (id: number, payload: BookmarkUpdatePayload) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  onMove: (id: number, to: MoveDirection) => Promise<void>;
  onOpen: (id: number) => Promise<void>;
  onReveal: (id: number) => Promise<void>;
}

const MOVES: {
  to: MoveDirection;
  glyph: string;
  title: string;
  stuck: (at: number, count: number) => boolean;
}[] = [
  { to: "top", glyph: "⤒", title: "移到最前", stuck: (at) => at === 0 },
  { to: "up", glyph: "↑", title: "上移一位", stuck: (at) => at === 0 },
  { to: "down", glyph: "↓", title: "下移一位", stuck: (at, count) => at === count - 1 },
  { to: "bottom", glyph: "⤓", title: "移到最后", stuck: (at, count) => at === count - 1 },
];

const TOOL_BUTTON =
  "cursor-pointer rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:cursor-default disabled:opacity-25";

export function BookmarkItem({
  bookmark,
  status,
  groups,
  at,
  count,
  onUpdate,
  onDelete,
  onMove,
  onOpen,
  onReveal,
}: BookmarkItemProps) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(bookmark.name);
  const [path, setPath] = useState(bookmark.path);
  const [groupId, setGroupId] = useState<number | null>(bookmark.group_id);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [moving, setMoving] = useState(false);
  const [opening, setOpening] = useState(false);
  const [revealing, setRevealing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleOpen() {
    if (opening) return;
    setOpening(true);
    try {
      await onOpen(bookmark.id);
    } finally {
      setOpening(false);
    }
  }

  async function handleReveal() {
    if (revealing) return;
    setRevealing(true);
    try {
      await onReveal(bookmark.id);
    } finally {
      setRevealing(false);
    }
  }

  function startEditing() {
    setName(bookmark.name);
    setPath(bookmark.path);
    setGroupId(bookmark.group_id);
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

    // Only send fields that actually changed. A bookmark whose file has
    // moved away is exactly the one someone needs to rename without also
    // re-submitting (and re-validating) a path they didn't touch.
    const payload: BookmarkUpdatePayload = {};
    if (cleanName !== bookmark.name) payload.name = cleanName;
    if (cleanPath !== bookmark.path) payload.path = cleanPath;
    if (groupId !== bookmark.group_id) payload.group_id = groupId;

    if (Object.keys(payload).length === 0) {
      setEditing(false);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onUpdate(bookmark.id, payload);
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

  async function handleMove(to: MoveDirection) {
    if (moving) return;
    setMoving(true);
    try {
      await onMove(bookmark.id, to);
    } catch (cause) {
      alert(messageOf(cause, "移动失败"));
    } finally {
      setMoving(false);
    }
  }

  if (editing) {
    return (
      <li className="rounded-md border border-slate-300 bg-white p-3 shadow-xs">
        <form onSubmit={(e) => void handleSave(e)} className="flex flex-col gap-2">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
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
              <label className="text-[11px] font-medium text-slate-500">所属组</label>
              <select
                value={groupId ?? ""}
                onChange={(e) => setGroupId(e.target.value ? Number(e.target.value) : null)}
                className="rounded border border-slate-200 px-2 py-1 text-xs text-slate-900 focus:border-slate-400 focus:outline-none"
              >
                <option value="">散装 (无分组)</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
              </select>
            </div>
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

  const isStale = status === "stale";

  return (
    <li
      className={`group flex items-center justify-between gap-3 rounded-md px-3 py-2.5 shadow-xs transition-colors ${
        isStale
          ? "border border-dashed border-slate-300 bg-slate-100/60 hover:bg-slate-100/90"
          : "bg-white hover:bg-slate-50/80"
      }`}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={`truncate text-sm font-medium ${
              isStale ? "text-slate-600" : "text-slate-800"
            }`}
          >
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

          {status === "unknown" && (
            <span
              className="inline-flex items-center gap-1 rounded border border-slate-200 bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium text-slate-500"
              title="检测中或尚未验证路径存在性"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-pulse" />
              未知
            </span>
          )}
          {status === "valid" && (
            <span
              className="inline-flex items-center gap-1 rounded border border-emerald-200 bg-emerald-50 px-1.5 py-0.5 text-[10px] font-medium text-emerald-700"
              title="路径有效，文件/目录存在"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              有效
            </span>
          )}
          {status === "stale" && (
            <span
              className="inline-flex items-center gap-1 rounded border border-slate-300 bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold text-slate-700 shadow-xs"
              title="路径不存在或已失效"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />
              失效
            </span>
          )}
        </div>

        {isStale ? (
          <p className="mt-0.5 truncate text-xs font-mono" title={bookmark.path}>
            <span className="line-through text-slate-400">{bookmark.path}</span>
            <span className="ml-1.5 font-sans text-[11px] font-normal text-rose-600">
              [路径不存在]
            </span>
          </p>
        ) : (
          <p className="mt-0.5 truncate text-xs text-slate-400 font-mono" title={bookmark.path}>
            {bookmark.path}
          </p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => void handleOpen()}
            disabled={opening}
            className={`cursor-pointer rounded px-2.5 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
              isStale
                ? "bg-slate-200/80 text-slate-500 hover:bg-slate-300 hover:text-slate-800"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200 hover:text-slate-900"
            }`}
          >
            {opening ? "打开中…" : "打开"}
          </button>
          {!bookmark.is_directory && (
            <button
              type="button"
              onClick={() => void handleReveal()}
              disabled={revealing}
              className={`cursor-pointer rounded px-2 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                isStale
                  ? "bg-slate-200/80 text-slate-500 hover:bg-slate-300 hover:text-slate-800"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900"
              }`}
            >
              {revealing ? "定位中…" : "打开所在文件夹"}
            </button>
          )}
        </div>

        <div className="flex items-center gap-0.5 opacity-40 transition-opacity group-hover:opacity-100">
          {MOVES.map((move) => (
            <button
              key={move.to}
              type="button"
              title={move.title}
              disabled={moving || move.stuck(at, count)}
              onClick={() => void handleMove(move.to)}
              className={TOOL_BUTTON}
            >
              {move.glyph}
            </button>
          ))}
        </div>

        <div className="ml-1 flex shrink-0 items-center gap-2 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
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
      </div>
    </li>
  );
}
