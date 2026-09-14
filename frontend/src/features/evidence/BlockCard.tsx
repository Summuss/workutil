import { useState } from "react";

import { InlineEdit } from "../../shared/InlineEdit";
import { useI18n } from "../../shared/i18n";
import {
  ChevronsDownIcon,
  ChevronsUpIcon,
  EditIcon,
  TrashIcon,
} from "../../shared/icons";
import { DragHandle, useSortableItem } from "../../shared/sortable";
import { Lightbox } from "../../shared/Lightbox";
import { useDraft } from "../../shared/useDraft";
import { BlockTextArea } from "./BlockTextArea";
import { hasTableMarkings } from "./clipboard";
import { TableBlockView } from "./TableBlockView";
import { MOVES, TOOL_BUTTON, type MoveLabels } from "./toolbar";
import type { Block, Move } from "./types";

/**
 * Everything that can be done to a table, which is everything one kind of
 * block can do that the others cannot.
 *
 * One prop rather than five: they arrive together, they are ignored together
 * by the other two kinds, and a table gaining an operation should not widen
 * every block's interface. There is no `onAddRow` and there never will be —
 * the reason is on the server, beside the endpoints that refuse to grow one.
 */
export interface TableActions {
  onHeader: (hasHeader: boolean) => Promise<void>;
  onCell: (row: number, column: number, value: string) => Promise<boolean>;
  onDeleteRow: (row: number) => Promise<void>;
  onDeleteColumn: (column: number) => Promise<void>;
  /** Takes back a wrong guess — this was a log, not a query result. */
  onAsText: () => Promise<void>;
}

interface BlockCardProps {
  block: Block;
  at: number;
  count: number;
  busy: boolean;
  /** Set when this block is one the server has just guessed the kind of, which
      is what puts the confirmation under it. */
  guessed: boolean;
  onEditText: (text: string) => Promise<boolean>;
  onLabel: (label: string) => Promise<boolean>;
  onMove: (to: Move) => Promise<void>;
  onDelete: () => Promise<void>;
  onSplitLines?: (splitLines: boolean) => Promise<void>;
  onAsTable?: () => Promise<boolean>;
  table: TableActions;
}

const LABEL_FIELD = "field-input min-w-0 flex-1";

/**
 * One block: its heading, its content, and what can be done to it.
 *
 * Editing is a button rather than a click on the content, deliberately: memo
 * tried click-to-edit and reverted it within a day (design.md §6 F1). Copying
 * a stack trace out of what you just pasted is an everyday move here too, and
 * drag-selecting text ends in a click that would throw the selection away.
 *
 * A block can be converted back and forth between table and text without limit
 * (ADR-0004): a mistaken conversion or an unrecognized query result can be
 * turned into a table, and a table can be returned to text.
 */
