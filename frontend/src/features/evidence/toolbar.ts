import type { ComponentType } from "react";

/** The small buttons that sit beside a case or a block. */
export const TOOL_BUTTON = "tool-btn";

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
  to: "top" | "bottom";
  stuck: (at: number, count: number) => boolean;
}[] = [
  { to: "top", stuck: (at) => at === 0 },
  { to: "bottom", stuck: (at, count) => at === count - 1 },
];

/** What one axis calls the moves. */
export type MoveLabels = Record<
  "top" | "bottom",
  { Icon: ComponentType<{ size?: number }>; title: string }
>;
