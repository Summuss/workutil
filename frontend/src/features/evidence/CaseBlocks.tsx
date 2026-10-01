import { useEffect, useRef, useState } from "react";

import { arrayMove } from "@dnd-kit/sortable";

import { readImage } from "../../shared/images";
import { useI18n } from "../../shared/i18n";
import { useDraft } from "../../shared/useDraft";
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
  setBlockBoxes,
  setBlockLabel,
  setTableCell,
  setTableHeader,
  setTextBlockSplitLines,
  turnBlockIntoTable,
  turnBlockIntoText,
} from "./api";
import { BlockCard } from "./BlockCard";
import { BlockOutlineRow } from "./BlockOutlineRow";
import { BlockTextArea } from "./BlockTextArea";
import type { Box } from "../../shared/BoxOverlay";
import { Lightbox } from "../../shared/Lightbox";
import { guardDuplicateImagePaste } from "../../shared/pasteDuplicateImage";
import { SortableList } from "../../shared/sortable";
import type { PastedText } from "./clipboard";
import type { Block, CaseDetail, Move } from "./types";

/** Where the bottom composer of one case keeps what has been typed into it. */
export function caseComposerDraftKey(caseId: number): string {
  return `draft:case:${caseId}:new`;
}

interface CaseBlocksProps {
  evidenceId: number;
  caseId: number;
  outline: boolean;
  onToggleOutline: (open: boolean) => void;
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
export function CaseBlocks({
  evidenceId,
  caseId,
  outline,
  onToggleOutline,
}: CaseBlocksProps) {
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
  const [jumpToBlockId, setJumpToBlockId] = useState<number | null>(null);
  const [failedImageIds, setFailedImageIds] = useState<ReadonlySet<number>>(new Set());
  const [activeImageBlockId, setActiveImageBlockId] = useState<number | null>(null);
  const [boxSelectActive, setBoxSelectActive] = useState(false);
  const hasPagedRef = useRef(false);

  const imageBlocks = blocks.filter(
    (b) => b.kind === "image" && b.image_url !== null && !failedImageIds.has(b.id),
  );

  const activeImageIndex =
    activeImageBlockId !== null
      ? imageBlocks.findIndex((b) => b.id === activeImageBlockId)
      : -1;
  const activeImageBlock =
    activeImageIndex !== -1 ? imageBlocks[activeImageIndex] : null;

  function handleImageError(blockId: number) {
    setFailedImageIds((prev) => {
      if (prev.has(blockId)) return prev;
      const next = new Set(prev);
      next.add(blockId);
      return next;
    });
  }

  function handleOpenLightbox(blockId: number, boxSelect: boolean = false) {
    hasPagedRef.current = false;
    setActiveImageBlockId(blockId);
    setBoxSelectActive(boxSelect);
  }

  function handleCloseLightbox() {
    if (hasPagedRef.current && activeImageBlockId !== null) {
      const el = document.getElementById(`evidence-block-${activeImageBlockId}`);
      el?.scrollIntoView({ block: "nearest" });
    }
    setActiveImageBlockId(null);
    setBoxSelectActive(false);
    hasPagedRef.current = false;
  }

  function handlePrevImage() {
    if (activeImageIndex > 0) {
      const target = imageBlocks[activeImageIndex - 1];
      if (target) {
        hasPagedRef.current = true;
        setActiveImageBlockId(target.id);
      }
    }
  }

  function handleNextImage() {
    if (activeImageIndex < imageBlocks.length - 1) {
      const target = imageBlocks[activeImageIndex + 1];
      if (target) {
        hasPagedRef.current = true;
        setActiveImageBlockId(target.id);
      }
    }
  }

  async function handleChangeBoxes(blockId: number, boxes: Box[]): Promise<boolean> {
    const block = blocks.find((one) => one.id === blockId);
    if (!block) return false;

    // Shown first and saved after, so a stroke stays where the drag left it
    // instead of vanishing for the round trip. A refusal puts back what the
    // server still holds (design.md §6 F5 截图上的红框).
    replace({ ...block, boxes });
    const saved = await run(async () => {
      replace(await setBlockBoxes(evidenceId, caseId, blockId, boxes));
    });
    if (!saved) {
      replace(block);
    }
    return saved;
  }

  function handleJump(blockId: number) {
    setJumpToBlockId(blockId);
    onToggleOutline(false);
  }

  // The box at the bottom is a draft too, and per case: a paragraph typed
  // against case 3 belongs to case 3, not to whichever one is open when you
  // come back. Its saved side is the empty string, so committing — or simply
  // clearing the box — is what drops the key.
  const { draft: composerDraft, setDraft: setComposerDraft } = useDraft(
    caseComposerDraftKey(caseId),
    "",
  );

  useEffect(() => {
    scrollContainerRef.current?.scrollTo({ top: 0 });
    setScrollToBlockId(null);
    setJumpToBlockId(null);
    setActiveImageBlockId(null);
    setBoxSelectActive(false);
    hasPagedRef.current = false;
  }, [caseId]);

  useEffect(() => {
    if (outline) {
      setActiveImageBlockId(null);
      setBoxSelectActive(false);
      hasPagedRef.current = false;
    }
  }, [outline]);

  /**
   * Bring the block that was just added into view, end first.
   *
   * `end` rather than `nearest`, because the thing being added is usually a
   * screenshot and a screenshot is usually taller than the list: `nearest`
   * counts a block as in view the moment its first pixel is, which parks the
   * viewport on the top edge of the picture — the part you were already
   * looking at. What you want to see is that the whole thing landed, which is
   * its bottom.
   *
   * And it has to wait for the bytes. An `<img>` with nothing in it yet is a
   * couple of pixels tall, so scrolling to the end of *that* is scrolling to
   * the top of the picture that arrives a moment later — the same wrong place,
   * arrived at a different way. `error` counts as arrived too: a broken image
   * must not leave the list parked wherever it was.
   */
  useEffect(() => {
    if (scrollToBlockId === null) return;
    const el = document.getElementById(`evidence-block-${scrollToBlockId}`);
    if (el === null) return;

    const reveal = () => {
      el.scrollIntoView({ block: "end" });
      setScrollToBlockId(null);
    };

    const loading = Array.from(el.querySelectorAll("img")).filter(
      (image) => !image.complete,
    );
    if (loading.length === 0) {
      reveal();
      return;
    }

    let pending = loading.length;
    const arrived = () => {
      pending -= 1;
      if (pending === 0) reveal();
    };
    for (const image of loading) {
      image.addEventListener("load", arrived);
      image.addEventListener("error", arrived);
    }
    return () => {
      for (const image of loading) {
        image.removeEventListener("load", arrived);
        image.removeEventListener("error", arrived);
      }
    };
  }, [scrollToBlockId, blocks]);

  /**
   * Jump from outline back to normal view and scroll the target block to the top.
   *
   * Must wait until the target AND all image blocks preceding it have loaded
   * (or errored), because when switching back from outline mode all cards are
   * newly mounted. Before images have bytes they are only a few pixels tall, so
   * scrolling prematurely will cause the target's position to drift down as
   * preceding images load (design.md §6 F5).
   */
  useEffect(() => {
    if (jumpToBlockId === null) return;
    const targetIndex = blocks.findIndex((b) => b.id === jumpToBlockId);
    if (targetIndex === -1) {
      setJumpToBlockId(null);
      return;
    }

    const targetEl = document.getElementById(`evidence-block-${jumpToBlockId}`);
    if (targetEl === null) return;

    const reveal = () => {
      targetEl.scrollIntoView({ block: "start" });
      setJumpToBlockId(null);
    };

    const precedingBlocks = blocks.slice(0, targetIndex + 1);
    const precedingImageBlocks = precedingBlocks.filter(
      (b) => b.kind === "image" && b.image_url !== null,
    );

    if (precedingImageBlocks.length === 0) {
      reveal();
      return;
    }

    const precedingEls = precedingBlocks
      .map((b) => document.getElementById(`evidence-block-${b.id}`))
      .filter((el): el is HTMLElement => el !== null);

    const allImages = precedingEls.flatMap((el) =>
      Array.from(el.querySelectorAll("img")),
    );
    const loading = allImages.filter((image) => !image.complete);

    if (loading.length === 0) {
      reveal();
      return;
    }

    let pending = loading.length;
    const arrived = () => {
      pending -= 1;
      if (pending === 0) {
        reveal();
      }
    };

    for (const image of loading) {
      if (image.complete) {
        pending -= 1;
      } else {
        image.addEventListener("load", arrived);
        image.addEventListener("error", arrived);
      }
    }

    if (pending === 0) {
      reveal();
      return;
    }

    return () => {
      for (const image of loading) {
        image.removeEventListener("load", arrived);
        image.removeEventListener("error", arrived);
      }
    };
  }, [jumpToBlockId, blocks, outline]);

  function setBlocks(next: Block[]) {
    setContent((current) =>
      current === null ? current : { ...current, blocks: next },
    );
  }

  async function handleAdd(text: string): Promise<boolean> {
    const accepted = await run(async () => {
      const added = await addTextBlock(evidenceId, caseId, text);
      setBlocks([...blocks, added]);
      setScrollToBlockId(added.id);
    });
    if (accepted) {
      // The composer empties in place and keeps the cursor, which is what makes
      // "keep pasting" work. It is done here rather than inside `BlockTextArea`
      // because the box is controlled from out here now.
      setComposerDraft("");
    }
    return accepted;
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
    if (files.length === 0) {
      return;
    }
    const recordSuccess = await guardDuplicateImagePaste(files);
    if (!recordSuccess) {
      return;
    }
    await run(async () => {
      const added: Block[] = [];
      try {
        for (const file of files) {
          added.push(
            await addImageBlock(evidenceId, caseId, await readImage(file)),
          );
        }
        await recordSuccess();
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

  function handleAsTable(blockId: number): Promise<boolean> {
    return run(async () => {
      replace(await turnBlockIntoTable(evidenceId, caseId, blockId));
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
      {/* Scroll container configured as a size query container so block card
          images can scale relative to its visible height (100cqh). Its own height
          is determined by the flex parent (`flex-1 min-h-0`), satisfying size
          containment without JavaScript (design.md §6 F5). */}
      <div
        ref={scrollContainerRef}
        className="flex-1 min-h-0 overflow-y-auto"
        style={{ containerType: "size" }}
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
              className={outline ? "flex flex-col gap-1.5" : "flex flex-col gap-3.5"}
            >
              {blocks.map((block, at) =>
                outline ? (
                  <BlockOutlineRow
                    key={block.id}
                    block={block}
                    at={at}
                    count={blocks.length}
                    busy={busy}
                    onLabel={(label) => handleLabel(block.id, label)}
                    onMove={(to) => handleMove(block.id, to)}
                    onDelete={() => handleDelete(block.id)}
                    onJump={handleJump}
                    onOpenLightbox={() => handleOpenLightbox(block.id)}
                    onImageError={() => handleImageError(block.id)}
                  />
                ) : (
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
                    onAsTable={() => handleAsTable(block.id)}
                    table={{
                      onHeader: (hasHeader) => handleHeader(block.id, hasHeader),
                      onCell: (row, column, value) =>
                        handleCell(block.id, row, column, value),
                      onDeleteRow: (row) => handleDeleteRow(block.id, row),
                      onDeleteColumn: (column) => handleDeleteColumn(block.id, column),
                      onAsText: () => handleAsText(block.id),
                    }}
                    onOpenLightbox={() => handleOpenLightbox(block.id)}
                    onOpenBoxSelect={() => handleOpenLightbox(block.id, true)}
                    onImageError={() => handleImageError(block.id)}
                  />
                ),
              )}
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
            value={composerDraft}
            onChange={setComposerDraft}
            busy={busy}
            hint={t("evidence.block_add_hint")}
            placeholder={t("evidence.block_add_placeholder")}
            onImages={(files) => void handleImages(files)}
            onTable={(paste) => void handleTable(paste)}
            onCommit={handleAdd}
          />
        </div>
      </div>

      {activeImageBlock && (
        <Lightbox
          src={activeImageBlock.image_url ?? ""}
          alt={activeImageBlock.label ?? t("evidence.screenshot_alt")}
          position={`${activeImageIndex + 1} / ${imageBlocks.length}`}
          label={activeImageBlock.label}
          onClose={handleCloseLightbox}
          onPrev={handlePrevImage}
          onNext={handleNextImage}
          hasPrev={activeImageIndex > 0}
          hasNext={activeImageIndex < imageBlocks.length - 1}
          boxes={activeImageBlock.boxes}
          boxSelectActive={boxSelectActive}
          onToggleBoxSelect={setBoxSelectActive}
          onChangeBoxes={(boxes) => handleChangeBoxes(activeImageBlock.id, boxes)}
          error={blockError}
        />
      )}
    </div>
  );
}
