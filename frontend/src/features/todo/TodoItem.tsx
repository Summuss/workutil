import { useEffect, useRef, useState, type FormEvent } from "react";

import { t } from "../../shared/i18n";
import {
  AlignLeftIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ChevronsDownIcon,
  ChevronsUpIcon,
  EditIcon,
  TrashIcon,
} from "../../shared/icons";
import { Markdown } from "../../shared/Markdown";
import { DragHandle, useSortableItem } from "../../shared/sortable";
import { getDueDateStatus } from "./dueDateUtil";
import type { MoveDirection, Todo, TodoUpdatePayload } from "./types";

interface TodoItemProps {
  todo: Todo;
  isCompleted: boolean;
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  at?: number;
  count?: number;
  onToggle: (id: number) => Promise<void>;
  onUpdate: (id: number, payload: TodoUpdatePayload) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
  onMove?: (id: number, to: MoveDirection) => Promise<void>;
}

const MOVES: {
  to: "top" | "bottom";
  Icon: typeof ChevronsUpIcon;
  titleKey: string;
  stuck: (at: number, count: number) => boolean;
}[] = [
  { to: "top", Icon: ChevronsUpIcon, titleKey: "todo.move_top", stuck: (at) => at === 0 },
  { to: "bottom", Icon: ChevronsDownIcon, titleKey: "todo.move_bottom", stuck: (at, count) => at === count - 1 },
];

