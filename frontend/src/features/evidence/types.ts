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

/** Where a case is being sent. Four buttons, no dragging (design.md §6 F5). */
export type CaseMove = "up" | "down" | "top" | "bottom";
