import { useState } from "react";
import { Link, useParams } from "react-router";

import { arrayMove } from "@dnd-kit/sortable";

import { InlineEdit } from "../../shared/InlineEdit";
import { useI18n } from "../../shared/i18n";
import { ArrowLeftIcon } from "../../shared/icons";
import { useEditRunner } from "../../shared/useEditRunner";
import { useLoad } from "../../shared/useLoad";
import {
  addCase,
  deleteCase,
  exportEvidenceUrl,
  getEvidence,
  moveCase,
  renameCase,
  renameEvidence,
} from "./api";
import { CaseBlocks } from "./CaseBlocks";
import { CaseTabs } from "./CaseTabs";
import type { Case, EvidenceDetail, Move } from "./types";

const TITLE_FIELD = "field-input min-w-0 flex-1";

/**
 * One evidence: its title, its cases, and the case you are working in.
 *
 * Which case is open is component state rather than part of the URL. Back and
 * forward step between the list and a workbook, which is the navigation spec
 * User Stories 25 asks for; making every tab click a history entry would turn
 * Back into "undo my last eight clicks" instead.
 */
export function EvidenceDetailPage() {
  const { t } = useI18n();
  const { evidenceId } = useParams();
  const id = Number(evidenceId);

  const {
    value: evidence,
    setValue: setEvidence,
    loading,
    error,
  } = useLoad<EvidenceDetail>(() => getEvidence(id), [id]);

  // One runner per thing being edited, so renaming the evidence and editing a
  // case each report where they happened and neither greys the other out.
  const titleEdit = useEditRunner(t("evidence.rename_failed"));
  const caseEdit = useEditRunner(t("common.action_failed"));

  // Which case the author last picked. The case actually shown is worked out
  // below, so a case that has been deleted — or one picked in a different
  // evidence — falls back to the first rather than showing nothing.
  const [pickedId, setPickedId] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState(false);

  const cases = evidence?.cases ?? [];
  const selectedId =
    cases.find((one) => one.id === pickedId)?.id ?? cases[0]?.id ?? null;

  function setCases(next: Case[]) {
    setEvidence((current) =>
      current === null
        ? current
        : { ...current, cases: next, case_count: next.length },
    );
  }

  function handleAdd(name: string): Promise<boolean> {
    return caseEdit.run(async () => {
      const created = await addCase(id, name);
      setCases([...cases, created]);
      setPickedId(created.id);
    });
  }

  function handleRename(caseId: number, name: string): Promise<boolean> {
    return caseEdit.run(async () => {
      const renamed = await renameCase(id, caseId, name);
      setCases(cases.map((one) => (one.id === caseId ? renamed : one)));
    });
  }

  async function handleDelete(caseId: number): Promise<void> {
    await caseEdit.run(async () => {
      await deleteCase(id, caseId);

      const wasAt = cases.findIndex((one) => one.id === caseId);
      const left = cases.filter((one) => one.id !== caseId);
      setCases(left);
      // Land on whatever took its place, so the content area is never blank
      // just because the case you were in is gone.
      setPickedId(left[Math.min(wasAt, left.length - 1)]?.id ?? null);
    });
  }

  async function handleReorderCase(caseId: number, targetIndex: number): Promise<void> {
    const oldIndex = cases.findIndex((c) => c.id === caseId);
    if (oldIndex === -1 || oldIndex === targetIndex) return;

    const prev = cases;
    const reorderedOptimistic = arrayMove(cases, oldIndex, targetIndex).map(
      (c, idx) => ({ ...c, order: idx }),
    );
    setCases(reorderedOptimistic);

    await caseEdit.run(async () => {
      try {
        setCases(await moveCase(id, caseId, targetIndex));
      } catch (cause) {
        setCases(prev);
        throw cause;
      }
    });
  }

  function handleMove(caseId: number, to: Move): Promise<void> {
    const targetIndex =
      typeof to === "number" ? to : to === "top" ? 0 : cases.length - 1;
    return handleReorderCase(caseId, targetIndex);
  }

  async function commitTitle(title: string): Promise<void> {
    if (evidence === null) {
      return;
    }
    if (title.trim() === evidence.title) {
      setEditingTitle(false);
      return;
    }

    const accepted = await titleEdit.run(async () => {
      const renamed = await renameEvidence(id, title);
      // Only what a rename actually changes: the cases are untouched, and the
      // response carries a count rather than them.
      setEvidence({
        ...evidence,
        title: renamed.title,
        updated_at: renamed.updated_at,
      });
    });
    if (accepted) {
      setEditingTitle(false);
    }
  }

  if (evidence === null) {
    return (
      <main className="mx-auto max-w-2xl px-8 py-9">
        <p className="text-center text-[13px]" style={{ color: "var(--text-faint)" }}>
          {loading ? t("common.loading") : (error ?? t("evidence.not_found"))}
        </p>
        <p className="mt-3 text-center text-xs">
          <Link to="/evidence" style={{ color: "var(--text-faint)" }}>
            {t("evidence.back_to_list_full")}
          </Link>
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-3.5 px-8 py-9">
      <div className="flex items-center gap-2.5">
        <Link
          to="/evidence"
          className="inline-flex shrink-0 items-center gap-1 text-xs"
          style={{ color: "var(--text-faint)" }}
        >
          <ArrowLeftIcon size={12} />
          {t("evidence.back_to_list_short")}
        </Link>
        {editingTitle ? (
          <InlineEdit
            initial={evidence.title}
            busy={titleEdit.busy}
            className={TITLE_FIELD}
            onCommit={commitTitle}
            onCancel={() => setEditingTitle(false)}
          />
        ) : (
          <button
            type="button"
            title={t("evidence.click_to_rename")}
            onClick={() => setEditingTitle(true)}
            className="min-w-0 flex-1 cursor-pointer truncate text-left text-base font-semibold"
          >
            {evidence.title}
          </button>
        )}
        <a
          href={exportEvidenceUrl(id)}
          download
          aria-disabled={cases.length === 0}
          tabIndex={cases.length === 0 ? -1 : undefined}
          onClick={(event) => {
            // pointer-events-none stops a click but not a keyboard Enter, and
            // tabIndex=-1 alone leaves a keyboard-then-mouse activation path
            // open — either would otherwise download the 422 refusal body as
            // an .xlsx file.
            if (cases.length === 0) {
              event.preventDefault();
            }
          }}
          className="btn-ghost shrink-0"
          style={cases.length === 0 ? { pointerEvents: "none", opacity: 0.4 } : undefined}
          title={cases.length === 0 ? t("evidence.export_no_cases") : t("evidence.export_excel")}
        >
          {t("evidence.export_excel")}
        </a>
      </div>

      {(error ?? titleEdit.error) !== null && (
        <p className="text-xs" style={{ color: "var(--danger)" }}>
          {error ?? titleEdit.error}
        </p>
      )}

      <CaseTabs
        cases={cases}
        selectedId={selectedId}
        busy={caseEdit.busy}
        error={caseEdit.error}
        onSelect={setPickedId}
        onAdd={handleAdd}
        onRename={handleRename}
        onDelete={handleDelete}
        onMove={handleMove}
        onReorder={handleReorderCase}
      />

      {selectedId === null ? (
        <div
          className="rounded-lg px-4 py-10 text-center text-xs"
          style={{ border: "1px dashed var(--border-strong)", color: "var(--text-faint)" }}
        >
          {t("evidence.no_cases_hint")}
        </div>
      ) : (
        // Keyed by the case, so switching tabs starts the content area over
        // rather than showing the previous case's blocks while the next load
        // is in flight.
        <CaseBlocks key={selectedId} evidenceId={id} caseId={selectedId} />
      )}
    </main>
  );
}
