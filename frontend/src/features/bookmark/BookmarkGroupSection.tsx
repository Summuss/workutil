import { useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import { t } from "../../shared/i18n";
import { BookmarkItem } from "./BookmarkItem";
import type {
  BookmarkGroup,
  BookmarkStatus,
  BookmarkUpdatePayload,
  MoveDirection,
} from "./types";

interface BookmarkGroupSectionProps {
  group: BookmarkGroup;
  groups: BookmarkGroup[];
  at: number;
  count: number;
  getStatus: (id: number) => BookmarkStatus;
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
  titleKey: string;
  stuck: (at: number, count: number) => boolean;
}[] = [
  { to: "top", glyph: "⤒", titleKey: "bookmark.move_group_top", stuck: (at) => at === 0 },
  { to: "up", glyph: "↑", titleKey: "bookmark.move_group_up", stuck: (at) => at === 0 },
  { to: "down", glyph: "↓", titleKey: "bookmark.move_group_down", stuck: (at, count) => at === count - 1 },
  { to: "bottom", glyph: "⤓", titleKey: "bookmark.move_group_bottom", stuck: (at, count) => at === count - 1 },
];


const TOOL_BUTTON =
  "cursor-pointer rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-slate-200 hover:text-slate-800 disabled:cursor-default disabled:opacity-25";

export function BookmarkGroupSection({
  group,
  groups,
  at,
  count,
  getStatus,
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
      setError(messageOf(cause, t("bookmark.rename_group_failed")));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (
      !window.confirm(
        t("bookmark.delete_group_confirm", { name: group.name }),
      )
    ) {
      return;
    }

    setDeleting(true);
    try {
      await onDeleteGroup(group.id);
    } catch (cause) {
      alert(messageOf(cause, t("bookmark.delete_group_failed")));
      setDeleting(false);
    }
  }

  async function handleMove(to: MoveDirection) {
    if (moving) return;
    setMoving(true);
    try {
      await onMoveGroup(group.id, to);
    } catch (cause) {
      alert(messageOf(cause, t("bookmark.move_group_failed")));
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
                {saving ? "…" : t("common.save")}
              </button>
              <button
                type="button"
                onClick={cancelRename}
                className="cursor-pointer rounded px-2 py-0.5 text-xs text-slate-500 hover:bg-slate-200"
              >
                {t("common.cancel")}
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
            {openingGroup ? t("bookmark.opening_group") : t("bookmark.open_all")}
          </button>

          {/* Group 4-way reorder buttons */}
          <div className="flex items-center gap-0.5">
            {MOVES.map((move) => (
              <button
                key={move.to}
                type="button"
                title={t(move.titleKey)}
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
                {t("bookmark.rename")}
              </button>
              <button
                type="button"
                onClick={() => void handleDelete()}
                disabled={deleting}
                className="cursor-pointer text-xs text-slate-400 hover:text-red-600 disabled:opacity-50"
              >
                {deleting ? t("bookmark.deleting_group") : t("bookmark.delete_group")}
              </button>
            </div>
          )}
        </div>
      </div>

      {group.bookmarks.length === 0 ? (
        <p className="py-4 text-center text-xs text-slate-400">
          {t("bookmark.group_empty")}
        </p>
      ) : (

        <ul className="flex flex-col gap-2">
          {group.bookmarks.map((bookmark, idx) => (
            <BookmarkItem
              key={bookmark.id}
              bookmark={bookmark}
              status={getStatus(bookmark.id)}
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
