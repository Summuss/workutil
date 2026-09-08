import { del, get, patch, post, put } from "../../shared/api";
import type { IncomingImage } from "../../shared/images";
import type {
  Block,
  Case,
  CaseDetail,
  Evidence,
  EvidenceDetail,
  Move,
} from "./types";

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