export function BlockCard({
  block,
  at,
  count,
  busy,
  guessed,
  onEditText,
  onLabel,
  onMove,
  onDelete,
  onSplitLines,
  onAsTable,
  table,
}: BlockCardProps) {
  const { t } = useI18n();
  const [editingText, setEditingText] = useState(false);
  const [editingLabel, setEditingLabel] = useState(false);
  const [editingTable, setEditingTable] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [imageError, setImageError] = useState(false);

  const isTextBlock = block.kind === "text";
  const {
    draft: textDraft,
    setDraft: setTextDraft,
    isDirty: isTextDirty,
    discard: discardTextDraft,
    commit: commitTextDraft,
  } = useDraft(
    isTextBlock ? `draft:block:${block.id}` : "",
    isTextBlock ? block.text : ""
  );

  const canReorder = count > 1 && !busy;
  const { ref, style, handleProps } = useSortableItem(block.id, !canReorder);

  const moveLabels: MoveLabels = {
    top: { Icon: ChevronsUpIcon, title: t("evidence.move_block_top") },
    bottom: { Icon: ChevronsDownIcon, title: t("evidence.move_block_bottom") },
  };

  async function commitText(text: string): Promise<boolean> {
    const accepted = await onEditText(text);
    if (accepted) {
      commitTextDraft();
      setEditingText(false);
    }
    return accepted;
  }

  async function commitLabel(label: string): Promise<void> {
    if (await onLabel(label)) {
      setEditingLabel(false);
    }
  }

  async function handleAsTable(): Promise<void> {
    // The draft goes only once the server has taken the text. A refusal
    // ("这段文字切不出表格") leaves this a text block, and whatever was typed
    // into it and not yet saved has to still be there when it does.
    if (await onAsTable?.()) {
      discardTextDraft();
    }
  }

  async function remove(): Promise<void> {
    // Deleting an image block deletes the screenshot itself, which nothing
    // undoes — hence the same confirmation as any other block, and no more.
    if (window.confirm(t("evidence.delete_block_confirm"))) {
      await onDelete();
      if (isTextBlock) {
        discardTextDraft();
      }
    }
  }

  return (
    <article
      id={`evidence-block-${block.id}`}
      ref={ref}
      style={style}
      className="card flex flex-col gap-2 px-4 py-3"
    >
      <div className="flex items-center gap-1">
        {editingLabel ? (
          <InlineEdit
            initial={block.label ?? ""}
            busy={busy}
            className={LABEL_FIELD}
            placeholder={t("evidence.block_label_placeholder")}
            onCommit={commitLabel}
            onCancel={() => setEditingLabel(false)}
          />
        ) : (
          <button
            type="button"
            title={block.label === null ? t("evidence.add_label_title") : t("evidence.edit_label_title")}
            onClick={() => setEditingLabel(true)}
            className={
              block.label === null
                ? "cursor-pointer text-xs"
                : "min-w-0 flex-1 cursor-pointer truncate text-left text-xs font-semibold"
            }
            style={{ color: block.label === null ? "var(--text-faint)" : "var(--text-muted)" }}
          >
            {block.label ?? t("evidence.add_label_button")}
          </button>
        )}

        {isTextDirty && (
          <span
            className="shrink-0 rounded px-1.5 py-0.5 text-[10.5px]"
            style={{
              fontFamily: "var(--mono)",
              color: "var(--warn)",
              background: "var(--warn-tint)",
            }}
          >
            {t("evidence.unsaved")}
          </span>
        )}

        <div className="ml-auto flex shrink-0 items-center gap-0.5">
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
          {block.kind === "text" && (
            <>
              {block.text.includes("\n") && (
                <button
                  type="button"
                  title={t("evidence.split_lines_tooltip")}
                  disabled={busy}
                  onClick={() => void onSplitLines?.(!block.split_lines)}
                  className={TOOL_BUTTON}
                >
                  {block.split_lines
                    ? t("evidence.split_lines_merge")
                    : t("evidence.split_lines_split")}
                </button>
              )}
              {hasTableMarkings(block.text) && (
                <button
                  type="button"
                  title={t("evidence.text_to_table_tooltip")}
                  disabled={busy}
                  onClick={() => void handleAsTable()}
                  className={TOOL_BUTTON}
                >
                  {t("evidence.text_to_table")}
                </button>
              )}
              <button
                type="button"
                disabled={busy || editingText}
                onClick={() => setEditingText(true)}
                className="icon-btn"
                title={t("common.edit")}
              >
                <EditIcon size={12} />
              </button>
            </>
          )}
          {block.kind === "table" && (
            <>
              {/* Stated rather than toggled blind: the button says which way
                  it will go, and the first row is redrawn the moment it does. */}
              <button
                type="button"
                title={t("evidence.table_header_tooltip")}
                disabled={busy}
                onClick={() => void table.onHeader(!block.has_header)}
                className={TOOL_BUTTON}
              >
                {block.has_header ? t("evidence.table_unset_header") : t("evidence.table_set_header")}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => setEditingTable(!editingTable)}
                className={TOOL_BUTTON}
              >
                {editingTable ? t("common.done") : t("common.edit")}
              </button>
              {/* Also here, and not only in the confirmation below, because a
                  wrong guess is often noticed later — on the read-through
                  before exporting, a day after the paste. The confirmation is
                  the one-click version while it is still fresh; this is the
                  door that is still there tomorrow. */}
              <button
                type="button"
                title={t("evidence.table_to_text_tooltip")}
                disabled={busy}
                onClick={() => void table.onAsText()}
                className={TOOL_BUTTON}
              >
                {t("evidence.table_to_text")}
              </button>
            </>
          )}
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
      </div>

      {/* The body is the one part that belongs to a kind; everything above
          this line belongs to all of them. */}
      {block.kind === "table" ? (
        <TableBlockView
          block={block}
          busy={busy}
          editing={editingTable}
          onCell={table.onCell}
          onDeleteRow={table.onDeleteRow}
          onDeleteColumn={table.onDeleteColumn}
        />
      ) : block.kind === "image" ? (
        /* Shown whole, scaled down to the card. The file on disk is the
           original — the only resizing this tool does happens on the copy
           inside an exported workbook (design.md §6 F5).

           No `src` fallback: an empty one asks the server for this page again
           and draws the answer as a broken image. */
        block.image_url !== null && (
          <>
            <img
              src={block.image_url}
              alt={block.label ?? t("evidence.screenshot_alt")}
              onClick={() => {
                if (!imageError) {
                  setLightboxOpen(true);
                }
              }}
              onError={() => setImageError(true)}
              className={`max-w-full self-start rounded-md${imageError ? "" : " cursor-pointer"}`}
              style={{ border: "1px solid var(--border)" }}
            />
            {lightboxOpen && !imageError && (
              <Lightbox
                src={block.image_url}
                alt={block.label ?? t("evidence.screenshot_alt")}
                onClose={() => setLightboxOpen(false)}
              />
            )}
          </>
        )
      ) : editingText ? (
        <BlockTextArea
          initial={block.text}
          value={textDraft}
          onChange={setTextDraft}
          isDirty={isTextDirty}
          onDiscard={discardTextDraft}
          busy={busy}
          autoFocus
          hint={t("evidence.edit_block_hint")}
          onCommit={commitText}
          onCancel={() => setEditingText(false)}
        />
      ) : (
        <pre
          className="overflow-x-auto whitespace-pre-wrap text-xs leading-relaxed"
          style={{ fontFamily: "var(--mono)", color: "var(--text)" }}
        >
          {block.text}
        </pre>
      )}

      {/* The guess, said out loud, with the way out of it beside it.
          Recognising a table is a guess that will sometimes be wrong — an
          indented log has every mark of one — so it costs nothing when right
          and one click when not. It is also the receipt for the paste: this is
          the line that says the thing you just pasted went in (spec 粘贴时的类型判别).
          It is ignorable and it goes on its own: nothing has to be dismissed,
          and it is gone on the next visit to this case — the toolbar keeps the
          correction itself, so what expires here is the reminder, not the way
          out. The kind is checked as well as the guess: correcting one leaves
          its id in `guessed`, and this line has to go the moment it does. */}
      {guessed && block.kind === "table" && (
        <p className="text-xs" style={{ color: "var(--text-faint)" }}>
          {t("evidence.table_detected", {
            rows: block.rows.length,
            cols: block.rows[0]?.length ?? 0,
          })}
          <button
            type="button"
            disabled={busy}
            onClick={() => void table.onAsText()}
            className="cursor-pointer underline underline-offset-2 disabled:cursor-default disabled:opacity-40"
            style={{ color: "var(--text-muted)" }}
          >
            {t("evidence.convert_to_plain_text")}
          </button>
        </p>
      )}
    </article>
  );
}
