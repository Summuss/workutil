import { useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import { BookmarkItem } from "./BookmarkItem";
import type {
  BookmarkGroup,
  BookmarkUpdatePayload,
  MoveDirection,
} from "./types";

interface BookmarkGroupSectionProps {
  group: BookmarkGroup;
  groups: BookmarkGroup[];
  at: number;
  count: number;
  onRenameGroup: (id: number, name: string) => Promise<void>;
  onDeleteGroup: (id: number) => Promise<void>;
  onMoveGroup: (id: number, to: MoveDirection) => Promise<void>;
  onOpenGroup: (id: number) => Promise<void>;
  onUpdateBookmark: (id: number, payload: BookmarkUpdatePayload) => Promise<void>;
  onDeleteBookmark: (id: number) => Promise<void>;
  onMoveBookmark: (id: number, to: MoveDirection) => Promise<void>;
  onOpenBookmark: (id: number) => Promise<void>;
  onRevealBookmark: (id: number) => Promise<void>;
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
  "cursor-pointer rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-slate-200 hover:text-slate-800 disabled:cursor-default disabled:opacity-25";

export function BookmarkGroupSection({
  group,
  groups,
  at,
  count,
  onRenameGroup,
  onDeleteGroup,
  onMoveGroup,
  onOpenGroup,
  onUpdateBookmark,
  onDeleteBookmark,
  onMoveBookmark,
  onOpenBookmark,
  onRevealBookmark,
}: BookmarkGroupSectionProps) {
  const [renaming, setRenaming] = useState(false);
  const [name, setName] = useState(group.name);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [moving, setMoving] = useState(false);
  const [openingGroup, setOpeningGroup] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleOpenGroup() {
    if (openingGroup || group.bookmarks.length === 0) return;
    setOpeningGroup(true);
    try {
      await onOpenGroup(group.id);
    } finally {
      setOpeningGroup(false);
    }
  }

  function startRename() {
    setName(group.name);
    setError(null);
    setRenaming(true);
  }

  function cancelRename() {
    setRenaming(false);
    setError(null);
  }

  async function handleSaveRename(e: FormEvent) {
    e.preventDefault();
    const cleanName = name.trim();
    if (!cleanName || saving) return;

    setSaving(true);
    setError(null);
    try {
      await onRenameGroup(group.id, cleanName);
      setRenaming(false);
    } catch (cause) {
      setError(messageOf(cause, "重命名失败"));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (
      !window.confirm(
        `确定删除组「${group.name}」吗? 组内书签将保留并转换为散装书签。`,
      )
    ) {
      return;
    }

    setDeleting(true);
    try {
      await onDeleteGroup(group.id);
    } catch (cause) {
      alert(messageOf(cause, "删除组失败"));
      setDeleting(false);
    }
  }

  async function handleMove(to: MoveDirection) {
    if (moving) return;
    setMoving(true);
    try {
      await onMoveGroup(group.id, to);
    } catch (cause) {
      alert(messageOf(cause, "移动组失败"));
    } finally {
      setMoving(false);
    }
  }

  return (
    <section className="flex flex-col gap-2 rounded-lg border border-slate-200/90 bg-slate-50/50 p-3.5">
      <div className="group/header flex items-center justify-between gap-2 border-b border-slate-200/70 pb-2">
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <span className="text-sm font-semibold text-slate-700">📁</span>
          {renaming ? (
            <form
              onSubmit={(e) => void handleSaveRename(e)}
              className="flex items-center gap-1.5"
            >
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="rounded border border-slate-300 bg-white px-2 py-0.5 text-xs text-slate-900 focus:border-slate-500 focus:outline-none"
                autoFocus
              />
              <button
                type="submit"
                disabled={saving || name.trim() === ""}
                className="cursor-pointer rounded bg-slate-800 px-2 py-0.5 text-xs text-white hover:bg-slate-700 disabled:opacity-50"
              >
                {saving ? "…" : "保存"}
              </button>
              <button
                type="button"
                onClick={cancelRename}
                className="cursor-pointer rounded px-2 py-0.5 text-xs text-slate-500 hover:bg-slate-200"
              >
                取消
              </button>
              {error !== null && (
                <span className="text-xs text-red-600">{error}</span>
              )}
            </form>
          ) : (
            <div className="flex items-center gap-2 truncate">
              <h2 className="truncate text-sm font-semibold text-slate-800">
                {group.name}
              </h2>
              <span className="text-xs text-slate-400">
                ({group.bookmarks.length})
              </span>
            </div>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <button
            type="button"
            onClick={() => void handleOpenGroup()}
            disabled={openingGroup || group.bookmarks.length === 0}
            className="cursor-pointer rounded bg-slate-800 px-2.5 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {openingGroup ? "正在打开…" : "一键全开"}
          </button>

          {/* Group 4-way reorder buttons */}
          <div className="flex items-center gap-0.5">
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

          {!renaming && (
            <div className="flex items-center gap-1 opacity-40 transition-opacity group-hover/header:opacity-100">
              <button
                type="button"
                onClick={startRename}
                className="cursor-pointer text-xs text-slate-500 hover:text-slate-800"
              >
                改名
              </button>
              <button
                type="button"
                onClick={() => void handleDelete()}
                disabled={deleting}
                className="cursor-pointer text-xs text-slate-400 hover:text-red-600 disabled:opacity-50"
              >
                {deleting ? "删组中…" : "删组"}
              </button>
            </div>
          )}
        </div>
      </div>

      {group.bookmarks.length === 0 ? (
        <p className="py-4 text-center text-xs text-slate-400">
          此组暂无书签。登记时选择此组，或编辑已有书签移入。
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {group.bookmarks.map((bookmark, idx) => (
            <BookmarkItem
              key={bookmark.id}
              bookmark={bookmark}
              groups={groups}
              at={idx}
              count={group.bookmarks.length}
              onUpdate={onUpdateBookmark}
              onDelete={onDeleteBookmark}
              onMove={onMoveBookmark}
              onOpen={onOpenBookmark}
              onReveal={onRevealBookmark}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
