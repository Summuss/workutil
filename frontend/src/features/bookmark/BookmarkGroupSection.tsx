import { useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import { t } from "../../shared/i18n";
import {
  ChevronsDownIcon,
  ChevronsUpIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  FolderIcon,
} from "../../shared/icons";
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
  Icon: typeof ChevronUpIcon;
  titleKey: string;
  stuck: (at: number, count: number) => boolean;
}[] = [
  { to: "top", Icon: ChevronsUpIcon, titleKey: "bookmark.move_group_top", stuck: (at) => at === 0 },
  { to: "up", Icon: ChevronUpIcon, titleKey: "bookmark.move_group_up", stuck: (at) => at === 0 },
  { to: "down", Icon: ChevronDownIcon, titleKey: "bookmark.move_group_down", stuck: (at, count) => at === count - 1 },
  { to: "bottom", Icon: ChevronsDownIcon, titleKey: "bookmark.move_group_bottom", stuck: (at, count) => at === count - 1 },
];

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
    <section className="card group/header flex flex-col gap-2.5 p-4">
      <div className="flex items-center justify-between gap-2 pb-2" style={{ borderBottom: "1px solid var(--border)" }}>
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <FolderIcon style={{ color: "var(--text-faint)" }} />
          {renaming ? (
            <form onSubmit={(e) => void handleSaveRename(e)} className="flex items-center gap-1.5">
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="field-input"
                style={{ width: "auto" }}
                autoFocus
              />
              <button
                type="submit"
                disabled={saving || name.trim() === ""}
                className="btn-primary"
                style={{ fontSize: "11px", padding: "4px 10px", borderRadius: "5px" }}
              >
                {saving ? "…" : t("common.save")}
              </button>
              <button type="button" onClick={cancelRename} className="text-btn">
                {t("common.cancel")}
              </button>
              {error !== null && (
                <span className="text-xs" style={{ color: "var(--danger)" }}>
                  {error}
                </span>
              )}
            </form>
          ) : (
            <div className="flex items-center gap-2 truncate">
              <h2 className="truncate text-[13.5px] font-medium">{group.name}</h2>
              <span className="text-xs" style={{ color: "var(--text-faint)" }}>
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
            className="btn-ghost"
            style={{ fontSize: "12px", padding: "5px 12px", borderRadius: "6px" }}
          >
            {openingGroup ? t("bookmark.opening_group") : t("bookmark.open_all")}
          </button>

          {/* Group 4-way reorder buttons */}
          <div className="flex items-center gap-0.5">
            {MOVES.map(({ to, Icon, titleKey, stuck }) => (
              <button
                key={to}
                type="button"
                title={t(titleKey)}
                disabled={moving || stuck(at, count)}
                onClick={() => void handleMove(to)}
                className="tool-btn"
              >
                <Icon size={12} />
              </button>
            ))}
          </div>

          {!renaming && (
            <div className="flex items-center gap-2.5 opacity-40 transition-opacity group-hover/header:opacity-100">
              <button type="button" onClick={startRename} className="text-btn">
                {t("bookmark.rename")}
              </button>
              <button
                type="button"
                onClick={() => void handleDelete()}
                disabled={deleting}
                className="text-btn text-btn-danger"
              >
                {deleting ? t("bookmark.deleting_group") : t("bookmark.delete_group")}
              </button>
            </div>
          )}
        </div>
      </div>

      {group.bookmarks.length === 0 ? (
        <p className="py-4 text-center text-xs" style={{ color: "var(--text-faint)" }}>
          {t("bookmark.group_empty")}
        </p>
      ) : (
        <ul className="flex flex-col gap-1.5">
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
