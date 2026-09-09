import { useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import { t } from "../../shared/i18n";
import {
  ChevronsDownIcon,
  ChevronsUpIcon,
  EditIcon,
  TrashIcon,
} from "../../shared/icons";
import { DragHandle, useSortableItem } from "../../shared/sortable";
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
  to: "top" | "bottom";
  Icon: typeof ChevronsUpIcon;
  titleKey: string;
  stuck: (at: number, count: number) => boolean;
}[] = [
  { to: "top", Icon: ChevronsUpIcon, titleKey: "bookmark.move_item_top", stuck: (at) => at === 0 },
  { to: "bottom", Icon: ChevronsDownIcon, titleKey: "bookmark.move_item_bottom", stuck: (at, count) => at === count - 1 },
];

const STATUS_STYLE: Record<BookmarkStatus, { dot: string; bg: string; color: string; border: string }> = {
  unknown: { dot: "var(--text-faint)", bg: "var(--stripe)", color: "var(--text-muted)", border: "var(--border)" },
  valid: { dot: "var(--success)", bg: "var(--success-tint)", color: "var(--success)", border: "var(--success-tint)" },
  stale: { dot: "var(--danger)", bg: "var(--danger-tint)", color: "var(--danger)", border: "var(--danger-tint)" },
};

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
  const canReorder = !editing && count > 1;
  const { ref, style, handleProps } = useSortableItem(bookmark.id, !canReorder);
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
      setError(messageOf(cause, t("bookmark.update_failed")));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm(t("bookmark.delete_item_confirm", { name: bookmark.name }))) {
      return;
    }

    setDeleting(true);
    try {
      await onDelete(bookmark.id);
    } catch (cause) {
      alert(messageOf(cause, t("common.delete_failed")));
      setDeleting(false);
    }
  }

  async function handleMove(to: MoveDirection) {
    if (moving) return;
    setMoving(true);
    try {
      await onMove(bookmark.id, to);
    } catch (cause) {
      alert(messageOf(cause, t("bookmark.move_failed")));
    } finally {
      setMoving(false);
    }
  }

  if (editing) {
    return (
      <li className="card p-3">
        <form onSubmit={(e) => void handleSave(e)} className="flex flex-col gap-2">
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
                {t("bookmark.name_label")}
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="field-input"
                autoFocus
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
                {t("bookmark.group_label")}
              </label>
              <select
                value={groupId ?? ""}
                onChange={(e) => setGroupId(e.target.value ? Number(e.target.value) : null)}
                className="field-input"
              >
                <option value="">{t("bookmark.loose_option")}</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium" style={{ color: "var(--text-muted)" }}>
              {t("bookmark.path_label")}
            </label>
            <input
              type="text"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              className="field-input"
            />
          </div>

          {error !== null && (
            <p className="text-xs" style={{ color: "var(--danger)" }}>
              {error}
            </p>
          )}

          <div className="mt-1 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={cancelEditing}
              className="btn-ghost"
              style={{ fontSize: "11.5px", padding: "5px 12px", borderRadius: "6px" }}
            >
              {t("common.cancel")}
            </button>
            <button
              type="submit"
              disabled={saving || name.trim() === "" || path.trim() === ""}
              className="btn-primary"
              style={{ fontSize: "11.5px", padding: "5px 12px", borderRadius: "6px" }}
            >
              {saving ? t("common.saving") : t("common.save")}
            </button>
          </div>
        </form>
      </li>
    );
  }

  const isStale = status === "stale";
  const statusStyle = STATUS_STYLE[status];

  return (
    <li
      ref={ref}
      className="group flex items-center justify-between gap-3 rounded-lg px-3.5 py-2.5 transition-colors"
      style={{
        ...style,
        border: isStale ? "1px dashed var(--border-strong)" : "1px solid var(--border)",
        background: isStale ? "var(--stripe)" : "var(--surface)",
      }}
    >
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className="truncate text-[13.5px] font-medium"
            style={{ color: isStale ? "var(--text-muted)" : "var(--text)" }}
          >
            {bookmark.name}
          </span>
          <span
            className="inline-block shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium"
            style={
              bookmark.is_directory
                ? { background: "var(--warn-tint)", color: "var(--warn)" }
                : { background: "var(--accent-tint)", color: "var(--accent-strong)" }
            }
          >
            {bookmark.is_directory ? t("bookmark.folder") : t("bookmark.file")}
          </span>

          <span
            className="inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
            style={{ background: statusStyle.bg, color: statusStyle.color }}
            title={
              status === "unknown"
                ? t("bookmark.status_unknown_title")
                : status === "valid"
                  ? t("bookmark.status_valid_title")
                  : t("bookmark.status_stale_title")
            }
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${status === "unknown" ? "animate-pulse" : ""}`}
              style={{ background: statusStyle.dot }}
            />
            {status === "unknown"
              ? t("bookmark.status_unknown")
              : status === "valid"
                ? t("bookmark.status_valid")
                : t("bookmark.status_stale")}
          </span>
        </div>

        {isStale ? (
          <p className="mt-1 truncate text-xs" style={{ fontFamily: "var(--mono)" }} title={bookmark.path}>
            <span style={{ color: "var(--text-faint)", textDecoration: "line-through" }}>{bookmark.path}</span>
            <span className="ml-1.5 text-[11px] font-normal" style={{ fontFamily: "var(--sans)", color: "var(--danger)" }}>
              {t("bookmark.path_not_found_tag")}
            </span>
          </p>
        ) : (
          <p
            className="mt-1 truncate text-xs"
            style={{ fontFamily: "var(--mono)", color: "var(--text-faint)" }}
            title={bookmark.path}
          >
            {bookmark.path}
          </p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2.5">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => void handleOpen()}
            disabled={opening}
            className="btn-ghost"
            style={{ fontSize: "11.5px", padding: "5px 11px", borderRadius: "6px" }}
          >
            {opening ? t("bookmark.opening") : t("bookmark.open")}
          </button>
          {!bookmark.is_directory && (
            <button
              type="button"
              onClick={() => void handleReveal()}
              disabled={revealing}
              className="btn-ghost"
              style={{ fontSize: "11.5px", padding: "5px 11px", borderRadius: "6px" }}
            >
              {revealing ? t("bookmark.revealing") : t("bookmark.reveal")}
            </button>
          )}
        </div>

        {count > 1 && (
          <div className="flex items-center gap-0.5 opacity-40 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
            <DragHandle
              title={t("common.drag_reorder")}
              disabled={moving}
              {...handleProps}
            />
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
        )}

        <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
          <button type="button" onClick={startEditing} className="icon-btn" title={t("common.edit")}>
            <EditIcon />
          </button>
          <button
            type="button"
            onClick={() => void handleDelete()}
            disabled={deleting}
            className="icon-btn icon-btn-danger"
            title={t("common.delete")}
          >
            <TrashIcon />
          </button>
        </div>
      </div>
    </li>
  );
}
