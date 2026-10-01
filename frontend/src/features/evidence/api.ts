import { del, get, patch, post, put } from "../../shared/api";
import type { IncomingImage } from "../../shared/images";
import type {
  Block,
  Case,
  CaseDetail,
  DuplicateCaseResponse,
  Evidence,
  EvidenceDetail,
  Move,
} from "./types";
import type { Box } from "../../shared/BoxOverlay";

export function listEvidence(): Promise<Evidence[]> {
  return get<Evidence[]>("/evidence");
}

export function getEvidence(id: number): Promise<EvidenceDetail> {
  return get<EvidenceDetail>(`/evidence/${id}`);
}

export function createEvidence(title: string): Promise<Evidence> {
  return post<Evidence>("/evidence", { title });
}

export function renameEvidence(id: number, title: string): Promise<Evidence> {
  return patch<Evidence>(`/evidence/${id}`, { title });
}

export function deleteEvidence(id: number): Promise<void> {
  return del(`/evidence/${id}`);
}

export function exportEvidenceUrl(id: number): string {
  return `/api/evidence/${id}/export`;
}

export function addCase(evidenceId: number, name: string): Promise<Case> {
  return post<Case>(`/evidence/${evidenceId}/cases`, { name });
}

export function renameCase(
  evidenceId: number,
  caseId: number,
  name: string,
): Promise<Case> {
  return patch<Case>(`/evidence/${evidenceId}/cases/${caseId}`, { name });
}

export function deleteCase(evidenceId: number, caseId: number): Promise<void> {
  return del(`/evidence/${evidenceId}/cases/${caseId}`);
}

export function duplicateCase(
  evidenceId: number,
  caseId: number,
): Promise<DuplicateCaseResponse> {
  return post<DuplicateCaseResponse>(
    `/evidence/${evidenceId}/cases/${caseId}/duplicate`,
  );
}

/** Moves answer with the whole new order — a move that hit an end changed nothing. */
export function moveCase(
  evidenceId: number,
  caseId: number,
  to: Move,
): Promise<Case[]> {
  return post<Case[]>(`/evidence/${evidenceId}/cases/${caseId}/move`, { to });
}

function blocksAt(evidenceId: number, caseId: number): string {
  return `/evidence/${evidenceId}/cases/${caseId}/blocks`;
}

/** One case and its blocks. Loaded a case at a time: only one is on screen. */
export function getCase(
  evidenceId: number,
  caseId: number,
): Promise<CaseDetail> {
  return get<CaseDetail>(`/evidence/${evidenceId}/cases/${caseId}`);
}

export function addTextBlock(
  evidenceId: number,
  caseId: number,
  text: string,
): Promise<Block> {
  return post<Block>(blocksAt(evidenceId, caseId), { kind: "text", text });
}

/**
 * Whatever was on the clipboard, for the server to make sense of.
 *
 * `kind: "paste"` is not one of the three kinds — it is the absence of one.
 * Cutting a clipboard into cells is what decides between a query result and a
 * paragraph, and that parsing lives on the server (design.md §6 F5), so this
 * says what it has and reads the kind off the block that comes back.
 *
 * `html` is the compatibility flavour, sent when the copy came from a web page
 * or Excel. The tool this is for puts only `text/plain` on the clipboard.
 */
export function addPastedBlock(
  evidenceId: number,
  caseId: number,
  text: string,
  html: string | null,
): Promise<Block> {
  return post<Block>(blocksAt(evidenceId, caseId), {
    kind: "paste",
    text,
    html,
  });
}

/** Takes back a table the server guessed wrong: it was a log all along. */
export function turnBlockIntoText(
  evidenceId: number,
  caseId: number,
  blockId: number,
): Promise<Block> {
  return post<Block>(`${blocksAt(evidenceId, caseId)}/${blockId}/as-text`);
}

/** Cuts a text block's current text into cells, turning it into a table. */
export function turnBlockIntoTable(
  evidenceId: number,
  caseId: number,
  blockId: number,
): Promise<Block> {
  return post<Block>(`${blocksAt(evidenceId, caseId)}/${blockId}/as-table`);
}

