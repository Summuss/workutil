import { useState } from "react";

import { arrayMove } from "@dnd-kit/sortable";

import { readImage } from "../../shared/images";
import { useI18n } from "../../shared/i18n";
import { useEditRunner } from "../../shared/useEditRunner";
import { useLoad } from "../../shared/useLoad";
import {
  addImageBlock,
  addPastedBlock,
  addTextBlock,
  deleteBlock,
  deleteTableColumn,
  deleteTableRow,
  editBlockText,
  getCase,
  moveBlock,
  setBlockLabel,
  setTableCell,
  setTableHeader,
  turnBlockIntoText,
} from "./api";
import { BlockCard } from "./BlockCard";
import { BlockTextArea } from "./BlockTextArea";
import { SortableList } from "../../shared/sortable";
import type { PastedText } from "./clipboard";
import type { Block, CaseDetail, Move } from "./types";

interface CaseBlocksProps {
  evidenceId: number;
  caseId: number;
}

/**
 * What is inside one case, and the box you keep adding to it from.
 *
 * Loaded a case at a time rather than with the whole evidence: only the open
 * case is on screen, and the others can be carrying every screenshot of a
 * day's verification. The composer sits at the bottom because that is where
 * the next block goes — this is a page you paste down, not fill in.
 *
 * Which is why the composer takes screenshots as well as words: pasting is one
 * gesture, and what happens next is decided by what was on the clipboard
 * rather than by which box you aimed at first (spec User Stories 8).
 */
