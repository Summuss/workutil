import { del, get, patch, post } from "../../shared/api";
import type { Case, CaseMove, Evidence, EvidenceDetail } from "./types";

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
  to: CaseMove,
): Promise<Case[]> {
  return post<Case[]>(`/evidence/${evidenceId}/cases/${caseId}/move`, { to });
}
