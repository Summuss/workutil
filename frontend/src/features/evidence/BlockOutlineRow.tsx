import { useState } from "react";

import { useI18n } from "../../shared/i18n";
import {
  ChevronsDownIcon,
  ChevronsUpIcon,
  ImageIcon,
  PlusIcon,
  TrashIcon,
} from "../../shared/icons";
import { InlineEdit } from "../../shared/InlineEdit";
import { DragHandle, useSortableItem } from "../../shared/sortable";
import { forgetDraft } from "../../shared/useDraft";
import { MOVES, TOOL_BUTTON, type MoveLabels } from "./toolbar";
import type { Block, Move } from "./types";

interface BlockOutlineRowProps {
  block: Block;
  at: number;
  count: number;
  busy: boolean;
  onLabel: (label: string) => Promise<boolean>;
  onMove: (to: Move) => Promise<void>;
  onDelete: () => Promise<void>;
  onJump: (blockId: number) => void;
  onImageError?: () => void;
}

function getFirstLine(text: string): string {
  const line = text.split(/\r?\n/).find((l) => l.trim().length > 0) ?? text;
  return line;
}

/**
 * One block in outline mode: a fixed-height row for scanning and reordering.
 *
 * Content editing and formatting controls are omitted deliberately: those
 * are done while looking at the content, which a row does not show.
 * Clicking the row returns to normal view and scrolls to this block.
 */
export function BlockOutlineRow({
  block,
  at,
  count,
  busy,
  onLabel,
  onMove,
  onDelete,
  onJump,
  onImageError,
}: BlockOutlineRowProps) {
  const { t } = useI18n();
  const [editingLabel, setEditingLabel] = useState(false);
  const [imageError, setImageError] = useState(false);

  const canReorder = count > 1 && !busy;
  const { ref, style, handleProps } = useSortableItem(block.id, !canReorder);

  const moveLabels: MoveLabels = {
    top: { Icon: ChevronsUpIcon, title: t("evidence.move_block_top") },
    bottom: { Icon: ChevronsDownIcon, title: t("evidence.move_block_bottom") },
  };

  const hasLabel = Boolean(block.label && block.label.trim() !== "");

  async function commitLabel(label: string): Promise<void> {
    if (await onLabel(label)) {
      setEditingLabel(false);
    }
  }

  async function remove(): Promise<void> {
    if (window.confirm(t("evidence.delete_block_confirm"))) {
      await onDelete();
      if (block.kind === "text") {
        forgetDraft(`draft:block:${block.id}`);
      }
    }
  }

  function handleClickRow(e: React.MouseEvent) {
    if (editingLabel) {
      setEditingLabel(false);
      return;
    }
    const target = e.target as HTMLElement | null;
    if (
      target?.closest("button") ||
      target?.closest("input") ||
      target?.closest("textarea")
    ) {
      return;
    }
    onJump(block.id);
  }

  return (
    <article
      id={`evidence-block-${block.id}`}
      ref={ref}
      style={style}
      onClick={handleClickRow}
      className="card flex h-14 items-center gap-2 px-3 py-1 cursor-pointer select-none transition-colors hover:bg-[var(--hover-wash)]"
    >
      {/* Left: Drag handle & Move buttons */}
      <div
        className="flex shrink-0 items-center gap-0.5"
        onClick={(e) => e.stopPropagation()}
      >
        {count > 1 && (
          <DragHandle
            title={t("common.drag_reorder")}
            disabled={busy}
            {...handleProps}
          />
        )}
        {MOVES.map(({ to, stuck }) => (
          <button
            key={to}
            type="button"
            title={moveLabels[to].title}
            disabled={busy || stuck(at, count)}
            onClick={() => void onMove(to)}
            className={TOOL_BUTTON}
          >
            {(() => {
              const Icon = moveLabels[to].Icon;
              return <Icon size={12} />;
            })()}
          </button>
        ))}
      </div>

      {/* Middle: Label and Summary */}
      <div className="flex flex-1 min-w-0 items-center gap-2 overflow-hidden">
        {editingLabel ? (
          <div
            onClick={(e) => e.stopPropagation()}
            className="min-w-[140px] max-w-[240px]"
          >
            <InlineEdit
              initial={block.label ?? ""}
              busy={busy}
              className="field-input py-1 px-2 text-xs"
              placeholder={t("evidence.block_label_placeholder")}
              onCommit={commitLabel}
              onCancel={() => setEditingLabel(false)}
            />
          </div>
        ) : hasLabel ? (
          <>
            <button
              type="button"
              title={t("evidence.edit_label_title")}
              onClick={(e) => {
                e.stopPropagation();
                setEditingLabel(true);
              }}
              className="shrink-0 max-w-[200px] truncate cursor-pointer text-xs font-semibold text-left"
              style={{ color: "var(--text-muted)" }}
            >
              {block.label}
            </button>
            <span
              className="shrink-0 text-xs select-none"
              style={{ color: "var(--text-faint)" }}
            >
              ·
            </span>
          </>
        ) : null}

        {/* Content Summary */}
        {block.kind === "text" ? (
          <span
            className="min-w-0 flex-1 truncate text-xs"
            style={{ fontFamily: "var(--mono)", color: "var(--text-muted)" }}
          >
            {getFirstLine(block.text)}
          </span>
        ) : block.kind === "table" ? (
          <span
            className="shrink-0 text-xs"
            style={{ color: "var(--text-muted)" }}
          >
            {t("evidence.outline_table_summary", {
              rows: block.rows.length,
              cols: block.rows[0]?.length ?? 0,
            })}
          </span>
        ) : imageError || block.image_url === null ? (
          <div
            className="flex h-10 w-12 shrink-0 items-center justify-center rounded"
            style={{
              background: "var(--hover-wash)",
              border: "1px dashed var(--border-strong)",
              color: "var(--text-faint)",
            }}
            title={t("evidence.image_load_failed")}
          >
            <ImageIcon size={16} />
          </div>
        ) : (
          <img
            src={block.image_url}
            alt={block.label ?? t("evidence.screenshot_alt")}
            onError={() => {
              setImageError(true);
              onImageError?.();
            }}
            className="h-10 w-auto max-w-[120px] shrink-0 rounded object-contain"
            style={{ border: "1px solid var(--border)" }}
          />
        )}

        {/* Small entry to add a label when block has none */}
        {!hasLabel && !editingLabel && (
          <button
            type="button"
            title={t("evidence.add_label_title")}
            onClick={(e) => {
              e.stopPropagation();
              setEditingLabel(true);
            }}
            className="icon-btn shrink-0 opacity-40 hover:opacity-100"
          >
            <PlusIcon size={11} />
          </button>
        )}
      </div>

      {/* Right: Delete button */}
      <div
        className="ml-auto flex shrink-0 items-center"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          disabled={busy}
          onClick={() => void remove()}
          className="icon-btn icon-btn-danger"
          title={t("common.delete")}
        >
          <TrashIcon size={12} />
        </button>
      </div>
    </article>
  );
}
