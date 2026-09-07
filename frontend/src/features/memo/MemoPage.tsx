import { useCallback, useEffect, useState } from "react";

import { messageOf } from "../../shared/api";
import { createMemo, listMemos } from "./api";
import { MemoComposer } from "./MemoComposer";
import { MemoList } from "./MemoList";
import type { ImageUpload, Memo } from "./types";

/** One page: the box on top, what you have written below it. */
export function MemoPage() {
  const [memos, setMemos] = useState<Memo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let abandoned = false;

    listMemos()
      .then((loaded) => {
        if (abandoned) {
          return;
        }
        // The box is usable from the first paint, so a memo may already have
        // been saved while this request was in flight. It belongs on top of
        // what came back, not underneath it — and must not be dropped.
        setMemos((savedMeanwhile) => {
          const alreadyHere = new Set(savedMeanwhile.map((memo) => memo.id));
          return [
            ...savedMeanwhile,
            ...loaded.filter((memo) => !alreadyHere.has(memo.id)),
          ];
        });
      })
      .catch((cause: unknown) => {
        if (!abandoned) {
          setError(messageOf(cause, "载入失败"));
        }
      })
      .finally(() => {
        if (!abandoned) {
          setLoading(false);
        }
      });

    return () => {
      abandoned = true;
    };
  }, []);

  // The saved memo goes straight to the top — no refetch, so it lands the
  // instant the request returns.
  const save = useCallback(async (body: string, images?: ImageUpload[]) => {
    const saved = await createMemo(body, images);
    setMemos((current) => [saved, ...current]);
    setError(null);
  }, []);


  const update = useCallback((updated: Memo) => {
    setMemos((current) =>
      current.map((memo) => (memo.id === updated.id ? updated : memo)),
    );
  }, []);

  const remove = useCallback((id: number) => {
    setMemos((current) => current.filter((memo) => memo.id !== id));
  }, []);

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-8">
      <MemoComposer onSave={save} />
      <MemoList
        memos={memos}
        loading={loading}
        error={error}
        onUpdate={update}
        onDelete={remove}
      />
    </main>
  );

}
