import { useEffect, useRef, useState } from "react";

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
  setTextBlockSplitLines,
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

function CaseBlocksSkeleton() {
  return (
    <div className="flex flex-1 flex-col gap-3.5 py-2 animate-pulse min-h-[300px]">
      <div
        className="h-20 rounded-lg opacity-60"
        style={{ background: "var(--surface-raised)", border: "1px solid var(--border)" }}
      />
      <div
        className="h-28 rounded-lg opacity-60"
        style={{ background: "var(--surface-raised)", border: "1px solid var(--border)" }}
      />
      <div
        className="h-24 rounded-lg opacity-60"
        style={{ background: "var(--surface-raised)", border: "1px solid var(--border)" }}
      />
    </div>
  );
}

/**
 * What is inside one case, and the box you keep adding to it from.
 *
 * Three-tier layout:
 * - The block list is the only scrollable area.
 * - Composer is fixed at the bottom so it stays pinned while pasting screenshots.
 * - Loading uses an equal-height skeleton placeholder to prevent layout collapse.
 */
export function CaseBlocks({ evidenceId, caseId }: CaseBlocksProps) {
  const { t } = useI18n();
  const scrollContainerRef = useRef<HTMLDivElement>(null);

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

  const [guessed, setGuessed] = useState<ReadonlySet<number>>(new Set());

  const blocks = content?.blocks ?? [];

  const [scrollToBlockId, setScrollToBlockId] = useState<number | null>(null);

  useEffect(() => {
    scrollContainerRef.current?.scrollTo({ top: 0 });
    setScrollToBlockId(null);
  }, [caseId]);

  useEffect(() => {
    if (scrollToBlockId === null) return;
    const el = document.getElementById(`evidence-block-${scrollToBlockId}`);
    if (el) {
      el.scrollIntoView({ block: "nearest" });
      setScrollToBlockId(null);
    }
  }, [scrollToBlockId, blocks]);

  function setBlocks(next: Block[]) {
    setContent((current) =>
      current === null ? current : { ...current, blocks: next },
    );
  }

  function handleAdd(text: string): Promise<boolean> {
    return run(async () => {
      const added = await addTextBlock(evidenceId, caseId, text);
      setBlocks([...blocks, added]);
      setScrollToBlockId(added.id);
    });
  }

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
      setScrollToBlockId(added.id);
    });
  }

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
          const last = added[added.length - 1];
          if (last) {
            setScrollToBlockId(last.id);
          }
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

  async function handleAsText(blockId: number): Promise<void> {
    await run(async () => {
      replace(await turnBlockIntoText(evidenceId, caseId, blockId));
    });
  }

  async function handleSplitLines(
    blockId: number,
    splitLines: boolean,
  ): Promise<void> {
    await run(async () => {
      replace(
        await setTextBlockSplitLines(evidenceId, caseId, blockId, splitLines),
      );
    });
  }

  return (
    <div className="flex flex-1 min-h-0 flex-col">
      <div
        ref={scrollContainerRef}
        className="flex-1 min-h-0 overflow-y-auto"
      >
        <div className="flex w-full flex-col gap-3.5 px-8 pt-1 pb-4 min-h-[300px]">
          {loading ? (
            <CaseBlocksSkeleton />
          ) : content === null ? (
            <div
              className="flex flex-1 min-h-[300px] items-center justify-center text-[13px]"
              style={{ color: "var(--text-faint)" }}
            >
              {error ?? t("evidence.open_case_failed")}
            </div>
          ) : blocks.length === 0 ? (
            <div
              className="flex flex-1 min-h-[300px] items-center justify-center rounded-lg py-12 text-xs"
              style={{ border: "1px dashed var(--border-strong)", color: "var(--text-faint)" }}
            >
              {t("evidence.case_empty_hint")}
            </div>
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
                  onSplitLines={(splitLines) =>
                    handleSplitLines(block.id, splitLines)
                  }
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
        </div>
      </div>

      <div className="shrink-0 z-10" style={{ background: "var(--bg)" }}>
        <div className="flex w-full flex-col gap-2 px-8 py-3.5">
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
      </div>
    </div>
  );
}
