import { useCallback, useState, type FormEvent } from "react";

import { arrayMove } from "@dnd-kit/sortable";

import { messageOf } from "../../shared/api";
import { useI18n } from "../../shared/i18n";
import { ChevronDownIcon, ChevronRightIcon, XIcon } from "../../shared/icons";
import { SortableList } from "../../shared/sortable";
import { useLoad } from "../../shared/useLoad";
import { PageLayout } from "../../shared/PageLayout";
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
  // Subscribing here re-renders this whole subtree (and its bare `t()` calls
  // below) when the language switches, instead of leaving it stale until some
  // unrelated state change happens to trigger a re-render.
  const { t } = useI18n();
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

  const handleReorder = useCallback(
    async (id: number | string, targetIndex: number) => {
      const todoId = Number(id);
      setActionError(null);
      const prev = loaded;
      if (!prev) return;

      const oldIndex = prev.todos.findIndex((t) => t.id === todoId);
      if (oldIndex === -1 || oldIndex === targetIndex) return;

      const reorderedOptimistic = arrayMove(prev.todos, oldIndex, targetIndex).map(
        (item, idx) => ({ ...item, order: idx }),
      );

      setLoaded({
        ...prev,
        todos: reorderedOptimistic,
      });

      try {
        const reordered = await moveTodo(todoId, targetIndex);
        setLoaded((curr) => (curr ? { ...curr, todos: reordered } : null));
      } catch (cause) {
        setLoaded(prev);
        setActionError(messageOf(cause, t("todo.move_failed")));
      }
    },
    [loaded, setLoaded, t],
  );

  const handleMove = useCallback(
    (id: number, to: MoveDirection) => {
      if (typeof to === "number") return handleReorder(id, to);
      const targetIndex = to === "top" ? 0 : (loaded?.todos.length ?? 1) - 1;
      return handleReorder(id, targetIndex);
    },
    [loaded, handleReorder],
  );

  return (
    <PageLayout
      fixedHeader={
        <>
          {/* Low friction input form: enter to save */}
          <form
            onSubmit={(e) => void handleCreate(e)}
            className="flex items-center gap-2 rounded-[9px] px-3.5 py-2.5"
            style={{ border: "1px solid var(--border-strong)", background: "var(--surface)" }}
          >
            <input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder={t("todo.composer_placeholder")}
              autoFocus
              className="min-w-0 flex-1 border-none bg-transparent text-[13.5px] outline-none"
              style={{ color: "var(--text)" }}
            />
            <div className="flex items-center gap-1">
              <input
                type="date"
                value={newDueDate}
                onChange={(e) => setNewDueDate(e.target.value)}
                title={t("todo.optional_due_date")}
                className="field-input"
                style={{ width: "auto" }}
              />
              {newDueDate && (
                <button
                  type="button"
                  onClick={() => setNewDueDate("")}
                  title={t("todo.clear_date")}
                  className="icon-btn"
                >
                  <XIcon size={11} />
                </button>
              )}
            </div>
            <button
              type="submit"
              disabled={creating || newTitle.trim() === ""}
              className="btn-primary shrink-0"
            >
              {creating ? t("common.saving") : t("common.add")}
            </button>
          </form>
          {actionError !== null && (
            <p className="px-1 text-xs" style={{ color: "var(--danger)" }}>
              {actionError}
            </p>
          )}

          {error !== null && (
            <div
              className="rounded-md p-3 text-xs"
              style={{ border: "1px solid var(--danger-tint)", background: "var(--danger-tint)", color: "var(--danger)" }}
            >
              {error}
            </div>
          )}
        </>
      }
    >
      {/* Active todos list */}
      {loading ? (
        <p className="py-4 text-center text-xs" style={{ color: "var(--text-faint)" }}>
          {t("common.loading")}
        </p>
      ) : todos.length === 0 ? (
        <div
          className="rounded-lg p-8 text-center text-xs"
          style={{ border: "1px dashed var(--border-strong)", color: "var(--text-faint)" }}
        >
          {t("todo.empty_state")}
        </div>
      ) : (
        <SortableList
          as="ul"
          className="flex flex-col gap-1.5"
          items={todos}
          onReorder={handleReorder}
        >
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
        </SortableList>
      )}

      {/* Completed section: default collapsed */}
      {completed.length > 0 && (
        <section className="mt-1.5 flex flex-col gap-2">
          <button
            type="button"
            onClick={() => setCompletedOpen((prev) => !prev)}
            className="flex cursor-pointer items-center gap-1.5 py-2 text-[12.5px]"
            style={{ color: "var(--text-muted)" }}
          >
            {completedOpen ? <ChevronDownIcon size={13} /> : <ChevronRightIcon size={13} />}
            <span>{t("todo.completed_header", { count: completed.length })}</span>
          </button>

          {completedOpen && (
            <ul className="flex flex-col gap-1.5">
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
    </PageLayout>
  );
}
