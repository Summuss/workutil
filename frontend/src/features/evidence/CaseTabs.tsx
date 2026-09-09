import { useState } from "react";

import { horizontalListSortingStrategy } from "@dnd-kit/sortable";

import { InlineEdit } from "../../shared/InlineEdit";
import { useI18n } from "../../shared/i18n";
import {
  ChevronsLeftIcon,
  ChevronsRightIcon,
  CopyIcon,
  EditIcon,
  PlusIcon,
  TrashIcon,
} from "../../shared/icons";
import { DragHandle, SortableList, useSortableItem } from "../../shared/sortable";
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
  onDuplicate: (caseId: number) => Promise<number | null>;
  onMove: (caseId: number, to: Move) => Promise<void>;
  onReorder?: (caseId: number, newIndex: number) => void | Promise<void>;
}

type Editing = { kind: "add" } | { kind: "rename"; caseId: number } | null;

const NAME_FIELD = "field-input w-28";

interface CaseTabItemProps {
  one: Case;
  selectedId: number | null;
  canReorder: boolean;
  busy: boolean;
  onSelect: (id: number) => void;
  onDoubleClick: () => void;
}

function CaseTabItem({
  one,
  selectedId,
  canReorder,
  busy,
  onSelect,
  onDoubleClick,
}: CaseTabItemProps) {
  const { t } = useI18n();
  const { ref, style, handleProps } = useSortableItem(one.id, !canReorder);
  const isSelected = one.id === selectedId;

  return (
    <div
      ref={ref}
      style={{
        ...style,
        background: isSelected ? "var(--accent)" : "transparent",
        border: isSelected ? "1px solid var(--accent)" : "1px solid var(--border)",
        borderRadius: "6px",
      }}
      className="group flex shrink-0 items-center transition-colors"
    >
      {canReorder && (
        <DragHandle
          title={t("common.drag_reorder")}
          disabled={busy}
          size={11}
          className="tool-btn cursor-grab active:cursor-grabbing px-1 opacity-40 group-focus-within:opacity-100 group-hover:opacity-100"
          style={{ color: isSelected ? "white" : undefined }}
          {...handleProps}
        />
      )}
      <button
        type="button"
        onClick={() => onSelect(one.id)}
        onDoubleClick={onDoubleClick}
        title={t("evidence.double_click_rename")}
        className="cursor-pointer px-2.5 py-1 text-xs"
        style={{
          fontFamily: "var(--mono)",
          color: isSelected ? "white" : "var(--text-muted)",
        }}
      >
        {one.name}
      </button>
    </div>
  );
}

/**
 * The cases of one evidence, in the order they will become sheets.
 *
 * A tab bar rather than a list because a case is a place you work *inside*:
 * only one case's content is on screen at a time, and the strip is how you get
 * between them.
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
  onDuplicate,
  onMove,
  onReorder,
}: CaseTabsProps) {
  const { t } = useI18n();
  const [editing, setEditing] = useState<Editing>(null);

  const moveLabels: MoveLabels = {
    top: { Icon: ChevronsLeftIcon, title: t("evidence.move_case_top") },
    bottom: { Icon: ChevronsRightIcon, title: t("evidence.move_case_bottom") },
  };

  const selected = cases.find((one) => one.id === selectedId) ?? null;
  const at = selected ? cases.indexOf(selected) : -1;
  const canReorder = cases.length > 1;

  async function duplicate() {
    if (selected === null) {
      return;
    }
    const newCaseId = await onDuplicate(selected.id);
    if (newCaseId !== null) {
      setEditing({ kind: "rename", caseId: newCaseId });
    }
  }

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
      <SortableList
        items={cases}
        strategy={horizontalListSortingStrategy}
        onReorder={(id, newIndex) => onReorder?.(Number(id), newIndex)}
        className="flex items-center gap-1.5 overflow-x-auto pb-2"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
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
            <CaseTabItem
              key={one.id}
              one={one}
              selectedId={selectedId}
              canReorder={canReorder}
              busy={busy}
              onSelect={onSelect}
              onDoubleClick={() =>
                setEditing({ kind: "rename", caseId: one.id })
              }
            />
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
      </SortableList>

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
            onClick={() => void duplicate()}
            disabled={busy}
            className={TOOL_BUTTON}
            title={t("evidence.duplicate_case")}
          >
            <CopyIcon size={12} />
          </button>
          <button
            type="button"
            onClick={() => setEditing({ kind: "rename", caseId: selected.id })}
            disabled={busy}
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
