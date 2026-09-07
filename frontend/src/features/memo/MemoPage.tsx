import { useCallback, useEffect, useState } from "react";

import { messageOf } from "../../shared/api";
import type { ImageUpload } from "../../shared/images";
import { createMemo, listMemos } from "./api";
import { MemoComposer } from "./MemoComposer";
import { MemoList } from "./MemoList";
import { MemoSearchBar } from "./MemoSearchBar";
import type { Memo } from "./types";

/** One page: the box on top, search bar in between, what you have written below it. */
export function MemoPage() {
  const [memos, setMemos] = useState<Memo[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMemos = useCallback(async (query: string) => {
    setLoading(true);
    try {
      const loaded = await listMemos(query);
      setMemos(loaded);
      setError(null);
    } catch (cause: unknown) {
      setError(messageOf(cause, "载入失败"));
    } finally {
      setLoading(false);
    }
  }, []);

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

  const handleSearch = useCallback(
    (query: string) => {
      setSearchQuery(query);
      void fetchMemos(query);
    },
    [fetchMemos],
  );

  const save = useCallback(
    async (body: string, images?: ImageUpload[]) => {
      const saved = await createMemo(body, images);
      setError(null);

      if (searchQuery.trim() === "") {
        // Straight to the top — no refetch, so it lands the instant the
        // request returns.
        setMemos((current) => [saved, ...current]);
        return;
      }
      // A search is on, so this list is a result set, not the whole list. Let
      // the server say whether what was just written belongs in it — and if
      // it does, with which snippets.
      await fetchMemos(searchQuery);
    },
    [searchQuery, fetchMemos],
  );

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
      <MemoSearchBar onChange={handleSearch} />
      <MemoList
        memos={memos}
        loading={loading}
        error={error}
        searchQuery={searchQuery}
        onUpdate={update}
        onDelete={remove}
      />
    </main>
  );
}
