import { useState } from "react";

import { InlineEdit } from "../../shared/InlineEdit";
import { useI18n } from "../../shared/i18n";
import { ChevronsLeftIcon, ChevronsRightIcon, ChevronLeftIcon, ChevronRightIcon, EditIcon, TrashIcon, PlusIcon } from "../../shared/icons";
import { MOVES, TOOL_BUTTON, type MoveLabels } from "./toolbar";
import type { Case, Move } from "./types";

interface CaseTabsProps {
  cases: Case[];
  selectedId: number | null;
  busy: boolean;
  error: string | null;
  onSelect: (caseId: number) => void;
  onAdd: (name: string) => Promise<boolean>;
  onRename: (caseId: number, name: string) => Promise<boolean>;
  onDelete: (caseId: number) => Promise<void>;
  onMove: (caseId: number, to: Move) => Promise<void>;
}

type Editing = { kind: "add" } | { kind: "rename"; caseId: number } | null;

const NAME_FIELD = "field-input w-28";

/**
 * The cases of one evidence, in the order they will become sheets.
 *
 * A tab bar rather than a list because a case is a place you work *inside*:
 * only one case's content is on screen at a time, and the strip is how you get
 * between them. Left and right here are the "上下移动" of design.md §6 F5 —
 * the tabs run horizontally, so the arrows do too.
 */
export function CaseTabs({
  cases,
  selectedId,
  busy,
  error,
  onSelect,
  onAdd,
  onRename,
  onDelete,
  onMove,
}: CaseTabsProps) {
  const { t } = useI18n();
  const [editing, setEditing] = useState<Editing>(null);

  const moveLabels: MoveLabels = {
    top: { Icon: ChevronsLeftIcon, title: t("evidence.move_case_top") },
    up: { Icon: ChevronLeftIcon, title: t("evidence.move_case_left") },
    down: { Icon: ChevronRightIcon, title: t("evidence.move_case_right") },
    bottom: { Icon: ChevronsRightIcon, title: t("evidence.move_case_bottom") },
  };

  const selected = cases.find((one) => one.id === selectedId) ?? null;
  const at = selected ? cases.indexOf(selected) : -1;

  // Closed only once the name was actually accepted, so a refused one stays in
  // the box with the reason underneath it.
  async function commit(name: string) {
    if (editing === null) {
      return;
    }
    const accepted =
      editing.kind === "add"
        ? await onAdd(name)
        : await onRename(editing.caseId, name);
    if (accepted) {
      setEditing(null);
    }
  }

  async function remove() {
    if (
      selected === null ||
      !window.confirm(
        t("evidence.delete_case_confirm", { name: selected.name }),
      )
    ) {
      return;
    }
    await onDelete(selected.id);
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2" style={{ borderBottom: "1px solid var(--border)" }}>
        {cases.map((one) =>
          editing?.kind === "rename" && editing.caseId === one.id ? (
            <InlineEdit
              key={one.id}
              initial={one.name}
              busy={busy}
              className={NAME_FIELD}
              placeholder={t("evidence.case_name_placeholder")}
              onCommit={commit}
              onCancel={() => setEditing(null)}
            />
          ) : (
            <button
              key={one.id}
              type="button"
              onClick={() => onSelect(one.id)}
              onDoubleClick={() =>
                setEditing({ kind: "rename", caseId: one.id })
              }
              title={t("evidence.double_click_rename")}
              className="shrink-0 cursor-pointer rounded-md px-3 py-1.5 text-xs transition-colors"
              style={
                one.id === selectedId
                  ? { fontFamily: "var(--mono)", background: "var(--accent)", color: "white" }
                  : { fontFamily: "var(--mono)", color: "var(--text-muted)" }
              }
            >
              {one.name}
            </button>
          ),
        )}

        {editing?.kind === "add" ? (
          <InlineEdit
            initial=""
            busy={busy}
            className={NAME_FIELD}
            placeholder={t("evidence.case_name_placeholder")}
            onCommit={commit}
            onCancel={() => setEditing(null)}
          />
        ) : (
          <button
            type="button"
            onClick={() => setEditing({ kind: "add" })}
            title={t("evidence.add_case_title")}
            className="icon-btn shrink-0"
            style={{ border: "1px dashed var(--border-strong)", borderRadius: "6px" }}
          >
            <PlusIcon />
          </button>
        )}
      </div>

      {error !== null && (
        <p className="text-xs" style={{ color: "var(--danger)" }}>
          {error}
        </p>
      )}

      {selected !== null && editing === null && (
        <div className="flex items-center gap-1 text-xs">
          <span className="mr-1" style={{ color: "var(--text-faint)" }}>
            {t("evidence.case_position", {
              current: at + 1,
              total: cases.length,
            })}
          </span>
          {MOVES.map(({ to, stuck }) => (
            <button
              key={to}
              type="button"
              title={moveLabels[to].title}
              disabled={busy || stuck(at, cases.length)}
              onClick={() => void onMove(selected.id, to)}
              className={TOOL_BUTTON}
            >
              {(() => {
                const Icon = moveLabels[to].Icon;
                return <Icon size={12} />;
              })()}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setEditing({ kind: "rename", caseId: selected.id })}
            className={TOOL_BUTTON}
            title={t("evidence.rename_case")}
          >
            <EditIcon size={12} />
          </button>
          <button
            type="button"
            onClick={() => void remove()}
            disabled={busy}
            className={`${TOOL_BUTTON} icon-btn-danger`}
            title={t("common.delete")}
          >
            <TrashIcon size={12} />
          </button>
        </div>
      )}
    </div>
  );
}
