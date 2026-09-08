import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { messageOf } from "../../shared/api";
import { t } from "../../shared/i18n";
import { XIcon } from "../../shared/icons";
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
      setError(t("todo.title_empty"));
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
      setError(messageOf(cause, t("todo.create_failed")));
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
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "var(--scrim)" }}
      onClick={onClose}
      onKeyDown={handleKeyDown}
    >
      <div
        className="card w-full max-w-md p-5"
        style={{ boxShadow: "0 24px 48px rgba(15,12,8,0.16), 0 8px 16px rgba(15,12,8,0.08)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-3" style={{ borderBottom: "1px solid var(--border)" }}>
          <h3 className="text-sm font-semibold">{t("memo.convert_to_todo_title")}</h3>
          <button type="button" onClick={onClose} className="icon-btn">
            <XIcon />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="todo-title-input" className="text-xs font-medium" style={{ color: "var(--text-muted)" }}>
              {t("todo.title_label")}
            </label>
            <input
              id="todo-title-input"
              ref={inputRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("todo.title_placeholder")}
              className="field-input"
              style={{ fontSize: "13px", padding: "7px 10px" }}
            />
          </div>

          <p className="text-[11px]" style={{ color: "var(--text-faint)" }}>
            {t("memo.convert_to_todo_hint")}
          </p>

          {error !== null && (
            <p className="text-xs" style={{ color: "var(--danger)" }}>
              {error}
            </p>
          )}

          <div className="mt-2 flex items-center justify-end gap-2">
            <button type="button" onClick={onClose} className="btn-ghost" style={{ fontSize: "12px", padding: "6px 13px", borderRadius: "6px" }}>
              {t("common.cancel")}
            </button>
            <button
              type="submit"
              disabled={submitting || title.trim() === ""}
              className="btn-primary"
              style={{ fontSize: "12px", padding: "6px 14px", borderRadius: "6px" }}
            >
              {submitting ? t("common.creating") : t("memo.confirm_create_todo")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
