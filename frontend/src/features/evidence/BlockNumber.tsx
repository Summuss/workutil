/**
 * Where a block stands in its case, counted from 1: `#3`.
 *
 * A reading of the position, not a field: it is never stored and never
 * exported, so inserting, deleting or dragging a block renumbers everything at
 * once. That is what keeps it from being the step number ADR-0003 removed,
 * which was typed in and went stale the moment a section was inserted.
 */
export function blockNumber(at: number): string {
  return `#${at + 1}`;
}

/** The number at the start of a card or an outline row, quiet beside the label. */
export function BlockNumber({ at, className = "" }: { at: number; className?: string }) {
  return (
    <span
      className={`shrink-0 text-[11px] tabular-nums select-none ${className}`}
      style={{ fontFamily: "var(--mono)", color: "var(--text-faint)" }}
    >
      {blockNumber(at)}
    </span>
  );
}
