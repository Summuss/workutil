/**
 * An evidence as the list sends it: no cases, only how many.
 *
 * The list is the way back into a workbook you started yesterday, not a
 * preview of it — see the backend's `EvidenceRead`.
 */
export interface Evidence {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  case_count: number;
}

/** One test case. `name` is the case number, and also the exported sheet name. */
export interface Case {
  id: number;
  name: string;
  order: number;
}

/** One evidence with its cases, in the order they will become sheets. */
export interface EvidenceDetail extends Evidence {
  cases: Case[];
}

/** Where a case or a block is being sent. Four buttons, no dragging (design.md §6 F5). */
export type Move = "up" | "down" | "top" | "bottom";

/** The three things a case is made of. A log is `text`, not a kind of its own. */
export type BlockKind = "text" | "image" | "table";

/**
 * One piece of a case: a paragraph, a screenshot, a query result.
 *
 * The pieces of a case stand side by side rather than 1→2→3 (ADR-0003) —
 * `label` is the optional small heading that says what a piece is, and most
 * blocks do without one.
 *
 * Each kind fills its own payload and leaves the others empty: `text` for a
 * paragraph, `image_url` for a screenshot. Switch on `kind`, never on which
 * field happens to be filled.
 */
export interface Block {
  id: number;
  kind: BlockKind;
  order: number;
  label: string | null;
  text: string;
  image_url: string | null;
}

/** One case with what is in it — a case at a time, not the whole workbook. */
export interface CaseDetail extends Case {
  blocks: Block[];
}
