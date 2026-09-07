import { useEditRunner } from "../../shared/useEditRunner";
import { useLoad } from "../../shared/useLoad";
import {
  addTextBlock,
  deleteBlock,
  editBlockText,
  getCase,
  moveBlock,
  setBlockLabel,
} from "./api";
import { BlockCard } from "./BlockCard";
import { BlockTextArea } from "./BlockTextArea";
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
 */
export function CaseBlocks({ evidenceId, caseId }: CaseBlocksProps) {
  const {
    value: content,
    setValue: setContent,
    loading,
    error,
  } = useLoad<CaseDetail>(
    () => getCase(evidenceId, caseId),
    [evidenceId, caseId],
  );

  const { busy, error: blockError, run } = useEditRunner("操作失败");

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

  async function handleMove(blockId: number, to: Move): Promise<void> {
    await run(async () => {
      setBlocks(await moveBlock(evidenceId, caseId, blockId, to));
    });
  }

  async function handleDelete(blockId: number): Promise<void> {
    await run(async () => {
      await deleteBlock(evidenceId, caseId, blockId);
      setBlocks(blocks.filter((one) => one.id !== blockId));
    });
  }

  if (content === null) {
    return (
      <p className="py-8 text-center text-sm text-slate-400">
        {loading ? "载入中…" : (error ?? "打不开这个用例。")}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {blocks.length === 0 ? (
        <p className="py-6 text-center text-xs text-slate-400">
          这个用例还是空的。下面写一段就开始了。
        </p>
      ) : (
        blocks.map((block, at) => (
          <BlockCard
            key={block.id}
            block={block}
            at={at}
            count={blocks.length}
            busy={busy}
            onEditText={(text) => handleEditText(block.id, text)}
            onLabel={(label) => handleLabel(block.id, label)}
            onMove={(to) => handleMove(block.id, to)}
            onDelete={() => handleDelete(block.id)}
          />
        ))
      )}

      {blockError !== null && (
        <p className="text-xs text-red-600">{blockError}</p>
      )}

      <BlockTextArea
        initial=""
        busy={busy}
        hint="Ctrl+Enter 添加一段"
        placeholder="写一段,或者粘贴一段日志…"
        onCommit={handleAdd}
      />
    </div>
  );
}
