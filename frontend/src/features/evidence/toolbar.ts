import type { Move } from "./types";

/** The small buttons that sit beside a case or a block. */
export const TOOL_BUTTON =
  "cursor-pointer rounded px-1.5 py-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 disabled:cursor-default disabled:opacity-40";

/**
 * The four ordering buttons, each with the position that leaves it nowhere to
 * go — no dragging, by decision (design.md §6 F5).
 *
 * Cases and blocks are reordered by the same four buttons in two directions:
 * the tab bar runs left to right, blocks stack downwards. Only the arrows and
 * the words for them differ, so only those are left to the caller. Greying a
 * stuck button out is presentation — the backend treats a move past either end
 * as a no-op regardless.
 */
export const MOVES: {
  to: Move;
  stuck: (at: number, count: number) => boolean;
}[] = [
  { to: "top", stuck: (at) => at === 0 },
  { to: "up", stuck: (at) => at === 0 },
  { to: "down", stuck: (at, count) => at === count - 1 },
  { to: "bottom", stuck: (at, count) => at === count - 1 },
];

/** What one axis calls the four moves. */
export type MoveLabels = Record<Move, { glyph: string; title: string }>;
