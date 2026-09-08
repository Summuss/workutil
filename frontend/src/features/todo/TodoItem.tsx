import { useEffect, useRef, useState, type FormEvent } from "react";

import type { Todo } from "./types";

interface TodoItemProps {
  todo: Todo;
  isCompleted: boolean;
  onToggle: (id: number) => Promise<void>;
  onUpdateTitle: (id: number, title: string) => Promise<void>;
  onDelete: (id: number) => Promise<void>;
}

export function TodoItem({
  todo,
  isCompleted,
  onToggle,
  onUpdateTitle,
  onDelete,
}: TodoItemProps) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(todo.title);
  const [submitting, setSubmitting] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setTitle(todo.title);
  }, [todo.title]);

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

  async function handleSave(e?: FormEvent) {
    if (e) e.preventDefault();
    const clean = title.trim();
    if (!clean) {
      setError("待办内容不能为空");
      return;
    }
    if (clean === todo.title) {
      setEditing(false);
      setError(null);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onUpdateTitle(todo.id, clean);
      setEditing(false);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  function handleCancel() {
    setTitle(todo.title);
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

  if (editing) {
    return (
      <li className="rounded-md border border-slate-300 bg-white p-2.5 shadow-xs">
        <form onSubmit={handleSave} className="flex flex-col gap-2">
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
            className="w-full rounded border border-slate-200 px-2.5 py-1 text-sm text-slate-900 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300"
          />
          {error !== null && <p className="text-xs text-red-600">{error}</p>}
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={handleCancel}
              className="cursor-pointer rounded px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-100"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting || title.trim() === ""}
              className="cursor-pointer rounded bg-slate-800 px-3 py-1 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {submitting ? "保存中…" : "保存"}
            </button>
          </div>
        </form>
      </li>
    );
  }

  return (
    <li
      className={`group flex items-center justify-between gap-3 rounded-md border shadow-xs transition-colors ${
        isCompleted
          ? "border-slate-200/70 bg-slate-100/50 px-3.5 py-2 hover:bg-slate-100/80"
          : "border-slate-200 bg-white px-3.5 py-2.5 hover:bg-slate-50/70"
      }`}
    >
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <button
          type="button"
          onClick={() => void handleToggle()}
          disabled={toggling}
          title={isCompleted ? "标为未完成" : "标为已完成"}
          className={`flex h-4 w-4 shrink-0 cursor-pointer items-center justify-center rounded-full transition-colors disabled:opacity-50 ${
            isCompleted
              ? "bg-slate-400 text-white hover:bg-slate-500"
              : "border border-slate-300 hover:border-slate-500 hover:bg-slate-100"
          }`}
        >
          {isCompleted && (
            <svg
              className="h-2.5 w-2.5 stroke-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="3"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
          )}
        </button>

        <span
          onDoubleClick={() => setEditing(true)}
          className={`min-w-0 flex-1 truncate text-sm select-none ${
            isCompleted
              ? "text-slate-400 line-through"
              : "text-slate-800"
          }`}
          title={todo.title}
        >
          {todo.title}
        </span>
      </div>

      <div className="flex shrink-0 items-center gap-2 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100">
        {!isCompleted && (
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="cursor-pointer text-xs text-slate-400 hover:text-slate-700"
          >
            编辑
          </button>
        )}
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
