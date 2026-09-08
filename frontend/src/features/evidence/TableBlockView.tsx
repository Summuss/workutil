import { useState } from "react";

import type { Block } from "./types";

interface TableBlockViewProps {
  block: Block;
  busy: boolean;
  editing: boolean;
  onCell: (row: number, column: number, value: string) => Promise<boolean>;
  onDeleteRow: (row: number) => Promise<void>;
  onDeleteColumn: (column: number) => Promise<void>;
}

const CELL = "border border-slate-200 px-2 py-1 align-top";
const HEADER_CELL = `${CELL} bg-[#87e7ad] font-semibold text-slate-900`;
const CUT_BUTTON =
  "cursor-pointer rounded px-1 text-slate-300 hover:bg-red-50 hover:text-red-600 disabled:cursor-default disabled:opacity-40";

/**
 * A query result with its rows and columns intact — the whole point of the kind.
 *
 * Reading and editing are two modes rather than one, the same call `BlockCard`
 * makes for text: cells hold values you copy out of, and click-to-edit throws
 * away the selection you were dragging. In edit mode every cell is a field and
 * the crosses that take a row or a column out appear beside them.
 *
 * There is no way to add a row or a column, here or anywhere else; the reason
 * is on the server, beside the endpoints that refuse to grow one.
 *
 * The header row is drawn from `has_header`, which is a flag and not a
 * different row — turning it off keeps every value, it only stops the first
 * row being drawn as column names.
 */
export function TableBlockView({
  block,
  busy,
  editing,
  onCell,
  onDeleteRow,
  onDeleteColumn,
}: TableBlockViewProps) {
  const columns = block.rows[0]?.length ?? 0;

  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-xs text-slate-800">
        {editing && (
          <thead>
            <tr>
              {/* Sits above the columns it cuts, and over the row buttons'
                  own column so the two never share a cell. */}
              <th className="w-6" />
              {Array.from({ length: columns }, (_, column) => (
                <th key={column} className="px-1 pb-1 font-normal">
                  <button
                    type="button"
                    title="删掉这一列"
                    disabled={busy}
                    onClick={() => void onDeleteColumn(column)}
                    className={CUT_BUTTON}
                  >
                    ✕
                  </button>
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {block.rows.map((cells, row) => (
            <tr key={row}>
              {editing && (
                <td className="pr-1">
                  <button
                    type="button"
                    title="删掉这一行"
                    disabled={busy}
                    onClick={() => void onDeleteRow(row)}
                    className={CUT_BUTTON}
                  >
                    ✕
                  </button>
                </td>
              )}
              {cells.map((value, column) => (
                <TableCell
                  key={column}
                  value={value}
                  header={block.has_header && row === 0}
                  busy={busy}
                  editing={editing}
                  onCommit={(next) => onCell(row, column, next)}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface TableCellProps {
  value: string;
  header: boolean;
  busy: boolean;
  editing: boolean;
  onCommit: (value: string) => Promise<boolean>;
}

/**
 * One cell: a value to read, or a field to change it in.
 *
 * Sent on blur as well as on Enter, because editing a table is several cells in
 * a row and reaching for Enter between each is not how a grid is filled in. A
 * value that has not changed is not sent at all, so tabbing across a row that
 * needed one change is one request and not five.
 *
 * A cell holding a newline keeps it: `whitespace-pre-wrap` shows the value the
 * way the database had it, which is the only thing an evidence is for.
 */
function TableCell({ value, header, busy, editing, onCommit }: TableCellProps) {
  const [draft, setDraft] = useState(value);
  const [shown, setShown] = useState(value);

  // Cells are keyed by where they are, not by what they hold, so deleting a row
  // slides every value below it into a component that is already on screen. A
  // draft belongs to the value it was started from: when the value underneath
  // changes, the draft starts again from the new one.
  if (shown !== value) {
    setShown(value);
    setDraft(value);
  }

  if (!editing) {
    return (
      <td className={`${header ? HEADER_CELL : CELL} whitespace-pre-wrap`}>
        {value}
      </td>
    );
  }

  async function commit() {
    if (draft !== value && !(await onCommit(draft))) {
      // Refused: the table on screen still says what the server does, so the
      // field goes back to it rather than keeping a value that was not saved.
      setDraft(value);
    }
  }

  return (
    <td className={header ? HEADER_CELL : CELL}>
      <input
        type="text"
        value={draft}
        disabled={busy}
        onChange={(event) => setDraft(event.target.value)}
        onBlur={() => void commit()}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            event.currentTarget.blur();
          }
          if (event.key === "Escape") {
            event.preventDefault();
            setDraft(value);
          }
        }}
        className="w-full min-w-24 bg-transparent font-mono text-xs outline-none focus:bg-white"
      />
    </td>
  );
}
