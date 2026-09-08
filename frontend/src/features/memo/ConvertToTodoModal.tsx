import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { messageOf } from "../../shared/api";
import { createTodo } from "../todo/api";
import { firstLine } from "./firstLine";
import type { Memo } from "./types";

interface ConvertToTodoModalProps {
  memo: Memo;
  onClose: () => void;
  onSuccess?: () => void;
}

export function ConvertToTodoModal({
  memo,
  onClose,
  onSuccess,
}: ConvertToTodoModalProps) {
  const [title, setTitle] = useState(() => firstLine(memo.body));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  async function handleSubmit(e?: FormEvent) {
    if (e) e.preventDefault();
    const cleanTitle = title.trim();
    if (!cleanTitle) {
      setError("待办标题不能为空");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await createTodo({
        title: cleanTitle,
        source_memo_id: memo.id,
      });
      onSuccess?.();
      onClose();
    } catch (cause) {
      setError(messageOf(cause, "创建待办失败"));
    } finally {
      setSubmitting(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (e.key === "Escape") {
      e.stopPropagation();
      onClose();
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-xs"
      onClick={onClose}
      onKeyDown={handleKeyDown}
    >
      <div
        className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-5 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h3 className="text-sm font-semibold text-slate-800">转为 Todo</h3>
          <button
            type="button"
            onClick={onClose}
            className="cursor-pointer text-sm text-slate-400 hover:text-slate-600"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="todo-title-input" className="text-xs font-medium text-slate-600">
              待办标题
            </label>
            <input
              id="todo-title-input"
              ref={inputRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="待办内容"
              className="w-full rounded border border-slate-200 px-3 py-1.5 text-sm text-slate-900 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300"
            />
          </div>

          <p className="text-[11px] text-slate-400">
            创建后将保留回溯到本条 Memo 的链接。
          </p>

          {error !== null && <p className="text-xs text-red-600">{error}</p>}

          <div className="mt-2 flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="cursor-pointer rounded px-3 py-1.5 text-xs text-slate-500 hover:bg-slate-100"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={submitting || title.trim() === ""}
              className="cursor-pointer rounded bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
            >
              {submitting ? "创建中…" : "确认创建"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