export function CaseBlocks({ evidenceId, caseId }: CaseBlocksProps) {
  const { t } = useI18n();
  const {
    value: content,
    setValue: setContent,
    loading,
    error,
  } = useLoad<CaseDetail>(
    () => getCase(evidenceId, caseId),
    [evidenceId, caseId],
  );

  const { busy, error: blockError, run } = useEditRunner(t("common.action_failed"));

  // The blocks whose kind the server worked out during this visit — the only
  // ones that draw the confirmation. Deliberately not stored: the line is there
  // to be read once and ignored, and a case reopened tomorrow should show the
  // tables, not a running commentary on how they were recognised.
  const [guessed, setGuessed] = useState<ReadonlySet<number>>(new Set());

  const blocks = content?.blocks ?? [];

  function setBlocks(next: Block[]) {
    setContent((current) =>
      current === null ? current : { ...current, blocks: next },
    );
  }

  function handleAdd(text: string): Promise<boolean> {
    return run(async () => {
      setBlocks([...blocks, await addTextBlock(evidenceId, caseId, text)]);
    });
  }

  /**
   * A paste that might be a query result, cut up by the server.
   *
   * What comes back says which kind it turned out to be, and a table is
   * remembered as a guess so the block draws the confirmation under itself.
   * That set is only ever added to here: reopening the case clears it, which is
   * what keeps a line meant as "that landed" from becoming furniture.
   */
  async function handleTable(paste: PastedText): Promise<void> {
    await run(async () => {
      const added = await addPastedBlock(
        evidenceId,
        caseId,
        paste.text,
        paste.html,
      );
      setGuessed((current) => new Set(current).add(added.id));
      setBlocks([...blocks, added]);
    });
  }

  /**
   * Pasted or dropped screenshots, one block each, in the order they came.
   *
   * Sent one at a time on purpose: the order they land in is the order they
   * were on the clipboard. What already got through stays on screen even if a
   * later one fails — those blocks are on the server, and hiding them would
   * only mean finding them again on the next reload.
   */
  async function handleImages(files: File[]): Promise<void> {
    await run(async () => {
      const added: Block[] = [];
      try {
        for (const file of files) {
          added.push(
            await addImageBlock(evidenceId, caseId, await readImage(file)),
          );
        }
      } finally {
        if (added.length > 0) {
          setBlocks([...blocks, ...added]);
        }
      }
    });
  }

  function replace(edited: Block) {
    setBlocks(blocks.map((one) => (one.id === edited.id ? edited : one)));
  }

  function handleEditText(blockId: number, text: string): Promise<boolean> {
    return run(async () => {
      replace(await editBlockText(evidenceId, caseId, blockId, text));
    });
  }

  function handleLabel(blockId: number, label: string): Promise<boolean> {
    return run(async () => {
      replace(await setBlockLabel(evidenceId, caseId, blockId, label));
    });
  }

  async function handleReorderBlock(
    activeId: number | string,
    targetIndex: number,
  ): Promise<void> {
    const blockId = Number(activeId);
    const oldIndex = blocks.findIndex((b) => b.id === blockId);
    if (oldIndex === -1 || oldIndex === targetIndex) return;

    const prev = blocks;
    const reorderedOptimistic = arrayMove(blocks, oldIndex, targetIndex).map(
      (b, idx) => ({ ...b, order: idx }),
    );
    setBlocks(reorderedOptimistic);

    await run(async () => {
      try {
        setBlocks(await moveBlock(evidenceId, caseId, blockId, targetIndex));
      } catch (cause) {
        setBlocks(prev);
        throw cause;
      }
    });
  }

  function handleMove(blockId: number, to: Move): Promise<void> {
    const targetIndex =
      typeof to === "number" ? to : to === "top" ? 0 : blocks.length - 1;
    return handleReorderBlock(blockId, targetIndex);
  }

  async function handleDelete(blockId: number): Promise<void> {
    await run(async () => {
      await deleteBlock(evidenceId, caseId, blockId);
      setBlocks(blocks.filter((one) => one.id !== blockId));
    });
  }

  // --- Inside a table -------------------------------------------------------
  //
  // Every one of these answers with the whole block, so the table on screen is
  // always the table the server has — which matters most for the two that
  // change its shape. Nothing here adds a row or a column, and that is the
  // point; the reason is on the server.

  async function handleHeader(
    blockId: number,
    hasHeader: boolean,
  ): Promise<void> {
    await run(async () => {
      replace(await setTableHeader(evidenceId, caseId, blockId, hasHeader));
    });
  }

  function handleCell(
    blockId: number,
    row: number,
    column: number,
    value: string,
  ): Promise<boolean> {
    return run(async () => {
      replace(
        await setTableCell(evidenceId, caseId, blockId, row, column, value),
      );
    });
  }

  async function handleDeleteRow(blockId: number, row: number): Promise<void> {
    await run(async () => {
      replace(await deleteTableRow(evidenceId, caseId, blockId, row));
    });
  }

  async function handleDeleteColumn(
    blockId: number,
    column: number,
  ): Promise<void> {
    await run(async () => {
      replace(await deleteTableColumn(evidenceId, caseId, blockId, column));
    });
  }

  /** The one click that takes back a wrong guess. The block stays the block —
      same place, same heading — so nothing but its kind changes. */
  async function handleAsText(blockId: number): Promise<void> {
    await run(async () => {
      replace(await turnBlockIntoText(evidenceId, caseId, blockId));
    });
  }

  if (content === null) {
    return (
      <p className="py-8 text-center text-[13px]" style={{ color: "var(--text-faint)" }}>
        {loading ? t("common.loading") : (error ?? t("evidence.open_case_failed"))}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3.5">
      {blocks.length === 0 ? (
        <p className="py-6 text-center text-xs" style={{ color: "var(--text-faint)" }}>
          {t("evidence.case_empty_hint")}
        </p>
      ) : (
        <SortableList
          items={blocks}
          onReorder={handleReorderBlock}
          className="flex flex-col gap-3.5"
        >
          {blocks.map((block, at) => (
            <BlockCard
              key={block.id}
              block={block}
              at={at}
              count={blocks.length}
              busy={busy}
              guessed={guessed.has(block.id)}
              onEditText={(text) => handleEditText(block.id, text)}
              onLabel={(label) => handleLabel(block.id, label)}
              onMove={(to) => handleMove(block.id, to)}
              onDelete={() => handleDelete(block.id)}
              table={{
                onHeader: (hasHeader) => handleHeader(block.id, hasHeader),
                onCell: (row, column, value) =>
                  handleCell(block.id, row, column, value),
                onDeleteRow: (row) => handleDeleteRow(block.id, row),
                onDeleteColumn: (column) => handleDeleteColumn(block.id, column),
                onAsText: () => handleAsText(block.id),
              }}
            />
          ))}
        </SortableList>
      )}

      {blockError !== null && (
        <p className="text-xs" style={{ color: "var(--danger)" }}>
          {blockError}
        </p>
      )}

      <BlockTextArea
        initial=""
        busy={busy}
        hint={t("evidence.block_add_hint")}
        placeholder={t("evidence.block_add_placeholder")}
        onImages={(files) => void handleImages(files)}
        onTable={(paste) => void handleTable(paste)}
        onCommit={handleAdd}
      />
    </div>
  );
}
