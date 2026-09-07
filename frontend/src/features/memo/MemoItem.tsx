import { useEffect, useState, type KeyboardEvent } from "react";

import { messageOf } from "../../shared/api";
import { updateMemo } from "./api";
import { firstLine } from "./firstLine";
import { MemoMarkdown } from "./MemoMarkdown";
import type { Memo } from "./types";

interface MemoItemProps {
  memo: Memo;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onUpdate: (updated: Memo) => void;
}

function formatTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function MemoItem({
  memo,
  isExpanded,
  onToggleExpand,
  onUpdate,
}: MemoItemProps) {
  const [body, setBody] = useState(memo.body);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep local body in sync if memo prop changes from outside
  useEffect(() => {
    setBody(memo.body);
  }, [memo.body]);

  async function handleSave() {
    const text = body.trim();
    if (text === "" || saving) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const updated = await updateMemo(memo.id, text);
      onUpdate(updated);
    } catch (cause) {
      setError(messageOf(cause, "保存失败"));
    } finally {
      setSaving(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      void handleSave();
    }
  }

  const isModified =
    new Date(memo.updated_at).getTime() - new Date(memo.created_at).getTime() >
    1000;

  if (!isExpanded) {
    return (
      <li
        onClick={onToggleExpand}
        className="group flex cursor-pointer items-center justify-between py-2.5 font-mono text-sm text-slate-700 hover:text-slate-900"
      >
        <span className="truncate">{firstLine(memo.body)}</span>
        <span className="ml-2 shrink-0 text-xs text-slate-400 opacity-0 transition-opacity group-hover:opacity-100">
          展开
        </span>
      </li>
    );
  }

  return (
    <li className="py-3">
      <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-xs">
        {/* Header & meta */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-2.5 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span>创建于 {formatTime(memo.created_at)}</span>
            {isModified && (
              <span>· 修改于 {formatTime(memo.updated_at)}</span>
            )}
          </div>
          <button
            type="button"
            onClick={onToggleExpand}
            className="cursor-pointer text-slate-400 hover:text-slate-600"
          >
            收起
          </button>
        </div>

        {/* Rendered Markdown Preview */}
        <div className="my-3">
          <MemoMarkdown content={body} />
        </div>

        {/* Plain Text Editor */}
        <div className="mt-3 border-t border-slate-100 pt-3">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={Math.min(10, Math.max(3, body.split("\n").length))}
            spellCheck={false}
            placeholder="修改内容…"
            className="w-full resize-y rounded-md border border-slate-200 bg-slate-50/50 p-2.5 font-mono text-xs leading-relaxed text-slate-900 outline-none focus:border-slate-400 focus:bg-white focus:ring-1 focus:ring-slate-300"
          />
          <div className="mt-2 flex min-h-5 items-center justify-between text-xs">
            <span className="text-red-600">{error}</span>
            <div className="flex items-center gap-3">
              <span className="text-slate-400">
                {saving ? "保存中…" : "Ctrl+Enter 保存"}
              </span>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || body.trim() === ""}
                className="cursor-pointer rounded-sm bg-slate-800 px-3 py-1 text-xs text-white hover:bg-slate-700 disabled:opacity-50"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      </div>
    </li>
  );
}
