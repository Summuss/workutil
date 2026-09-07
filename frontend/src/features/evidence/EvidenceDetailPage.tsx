import { useState } from "react";
import { Link, useParams } from "react-router";

import { messageOf } from "../../shared/api";
import { InlineEdit } from "../../shared/InlineEdit";
import { useLoad } from "../../shared/useLoad";
import {
  addCase,
  deleteCase,
  getEvidence,
  moveCase,
  renameCase,
  renameEvidence,
} from "./api";
import { CaseTabs } from "./CaseTabs";
import type { Case, CaseMove, EvidenceDetail } from "./types";

const TITLE_FIELD =
  "min-w-0 flex-1 rounded-md border border-slate-400 bg-white px-2 py-1 text-base text-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-300";

/**
 * One evidence: its title, its cases, and the case you are working in.
 *
 * Which case is open is component state rather than part of the URL. Back and
 * forward step between the list and a workbook, which is the navigation spec
 * User Stories 25 asks for; making every tab click a history entry would turn
 * Back into "undo my last eight clicks" instead.
 */
export function EvidenceDetailPage() {
  const { evidenceId } = useParams();
  const id = Number(evidenceId);

  const {
    value: evidence,
    setValue: setEvidence,
    loading,
    error,
    setError,
  } = useLoad<EvidenceDetail>(() => getEvidence(id), [id]);

  // Which case the author last picked. The case actually shown is worked out
  // below, so a case that has been deleted — or one picked in a different
  // evidence — falls back to the first rather than showing nothing.
  const [pickedId, setPickedId] = useState<number | null>(null);
  const [editingTitle, setEditingTitle] = useState(false);
  const [busy, setBusy] = useState(false);
  const [caseError, setCaseError] = useState<string | null>(null);

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

  /**
   * Run one case edit, keeping the server's reason next to the tab bar.
   *
   * Answers whether it was accepted, so a rejected name can stay on screen
   * with what was typed still in it — which is the whole point of refusing an
   * illegal sheet name here rather than at export.
   */
  async function runCaseEdit(change: () => Promise<void>): Promise<boolean> {
    setBusy(true);
    setCaseError(null);
    try {
      await change();
      return true;
    } catch (cause) {
      setCaseError(messageOf(cause, "操作失败"));
      return false;
    } finally {
      setBusy(false);
    }
  }

  function handleAdd(name: string): Promise<boolean> {
    return runCaseEdit(async () => {
      const created = await addCase(id, name);
      setCases([...cases, created]);
      setPickedId(created.id);
    });
  }

  function handleRename(caseId: number, name: string): Promise<boolean> {
    return runCaseEdit(async () => {
      const renamed = await renameCase(id, caseId, name);
      setCases(cases.map((one) => (one.id === caseId ? renamed : one)));
    });
  }

  async function handleDelete(caseId: number): Promise<void> {
    await runCaseEdit(async () => {
      await deleteCase(id, caseId);

      const wasAt = cases.findIndex((one) => one.id === caseId);
      const left = cases.filter((one) => one.id !== caseId);
      setCases(left);
      // Land on whatever took its place, so the content area is never blank
      // just because the case you were in is gone.
      setPickedId(left[Math.min(wasAt, left.length - 1)]?.id ?? null);
    });
  }

  async function handleMove(caseId: number, to: CaseMove): Promise<void> {
    await runCaseEdit(async () => {
      setCases(await moveCase(id, caseId, to));
    });
  }

  async function commitTitle(title: string): Promise<void> {
    if (evidence === null) {
      return;
    }
    if (title.trim() === evidence.title) {
      setEditingTitle(false);
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const renamed = await renameEvidence(id, title);
      // Only what a rename actually changes: the cases are untouched, and the
      // response carries a count rather than them.
      setEvidence({
        ...evidence,
        title: renamed.title,
        updated_at: renamed.updated_at,
      });
      setEditingTitle(false);
    } catch (cause) {
      setError(messageOf(cause, "改名失败"));
    } finally {
      setBusy(false);
    }
  }

  if (evidence === null) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-8">
        <p className="text-center text-sm text-slate-400">
          {loading ? "载入中…" : (error ?? "没有这份 Evidence。")}
        </p>
        <p className="mt-3 text-center text-xs">
          <Link to="/evidence" className="text-slate-400 hover:text-slate-700">
            ← 回到列表
          </Link>
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-6">
      <div className="flex items-center gap-2">
        <Link
          to="/evidence"
          className="shrink-0 text-xs text-slate-400 hover:text-slate-700"
        >
          ← 列表
        </Link>
        {editingTitle ? (
          <InlineEdit
            initial={evidence.title}
            busy={busy}
            className={TITLE_FIELD}
            onCommit={commitTitle}
            onCancel={() => setEditingTitle(false)}
          />
        ) : (
          <button
            type="button"
            title="点击改名"
            onClick={() => setEditingTitle(true)}
            className="min-w-0 flex-1 cursor-pointer truncate text-left text-base font-semibold text-slate-900 hover:text-slate-600"
          >
            {evidence.title}
          </button>
        )}
      </div>

      {error !== null && <p className="text-xs text-red-600">{error}</p>}

      <CaseTabs
        cases={cases}
        selectedId={selectedId}
        busy={busy}
        error={caseError}
        onSelect={setPickedId}
        onAdd={handleAdd}
        onRename={handleRename}
        onDelete={handleDelete}
        onMove={handleMove}
      />

      {/* The content area. Text, image and table blocks arrive in tickets
          04–06; until then a case is a name and a place for them to go. */}
      <div className="rounded-lg border border-dashed border-slate-200 px-4 py-10 text-center text-xs text-slate-400">
        {cases.length === 0
          ? "还没有用例。上面的「+ 用例」填个编号,比如 1 或 2~5。"
          : "这个用例还是空的。文字、图片、表格的录入在后续 ticket 里。"}
      </div>
    </main>
  );
}