/** Says whether a table's first row is column names — stated, not toggled. */
export function setTableHeader(
  evidenceId: number,
  caseId: number,
  blockId: number,
  hasHeader: boolean,
): Promise<Block> {
  return put<Block>(`${blocksAt(evidenceId, caseId)}/${blockId}/header`, {
    has_header: hasHeader,
  });
}

/** Says whether a text block's lines are split row-by-row on export. */
export function setTextBlockSplitLines(
  evidenceId: number,
  caseId: number,
  blockId: number,
  splitLines: boolean,
): Promise<Block> {
  return put<Block>(`${blocksAt(evidenceId, caseId)}/${blockId}/split-lines`, {
    split_lines: splitLines,
  });
}

/** Replaces every red box on an image block with `boxes`. */
export function setBlockBoxes(
  evidenceId: number,
  caseId: number,
  blockId: number,
  boxes: Box[],
): Promise<Block> {
  return put<Block>(`${blocksAt(evidenceId, caseId)}/${blockId}/boxes`, {
    boxes,
  });
}

export function setTableCell(
  evidenceId: number,
  caseId: number,
  blockId: number,
  row: number,
  column: number,
  value: string,
): Promise<Block> {
  return put<Block>(
    `${blocksAt(evidenceId, caseId)}/${blockId}/cells/${row}/${column}`,
    { value },
  );
}

/**
 * Takes a row or a column out. There is deliberately no function that puts one
 * in, here or on the server, which is where the reason is written down.
 *
 * Both answer with the whole table, the way a move answers with the whole order.
 */
export function deleteTableRow(
  evidenceId: number,
  caseId: number,
  blockId: number,
  row: number,
): Promise<Block> {
  return del<Block>(`${blocksAt(evidenceId, caseId)}/${blockId}/rows/${row}`);
}

export function deleteTableColumn(
  evidenceId: number,
  caseId: number,
  blockId: number,
  column: number,
): Promise<Block> {
  return del<Block>(
    `${blocksAt(evidenceId, caseId)}/${blockId}/columns/${column}`,
  );
}

/**
 * One pasted screenshot, one block.
 *
 * Posted the moment it is pasted rather than held for a save: an image block
 * *is* the screenshot, so there is nothing else for it to wait for. A paste of
 * three sends three of these in turn, which is what puts them in the case in
 * the order they were pasted.
 */
export function addImageBlock(
  evidenceId: number,
  caseId: number,
  image: IncomingImage,
): Promise<Block> {
  return post<Block>(blocksAt(evidenceId, caseId), { kind: "image", image });
}

export function editBlockText(
  evidenceId: number,
  caseId: number,
  blockId: number,
  text: string,
): Promise<Block> {
  return patch<Block>(`${blocksAt(evidenceId, caseId)}/${blockId}`, { text });
}

/** Sets the small heading, or clears it — a blank one is no heading. */
export function setBlockLabel(
  evidenceId: number,
  caseId: number,
  blockId: number,
  label: string,
): Promise<Block> {
  return put<Block>(`${blocksAt(evidenceId, caseId)}/${blockId}/label`, {
    label,
  });
}

/** Sets the note, or clears it — a blank one is no note. Never exported. */
export function setBlockNote(
  evidenceId: number,
  caseId: number,
  blockId: number,
  note: string,
): Promise<Block> {
  return put<Block>(`${blocksAt(evidenceId, caseId)}/${blockId}/note`, {
    note,
  });
}

export function deleteBlock(
  evidenceId: number,
  caseId: number,
  blockId: number,
): Promise<void> {
  return del(`${blocksAt(evidenceId, caseId)}/${blockId}`);
}

export function moveBlock(
  evidenceId: number,
  caseId: number,
  blockId: number,
  to: Move,
): Promise<Block[]> {
  return post<Block[]>(`${blocksAt(evidenceId, caseId)}/${blockId}/move`, {
    to,
  });
}
