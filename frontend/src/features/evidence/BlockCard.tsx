import { useState } from "react";

import { InlineEdit } from "../../shared/InlineEdit";
import { BlockTextArea } from "./BlockTextArea";
import { MOVES, TOOL_BUTTON, type MoveLabels } from "./toolbar";
import type { Block, Move } from "./types";

interface BlockCardProps {
  block: Block;
  at: number;
  count: number;
  busy: boolean;
  onEditText: (text: string) => Promise<boolean>;
  onLabel: (label: string) => Promise<boolean>;
  onMove: (to: Move) => Promise<void>;
  onDelete: () => Promise<void>;
}

/** Blocks stack downwards, so the same four moves point up and down here. */
const MOVE_LABELS: MoveLabels = {
  top: { glyph: "⤒", title: "移到最前" },
  up: { glyph: "↑", title: "上移一位" },
  down: { glyph: "↓", title: "下移一位" },
  bottom: { glyph: "⤓", title: "移到最后" },
};

const LABEL_FIELD =
  "min-w-0 flex-1 rounded-md border border-slate-400 bg-white px-2 py-0.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300";

/**
 * One block: its heading, its content, and what can be done to it.
 *
 * Editing is a button rather than a click on the content, deliberately: memo
 * tried click-to-edit and reverted it within a day (design.md §6 F1). Copying
 * a stack trace out of what you just pasted is an everyday move here too, and
 * drag-selecting text ends in a click that would throw the selection away.
 */
export function BlockCard({
  block,
  at,
  count,
  busy,
  onEditText,
  onLabel,
  onMove,
  onDelete,
}: BlockCardProps) {
  const [editingText, setEditingText] = useState(false);
  const [editingLabel, setEditingLabel] = useState(false);

  async function commitText(text: string): Promise<boolean> {
    const accepted = await onEditText(text);
    if (accepted) {
      setEditingText(false);
    }
    return accepted;
  }

  async function commitLabel(label: string): Promise<void> {
    if (await onLabel(label)) {
      setEditingLabel(false);
    }
  }

  async function remove(): Promise<void> {
    if (window.confirm("确定删除这一段吗?")) {
      await onDelete();
    }
  }

  return (
    <article className="flex flex-col gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2.5">
      <div className="flex items-center gap-1">
        {editingLabel ? (
          <InlineEdit
            initial={block.label ?? ""}
            busy={busy}
            className={LABEL_FIELD}
            placeholder="小标题,比如「事前準備の DB データ」(留空即不要)"
            onCommit={commitLabel}
            onCancel={() => setEditingLabel(false)}
          />
        ) : (
          <button
            type="button"
            title={block.label === null ? "加个小标题" : "改小标题"}
            onClick={() => setEditingLabel(true)}
            className={
              block.label === null
                ? "cursor-pointer text-xs text-slate-300 hover:text-slate-600"
                : "min-w-0 flex-1 cursor-pointer truncate text-left text-xs font-semibold text-slate-700 hover:text-slate-900"
            }
          >
            {block.label ?? "+ 小标题"}
          </button>
        )}

        <div className="ml-auto flex shrink-0 items-center text-xs">
          {MOVES.map(({ to, stuck }) => (
            <button
              key={to}
              type="button"
              title={MOVE_LABELS[to].title}
              disabled={busy || stuck(at, count)}
              onClick={() => void onMove(to)}
              className={TOOL_BUTTON}
            >
              {MOVE_LABELS[to].glyph}
            </button>
          ))}
          <button
            type="button"
            disabled={busy || editingText}
            onClick={() => setEditingText(true)}
            className={TOOL_BUTTON}
          >
            编辑
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void remove()}
            className={`${TOOL_BUTTON} hover:text-red-600`}
          >
            删除
          </button>
        </div>
      </div>

      {/* Only text blocks exist so far; image and table bring their own bodies
          in tickets 05 and 06, and everything above this line is theirs too. */}
      {editingText ? (
        <BlockTextArea
          initial={block.text}
          busy={busy}
          autoFocus
          hint="Ctrl+Enter 保存 · Esc 取消"
          onCommit={commitText}
          onCancel={() => setEditingText(false)}
        />
      ) : (
        <pre className="overflow-x-auto font-mono text-xs leading-relaxed whitespace-pre-wrap text-slate-800">
          {block.text}
        </pre>
      )}
    </article>
  );
}
