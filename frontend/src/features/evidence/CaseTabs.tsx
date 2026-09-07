import { useState } from "react";

import { InlineEdit } from "../../shared/InlineEdit";
import type { Case, CaseMove } from "./types";

interface CaseTabsProps {
  cases: Case[];
  selectedId: number | null;
  busy: boolean;
  error: string | null;
  onSelect: (caseId: number) => void;
  onAdd: (name: string) => Promise<boolean>;
  onRename: (caseId: number, name: string) => Promise<boolean>;
  onDelete: (caseId: number) => Promise<void>;
  onMove: (caseId: number, to: CaseMove) => Promise<void>;
}

type Editing = { kind: "add" } | { kind: "rename"; caseId: number } | null;

/**
 * The four ordering buttons, each with the position that leaves it nowhere to
 * go. Not a drag — see design.md §6 F5. The backend treats a move past either
 * end as a no-op regardless; greying them out is only so the buttons say so.
 */
const MOVES: {
  to: CaseMove;
  glyph: string;
  title: string;
  stuck: (at: number, count: number) => boolean;
}[] = [
  { to: "top", glyph: "⇤", title: "移到最前", stuck: (at) => at === 0 },
  { to: "up", glyph: "←", title: "前移一位", stuck: (at) => at === 0 },
  {
    to: "down",
    glyph: "→",
    title: "后移一位",
    stuck: (at, count) => at === count - 1,
  },
  {
    to: "bottom",
    glyph: "⇥",
    title: "移到最后",
    stuck: (at, count) => at === count - 1,
  },
];

const TOOL_BUTTON =
  "cursor-pointer rounded px-1.5 py-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:cursor-default disabled:opacity-40";

const NAME_FIELD =
  "w-28 rounded-md border border-slate-400 bg-white px-2 py-1 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300";

/**
 * The cases of one evidence, in the order they will become sheets.
 *
 * A tab bar rather than a list because a case is a place you work *inside*:
 * only one case's content is on screen at a time, and the strip is how you get
 * between them. Left and right here are the "上下移动" of design.md §6 F5 —
 * the tabs run horizontally, so the arrows do too.
 */
export function CaseTabs({
  cases,
  selectedId,
  busy,
  error,
  onSelect,
  onAdd,
  onRename,
  onDelete,
  onMove,
}: CaseTabsProps) {
  const [editing, setEditing] = useState<Editing>(null);

  const selected = cases.find((one) => one.id === selectedId) ?? null;
  const at = selected ? cases.indexOf(selected) : -1;

  // Closed only once the name was actually accepted, so a refused one stays in
  // the box with the reason underneath it.
  async function commit(name: string) {
    if (editing === null) {
      return;
    }
    const accepted =
      editing.kind === "add"
        ? await onAdd(name)
        : await onRename(editing.caseId, name);
    if (accepted) {
      setEditing(null);
    }
  }

  async function remove() {
    if (
      selected === null ||
      !window.confirm(`确定删除用例「${selected.name}」吗?`)
    ) {
      return;
    }
    await onDelete(selected.id);
  }

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-1 overflow-x-auto border-b border-slate-200 pb-1.5">
        {cases.map((one) =>
          editing?.kind === "rename" && editing.caseId === one.id ? (
            <InlineEdit
              key={one.id}
              initial={one.name}
              busy={busy}
              className={NAME_FIELD}
              placeholder="用例编号"
              onCommit={commit}
              onCancel={() => setEditing(null)}
            />
          ) : (
            <button
              key={one.id}
              type="button"
              onClick={() => onSelect(one.id)}
              onDoubleClick={() =>
                setEditing({ kind: "rename", caseId: one.id })
              }
              title="双击改名"
              className={
                one.id === selectedId
                  ? "shrink-0 cursor-pointer rounded-md bg-slate-800 px-3 py-1 font-mono text-xs text-white"
                  : "shrink-0 cursor-pointer rounded-md px-3 py-1 font-mono text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-800"
              }
            >
              {one.name}
            </button>
          ),
        )}

        {editing?.kind === "add" ? (
          <InlineEdit
            initial=""
            busy={busy}
            className={NAME_FIELD}
            placeholder="用例编号"
            onCommit={commit}
            onCancel={() => setEditing(null)}
          />
        ) : (
          <button
            type="button"
            onClick={() => setEditing({ kind: "add" })}
            title="添加用例"
            className="shrink-0 cursor-pointer rounded-md px-2.5 py-1 text-xs text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          >
            + 用例
          </button>
        )}
      </div>

      {error !== null && <p className="text-xs text-red-600">{error}</p>}

      {selected !== null && editing === null && (
        <div className="flex items-center gap-1 text-xs">
          <span className="mr-1 text-slate-400">
            第 {at + 1} / {cases.length} 个用例
          </span>
          {MOVES.map(({ to, glyph, title, stuck }) => (
            <button
              key={to}
              type="button"
              title={title}
              disabled={busy || stuck(at, cases.length)}
              onClick={() => void onMove(selected.id, to)}
              className={TOOL_BUTTON}
            >
              {glyph}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setEditing({ kind: "rename", caseId: selected.id })}
            className={TOOL_BUTTON}
          >
            重命名
          </button>
          <button
            type="button"
            onClick={() => void remove()}
            disabled={busy}
            className={`${TOOL_BUTTON} hover:text-red-600`}
          >
            删除
          </button>
        </div>
      )}
    </div>
  );
}
