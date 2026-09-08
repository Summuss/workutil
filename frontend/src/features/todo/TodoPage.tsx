import { useCallback, useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import { t } from "../../shared/i18n";
import { useLoad } from "../../shared/useLoad";
import {
  completeTodo,
  createTodo,
  deleteTodo,
  listTodos,
  moveTodo,
  reopenTodo,
  updateTodo,
} from "./api";
import { TodoItem } from "./TodoItem";
import type { MoveDirection, TodoListResponse, TodoUpdatePayload } from "./types";

export function TodoPage() {
  const {
    value: loaded,
    setValue: setLoaded,
    loading,
    error,
  } = useLoad<TodoListResponse>(() => listTodos());

  const [newTitle, setNewTitle] = useState("");
  const [newDueDate, setNewDueDate] = useState("");
  const [creating, setCreating] = useState(false);
  const [completedOpen, setCompletedOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const todos = loaded?.todos ?? [];
  const completed = loaded?.completed ?? [];

  const handleCreate = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const clean = newTitle.trim();
      if (!clean || creating) return;

      setCreating(true);
      setActionError(null);
      try {
        const created = await createTodo({
          title: clean,
          due_date: newDueDate || null,
        });
        setNewTitle("");
        setNewDueDate("");
        setLoaded((curr) =>
          curr
            ? {
                ...curr,
                todos: [...curr.todos, created],
              }
            : null,
        );
      } catch (cause) {
        setActionError(messageOf(cause, t("todo.create_failed")));
      } finally {
        setCreating(false);
      }
    },
    [newTitle, newDueDate, creating, setLoaded],
  );

  const handleComplete = useCallback(
    async (id: number) => {
      setActionError(null);
      try {
        const updated = await completeTodo(id);
        setLoaded((curr) => {
          if (!curr) return null;
          return {
            ...curr,
            todos: curr.todos.filter((t) => t.id !== id),
            completed: [updated, ...curr.completed.filter((t) => t.id !== id)],
          };
        });
      } catch (cause) {
        setActionError(messageOf(cause, t("todo.complete_failed")));
      }
    },
    [setLoaded],
  );

  const handleReopen = useCallback(
    async (id: number) => {
      setActionError(null);
      try {
        const updated = await reopenTodo(id);
        setLoaded((curr) => {
          if (!curr) return null;
          return {
            ...curr,
            todos: [...curr.todos, updated].sort((a, b) => a.order - b.order),
            completed: curr.completed.filter((t) => t.id !== id),
          };
        });
      } catch (cause) {
        setActionError(messageOf(cause, t("todo.reopen_failed")));
      }
    },
    [setLoaded],
  );

  const handleUpdate = useCallback(
    async (id: number, payload: TodoUpdatePayload) => {
      setActionError(null);
      try {
        const updated = await updateTodo(id, payload);
        setLoaded((curr) => {
          if (!curr) return null;
          return {
            ...curr,
            todos: curr.todos.map((t) => (t.id === id ? updated : t)),
            completed: curr.completed.map((t) => (t.id === id ? updated : t)),
          };
        });
      } catch (cause) {
        setActionError(messageOf(cause, t("todo.update_failed")));
        throw cause;
      }
    },
    [setLoaded],
  );

  const handleDelete = useCallback(
    async (id: number) => {
      setActionError(null);
      try {
        await deleteTodo(id);
        setLoaded((curr) => {
          if (!curr) return null;
          return {
            ...curr,
            todos: curr.todos.filter((t) => t.id !== id),
            completed: curr.completed.filter((t) => t.id !== id),
          };
        });
      } catch (cause) {
        setActionError(messageOf(cause, t("todo.delete_failed")));
      }
    },
    [setLoaded],
  );

  const handleMove = useCallback(
    async (id: number, to: MoveDirection) => {
      setActionError(null);
      try {
        const reordered = await moveTodo(id, to);
        setLoaded((curr) =>
          curr
            ? {
                ...curr,
                todos: reordered,
              }
            : null,
        );
      } catch (cause) {
        setActionError(messageOf(cause, t("todo.move_failed")));
      }
    },
    [setLoaded],
  );

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-6">
      {/* Low friction input form: enter to save */}
      <div className="flex flex-col gap-1.5 rounded-lg border border-slate-200 bg-white p-3 shadow-xs">
        <form onSubmit={(e) => void handleCreate(e)} className="flex items-center gap-2">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder={t("todo.composer_placeholder")}
            autoFocus
            className="min-w-0 flex-1 rounded-md border border-slate-200 bg-white px-3.5 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300"
          />
          <div className="flex items-center gap-1">
            <input
              type="date"
              value={newDueDate}
              onChange={(e) => setNewDueDate(e.target.value)}
              title={t("todo.optional_due_date")}
              className="rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs text-slate-700 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300"
            />
            {newDueDate && (
              <button
                type="button"
                onClick={() => setNewDueDate("")}
                title={t("todo.clear_date")}
                className="cursor-pointer text-xs text-slate-400 hover:text-slate-600 px-1"
              >
                ✕
              </button>
            )}
          </div>
          <button
            type="submit"
            disabled={creating || newTitle.trim() === ""}
            className="cursor-pointer shrink-0 rounded-md bg-slate-800 px-4 py-2 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {creating ? t("common.saving") : t("common.add")}
          </button>
        </form>
        {actionError !== null && (
          <p className="text-xs text-red-600 px-1">{actionError}</p>
        )}
      </div>

      {error !== null && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Active todos list */}
      <section className="flex flex-col gap-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {t("todo.active_header", { count: todos.length })}
        </h2>

        {loading ? (
          <p className="py-4 text-center text-xs text-slate-400">{t("common.loading")}</p>
        ) : todos.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 p-8 text-center text-xs text-slate-400">
            {t("todo.empty_state")}
          </div>
        ) : (
          <ul className="flex flex-col gap-2">
            {todos.map((todo, index) => (
              <TodoItem
                key={todo.id}
                todo={todo}
                isCompleted={false}
                at={index}
                count={todos.length}
                onToggle={handleComplete}
                onUpdate={handleUpdate}
                onDelete={handleDelete}
                onMove={handleMove}
              />
            ))}
          </ul>
        )}
      </section>

      {/* Completed section: default collapsed */}
      {completed.length > 0 && (
        <section className="mt-2 flex flex-col gap-3">
          <div>
            <button
              type="button"
              onClick={() => setCompletedOpen((prev) => !prev)}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold text-slate-500 hover:bg-slate-200/50 hover:text-slate-800 transition-colors"
            >
              <span className="text-[10px]">{completedOpen ? "▼" : "▶"}</span>
              <span>{t("todo.completed_header", { count: completed.length })}</span>
            </button>
          </div>

          {completedOpen && (
            <ul className="flex flex-col gap-2">
              {completed.map((todo) => (
                <TodoItem
                  key={todo.id}
                  todo={todo}
                  isCompleted={true}
                  onToggle={handleReopen}
                  onUpdate={handleUpdate}
                  onDelete={handleDelete}
                />
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}
