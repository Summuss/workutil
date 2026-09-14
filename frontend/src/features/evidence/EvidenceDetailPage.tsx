import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { arrayMove } from "@dnd-kit/sortable";

import { messageOf } from "../../shared/api";
import { InlineEdit } from "../../shared/InlineEdit";
import { useI18n } from "../../shared/i18n";
import { ArrowLeftIcon, SidebarIcon } from "../../shared/icons";
import { PageLayout } from "../../shared/PageLayout";
import { useEditRunner } from "../../shared/useEditRunner";
import { useLoad } from "../../shared/useLoad";
import {
  addCase,
  deleteCase,
  duplicateCase,
  exportEvidenceUrl,
  getEvidence,
  moveCase,
  renameCase,
  renameEvidence,
} from "./api";
import { CaseBlocks } from "./CaseBlocks";
import { CaseTabs } from "./CaseTabs";
import { EvidenceMemoPanel } from "./EvidenceMemoPanel";
import type { Case, EvidenceDetail, Move } from "./types";

const TITLE_FIELD = "field-input min-w-0 flex-1";
const MEMO_PANEL_STORAGE_KEY = "workutil_evidence_memo_panel_open";

function loadMemoPanelOpen(): boolean {
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      return localStorage.getItem(MEMO_PANEL_STORAGE_KEY) === "true";
    } catch {
      // localStorage may be unavailable or blocked
    }
  }
  return false;
}

function saveMemoPanelOpen(open: boolean): void {
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      localStorage.setItem(MEMO_PANEL_STORAGE_KEY, open ? "true" : "false");
    } catch {
      // ignore storage failures
    }
  }
}

/**
 * One evidence: its title, its cases, and the case you are working in.
 *
 * Which case is open is reflected in the URL (/evidence/:evidenceId/cases/:caseId)
 * but tab switches use replace rather than push. Back and forward step between
 * the list and an evidence workbook, which is the navigation spec User
 * Stories 25 asks for; making every tab click a history entry would turn Back
 * into "undo my last eight clicks" instead.
 */
export function EvidenceDetailPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { evidenceId, caseId } = useParams();
  const id = Number(evidenceId);
  const urlCaseId = caseId !== undefined ? Number(caseId) : null;

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

  const [editingTitle, setEditingTitle] = useState(false);
  const [memoPanelOpen, setMemoPanelOpen] = useState(loadMemoPanelOpen);

  function toggleMemoPanel() {
    setMemoPanelOpen((prev) => {
      const next = !prev;
      saveMemoPanelOpen(next);
      return next;
    });
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      // Intentionally checks ONLY event.ctrlKey (and strictly not event.metaKey)
      // because on macOS Cmd+M is the system-wide shortcut to minimize the window.
      if (event.ctrlKey && !event.metaKey && (event.key === "m" || event.key === "M")) {
        event.preventDefault();
        toggleMemoPanel();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  const cases = evidence?.cases ?? [];
  const selectedId =
    cases.find((one) => one.id === urlCaseId)?.id ?? cases[0]?.id ?? null;

  // Keep URL in sync: if visiting without a caseId or with a stale/invalid
  // caseId, replace with the canonical case path once evidence loads.
  useEffect(() => {
    if (evidence === null) {
      return;
    }
    if (selectedId !== null) {
      if (urlCaseId !== selectedId) {
        navigate(`/evidence/${id}/cases/${selectedId}`, { replace: true });
      }
    } else if (urlCaseId !== null) {
      navigate(`/evidence/${id}`, { replace: true });
    }
  }, [evidence, id, selectedId, urlCaseId, navigate]);

  function setCases(next: Case[]) {
    setEvidence((current) =>
      current === null
        ? current
        : { ...current, cases: next, case_count: next.length },
    );
  }

  function handleSelectCase(targetCaseId: number) {
    navigate(`/evidence/${id}/cases/${targetCaseId}`, { replace: true });
  }

  function handleAdd(name: string): Promise<boolean> {
    return caseEdit.run(async () => {
      const created = await addCase(id, name);
      setCases([...cases, created]);
      navigate(`/evidence/${id}/cases/${created.id}`, { replace: true });
    });
  }

  function handleRename(targetCaseId: number, name: string): Promise<boolean> {
    return caseEdit.run(async () => {
      const renamed = await renameCase(id, targetCaseId, name);
      setCases(cases.map((one) => (one.id === targetCaseId ? renamed : one)));
    });
  }

  async function handleDelete(targetCaseId: number): Promise<void> {
    await caseEdit.run(async () => {
      await deleteCase(id, targetCaseId);

      const wasAt = cases.findIndex((one) => one.id === targetCaseId);
      const left = cases.filter((one) => one.id !== targetCaseId);
      setCases(left);
      // Land on whatever took its place, so the content area is never blank
      // just because the case you were in is gone.
      const nextId = left[Math.min(wasAt, left.length - 1)]?.id ?? null;
      if (nextId !== null) {
        navigate(`/evidence/${id}/cases/${nextId}`, { replace: true });
      } else {
        navigate(`/evidence/${id}`, { replace: true });
      }
    });
  }

  async function handleDuplicate(targetCaseId: number): Promise<number | null> {
    let newCaseId: number | null = null;
    await caseEdit.run(async () => {
      try {
        const res = await duplicateCase(id, targetCaseId);
        setCases(res.cases);
        newCaseId = res.new_case_id;
        navigate(`/evidence/${id}/cases/${res.new_case_id}`, { replace: true });
      } catch (cause) {
        throw new Error(messageOf(cause, t("evidence.duplicate_case_failed")));
      }
    });
    return newCaseId;
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
      <PageLayout>
        <p className="text-center text-[13px]" style={{ color: "var(--text-faint)" }}>
          {loading ? t("common.loading") : (error ?? t("evidence.not_found"))}
        </p>
        <p className="mt-3 text-center text-xs">
          {/* The arrow is drawn here, never carried inside the copy: a language
              pack that ships its own "←" gives you two of them the day the
              button grows an icon. */}
          <Link
            to="/evidence"
            className="inline-flex items-center gap-1"
            style={{ color: "var(--text-faint)" }}
          >
            <ArrowLeftIcon size={12} />
            {t("evidence.back_to_list_full")}
          </Link>
        </p>
      </PageLayout>
    );
  }

  return (
    <div className="flex flex-1 min-h-0 flex-row overflow-hidden">
      <PageLayout
        className="min-w-0"
        scrollable={selectedId === null}
        fixedHeader={
          <>
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
              <button
                type="button"
                onClick={toggleMemoPanel}
                className="btn-ghost shrink-0 inline-flex items-center gap-1.5"
                style={memoPanelOpen ? { color: "var(--accent)" } : undefined}
                title={t("evidence.toggle_memo_panel")}
              >
                <SidebarIcon size={13} />
                <span>{t("evidence.memo_panel_button")}</span>
              </button>
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
              onSelect={handleSelectCase}
              onAdd={handleAdd}
              onRename={handleRename}
              onDelete={handleDelete}
              onDuplicate={handleDuplicate}
              onMove={handleMove}
              onReorder={handleReorderCase}
            />
          </>
        }
      >
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
      </PageLayout>

      {memoPanelOpen && (
        <EvidenceMemoPanel
          onClose={() => {
            saveMemoPanelOpen(false);
            setMemoPanelOpen(false);
          }}
        />
      )}
    </div>
  );
}