export function TodoItem({
  todo,
  isCompleted,
  isExpanded = false,
  onToggleExpand,
  at,
  count,
  onToggle,
  onUpdate,
  onDelete,
  onMove,
}: TodoItemProps) {
  const [editing, setEditing] = useState(false);
  const canReorder = !isCompleted && !editing && onMove !== undefined && count !== undefined && count > 1;
  const { ref, style, handleProps } = useSortableItem(todo.id, !canReorder);
  const [title, setTitle] = useState(todo.title);
  const [description, setDescription] = useState(todo.description ?? "");
  const [dueDate, setDueDate] = useState(todo.due_date ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [moving, setMoving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setTitle(todo.title);
    setDescription(todo.description ?? "");
    setDueDate(todo.due_date ?? "");
  }, [todo.title, todo.description, todo.due_date]);

  useEffect(() => {
    if (editing) {
      editInputRef.current?.focus();
      editInputRef.current?.select();
    }
  }, [editing]);

  async function handleToggle() {
    if (toggling) return;
    setToggling(true);
    try {
      await onToggle(todo.id);
    } finally {
      setToggling(false);
    }
  }

  async function handleMove(to: MoveDirection) {
    if (!onMove || moving) return;
    setMoving(true);
    try {
      await onMove(todo.id, to);
    } finally {
      setMoving(false);
    }
  }

  async function handleSave(e?: FormEvent) {
    if (e) e.preventDefault();
    const clean = title.trim();
    if (!clean) {
      setError(t("todo.title_empty"));
      return;
    }
    const cleanDate = dueDate ? dueDate : null;
    if (
      clean === todo.title &&
      cleanDate === todo.due_date &&
      description === (todo.description ?? "")
    ) {
      setEditing(false);
      setError(null);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onUpdate(todo.id, {
        title: clean,
        description: description,
        due_date: cleanDate,
      });
      setEditing(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : t("common.save_failed"));
    } finally {
      setSubmitting(false);
    }
  }

  function handleCancel() {
    setTitle(todo.title);
    setDescription(todo.description ?? "");
    setDueDate(todo.due_date ?? "");
    setEditing(false);
    setError(null);
  }

  async function handleDelete() {
    if (deleting) return;
    setDeleting(true);
    try {
      await onDelete(todo.id);
    } finally {
      setDeleting(false);
    }
  }

  const dueStatus = getDueDateStatus(todo.due_date);
  const dueBadge =
    dueStatus === "none"
      ? null
      : dueStatus === "overdue"
        ? { label: t("todo.overdue", { date: todo.due_date ?? "" }), bg: "var(--danger-tint)", color: "var(--danger)" }
        : dueStatus === "today"
          ? { label: t("todo.due_today"), bg: "var(--warn-tint)", color: "var(--warn)" }
          : { label: todo.due_date ?? "", bg: "transparent", color: "var(--text-faint)" };

  if (editing) {
    return (
      <li className="card p-3">
        <form onSubmit={handleSave} className="flex flex-col gap-2.5">
          <input
            ref={editInputRef}
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                handleCancel();
              }
            }}
            placeholder={t("todo.title_placeholder")}
            className="field-input"
            style={{ fontSize: "13px" }}
          />

          <div className="flex flex-col gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
            <span>{t("todo.description_label")}</span>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              onKeyDown={(e) => {
                if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
                  void handleSave(e);
                } else if (e.key === "Escape") {
                  handleCancel();
                }
              }}
              placeholder={t("todo.description_placeholder")}
              rows={Math.min(10, Math.max(3, description.split("\n").length))}
              className="field-input resize-y leading-relaxed"
              style={{ fontFamily: "var(--mono)", fontSize: "13px" }}
              spellCheck={false}
            />
          </div>

          <div className="flex items-center gap-2.5 text-xs" style={{ color: "var(--text-muted)" }}>
            <span>{t("todo.due_date_label")}</span>
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className="field-input"
              style={{ width: "auto", padding: "4px 8px" }}
            />
            {dueDate && (
              <button type="button" onClick={() => setDueDate("")} className="text-btn">
                {t("todo.clear_date")}
              </button>
            )}
          </div>

          {error !== null && (
            <p className="text-xs" style={{ color: "var(--danger)" }}>
              {error}
            </p>
          )}

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={handleCancel}
              className="btn-ghost"
              style={{ fontSize: "11.5px", padding: "5px 12px", borderRadius: "6px" }}
            >
              {t("common.cancel")}
            </button>
            <button
              type="submit"
              disabled={submitting || title.trim() === ""}
              className="btn-primary"
              style={{ fontSize: "11.5px", padding: "5px 12px", borderRadius: "6px" }}
            >
              {submitting ? t("common.saving") : t("common.save")}
            </button>
          </div>
        </form>
      </li>
    );
  }

  const hasDescription = Boolean(todo.description && todo.description.trim());

  return (
    <li
      ref={ref}
      style={{
        ...style,
        border: `1px solid ${isCompleted ? "var(--border)" : "var(--border)"}`,
        background: isCompleted ? "var(--stripe)" : "var(--surface)",
      }}
      className="group flex flex-col rounded-lg px-3.5 py-2.5 transition-colors"
    >
      <div className="flex items-center gap-3 w-full">
        <button
          type="button"
          onClick={() => void handleToggle()}
          disabled={toggling}
          title={isCompleted ? t("todo.mark_incomplete") : t("todo.mark_complete")}
          className="flex h-[17px] w-[17px] shrink-0 cursor-pointer items-center justify-center rounded-[5px] transition-colors disabled:opacity-50"
          style={
            isCompleted
              ? { background: "var(--accent)" }
              : { border: "1.5px solid var(--border-strong)" }
          }
        >
          {isCompleted && <CheckIcon size={11} style={{ color: "white" }} strokeWidth={3} />}
        </button>

        <span
          onDoubleClick={() => !isCompleted && setEditing(true)}
          className="min-w-0 flex-1 truncate text-[13.5px] select-none"
          style={
            isCompleted
              ? { color: "var(--text-faint)", textDecoration: "line-through" }
              : { color: "var(--text)" }
          }
          title={todo.title}
        >
          {todo.title}
        </span>

        {hasDescription && (
          <button
            type="button"
            onClick={onToggleExpand}
            className="inline-flex shrink-0 items-center gap-1 cursor-pointer transition-opacity hover:opacity-80"
            style={{ color: "var(--text-muted)" }}
            title={isExpanded ? t("todo.collapse") : t("todo.expand")}
          >
            <AlignLeftIcon size={12} />
            {isExpanded ? <ChevronUpIcon size={12} /> : <ChevronDownIcon size={12} />}
          </button>
        )}

        {dueBadge && (
          <span
            className="inline-flex shrink-0 items-center rounded-full px-2 py-1 text-[10.5px]"
            style={{
              fontFamily: "var(--mono)",
              background: isCompleted ? "transparent" : dueBadge.bg,
              color: isCompleted ? "var(--text-faint)" : dueBadge.color,
              textDecoration: isCompleted ? "line-through" : "none",
            }}
          >
            {dueBadge.label}
          </span>
        )}

        {canReorder && at !== undefined && count !== undefined && (
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

        <div className="flex items-center gap-1 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
          {!isCompleted && (
            <button type="button" onClick={() => setEditing(true)} className="icon-btn" title={t("common.edit")}>
              <EditIcon />
            </button>
          )}
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

      {hasDescription && isExpanded && (
        <div
          className="mt-2.5 pt-2 pl-7 text-[13px] border-t border-dashed"
          style={{ borderColor: "var(--border)" }}
        >
          <Markdown content={todo.description} />
        </div>
      )}
    </li>
  );
}
