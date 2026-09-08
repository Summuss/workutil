import { useState } from "react";

import { InlineEdit } from "../../shared/InlineEdit";
import { BlockTextArea } from "./BlockTextArea";
import { TableBlockView } from "./TableBlockView";
import { MOVES, TOOL_BUTTON, type MoveLabels } from "./toolbar";
import type { Block, Move } from "./types";

/**
 * Everything that can be done to a table, which is everything one kind of
 * block can do that the others cannot.
 *
 * One prop rather than five: they arrive together, they are ignored together
 * by the other two kinds, and a table gaining an operation should not widen
 * every block's interface. There is no `onAddRow` and there never will be —
 * the reason is on the server, beside the endpoints that refuse to grow one.
 */
export interface TableActions {
  onHeader: (hasHeader: boolean) => Promise<void>;
  onCell: (row: number, column: number, value: string) => Promise<boolean>;
  onDeleteRow: (row: number) => Promise<void>;
  onDeleteColumn: (column: number) => Promise<void>;
  /** Takes back a wrong guess — this was a log, not a query result. */
  onAsText: () => Promise<void>;
}

interface BlockCardProps {
  block: Block;
  at: number;
  count: number;
  busy: boolean;
  /** Set when this block is one the server has just guessed the kind of, which
      is what puts the confirmation under it. */
  guessed: boolean;
  onEditText: (text: string) => Promise<boolean>;
  onLabel: (label: string) => Promise<boolean>;
  onMove: (to: Move) => Promise<void>;
  onDelete: () => Promise<void>;
  table: TableActions;
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
 *
 * A block changes kind exactly once and in one direction: a table the server
 * read out of a paste can be told it was a log all along. Nothing else does —
 * an image is retaken and re-pasted, not edited.
 */
export function BlockCard({
  block,
  at,
  count,
  busy,
  guessed,
  onEditText,
  onLabel,
  onMove,
  onDelete,
  table,
}: BlockCardProps) {
  const [editingText, setEditingText] = useState(false);
  const [editingLabel, setEditingLabel] = useState(false);
  const [editingTable, setEditingTable] = useState(false);

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
    // Deleting an image block deletes the screenshot itself, which nothing
    // undoes — hence the same confirmation as any other block, and no more.
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
          {block.kind === "text" && (
            <button
              type="button"
              disabled={busy || editingText}
              onClick={() => setEditingText(true)}
              className={TOOL_BUTTON}
            >
              编辑
            </button>
          )}
          {block.kind === "table" && (
            <>
              {/* Stated rather than toggled blind: the button says which way
                  it will go, and the first row is redrawn the moment it does. */}
              <button
                type="button"
                title="第一行是不是列名 —— 工具猜不出来,由你说了算"
                disabled={busy}
                onClick={() => void table.onHeader(!block.has_header)}
                className={TOOL_BUTTON}
              >
                {block.has_header ? "取消表头" : "设为表头"}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => setEditingTable(!editingTable)}
                className={TOOL_BUTTON}
              >
                {editingTable ? "完成" : "编辑"}
              </button>
              {/* Also here, and not only in the confirmation below, because a
                  wrong guess is often noticed later — on the read-through
                  before exporting, a day after the paste. The confirmation is
                  the one-click version while it is still fresh; this is the
                  door that is still there tomorrow. */}
              <button
                type="button"
                title="识别错了?把它变回一段纯文字,原文一字不差"
                disabled={busy}
                onClick={() => void table.onAsText()}
                className={TOOL_BUTTON}
              >
                改为文字
              </button>
            </>
          )}
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

      {/* The body is the one part that belongs to a kind; everything above
          this line belongs to all of them. */}
      {block.kind === "table" ? (
        <TableBlockView
          block={block}
          busy={busy}
          editing={editingTable}
          onCell={table.onCell}
          onDeleteRow={table.onDeleteRow}
          onDeleteColumn={table.onDeleteColumn}
        />
      ) : block.kind === "image" ? (
        /* Shown whole, scaled down to the card. The file on disk is the
           original — the only resizing this tool does happens on the copy
           inside an exported workbook (design.md §6 F5).

           No `src` fallback: an empty one asks the server for this page again
           and draws the answer as a broken image. */
        block.image_url !== null && (
          <img
            src={block.image_url}
            alt={block.label ?? "截图"}
            className="max-w-full self-start rounded border border-slate-200"
          />
        )
      ) : editingText ? (
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

      {/* The guess, said out loud, with the way out of it beside it.
          Recognising a table is a guess that will sometimes be wrong — an
          indented log has every mark of one — so it costs nothing when right
          and one click when not. It is also the receipt for the paste: this is
          the line that says the thing you just pasted went in (spec 粘贴时的类型判别).
          It is ignorable and it goes on its own: nothing has to be dismissed,
          and it is gone on the next visit to this case — the toolbar keeps the
          correction itself, so what expires here is the reminder, not the way
          out. The kind is checked as well as the guess: correcting one leaves
          its id in `guessed`, and this line has to go the moment it does. */}
      {guessed && block.kind === "table" && (
        <p className="text-xs text-slate-400">
          识别为表格,{block.rows.length} 行 {block.rows[0]?.length ?? 0} 列 ·{" "}
          <button
            type="button"
            disabled={busy}
            onClick={() => void table.onAsText()}
            className="cursor-pointer underline underline-offset-2 hover:text-slate-700 disabled:cursor-default disabled:opacity-40"
          >
            改为纯文字
          </button>
        </p>
      )}
    </article>
  );
}
