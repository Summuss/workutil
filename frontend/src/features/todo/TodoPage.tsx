import { useCallback, useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import { useLoad } from "../../shared/useLoad";
import {
  completeTodo,
  createTodo,
  deleteTodo,
  listTodos,
  reopenTodo,
  updateTodo,
} from "./api";
import { TodoItem } from "./TodoItem";
import type { TodoListResponse } from "./types";

export function TodoPage() {
  const {
    value: loaded,
    setValue: setLoaded,
    loading,
    error,
  } = useLoad<TodoListResponse>(() => listTodos());

  const [newTitle, setNewTitle] = useState("");
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
        const created = await createTodo({ title: clean });
        setNewTitle("");
        setLoaded((curr) =>
          curr
            ? {
                ...curr,
                todos: [...curr.todos, created],
              }
            : null,
        );
      } catch (cause) {
        setActionError(messageOf(cause, "创建待办失败"));
      } finally {
        setCreating(false);
      }
    },
    [newTitle, creating, setLoaded],
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
        setActionError(messageOf(cause, "标记完成失败"));
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
            todos: [...curr.todos, updated],
            completed: curr.completed.filter((t) => t.id !== id),
          };
        });
      } catch (cause) {
        setActionError(messageOf(cause, "撤销完成失败"));
      }
    },
    [setLoaded],
  );

  const handleUpdateTitle = useCallback(
    async (id: number, title: string) => {
      setActionError(null);
      try {
        const updated = await updateTodo(id, { title });
        setLoaded((curr) => {
          if (!curr) return null;
          return {
            ...curr,
            todos: curr.todos.map((t) => (t.id === id ? updated : t)),
            completed: curr.completed.map((t) => (t.id === id ? updated : t)),
          };
        });
      } catch (cause) {
        setActionError(messageOf(cause, "更新待办失败"));
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
        setActionError(messageOf(cause, "删除待办失败"));
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
            placeholder="记下一件待办… (按 Enter 保存)"
            autoFocus
            className="min-w-0 flex-1 rounded-md border border-slate-200 bg-white px-3.5 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300"
          />
          <button
            type="submit"
            disabled={creating || newTitle.trim() === ""}
            className="cursor-pointer shrink-0 rounded-md bg-slate-800 px-4 py-2 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {creating ? "保存中…" : "添加"}
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
          待办 ({todos.length})
        </h2>

        {loading ? (
          <p className="py-4 text-center text-xs text-slate-400">载入中…</p>
        ) : todos.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 p-8 text-center text-xs text-slate-400">
            暂无未完成待办，在上方输入并按 Enter 即可记下一条。
          </div>
        ) : (
          <ul className="flex flex-col gap-2">
            {todos.map((todo) => (
              <TodoItem
                key={todo.id}
                todo={todo}
                isCompleted={false}
                onToggle={handleComplete}
                onUpdateTitle={handleUpdateTitle}
                onDelete={handleDelete}
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
              <span>已完成 ({completed.length})</span>
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
                  onUpdateTitle={handleUpdateTitle}
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
