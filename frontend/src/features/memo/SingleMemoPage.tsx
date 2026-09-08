import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { messageOf } from "../../shared/api";
import { getMemo } from "./api";
import { MemoItem } from "./MemoItem";
import type { Memo } from "./types";

export function SingleMemoPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [memo, setMemo] = useState<Memo | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id || isNaN(Number(id))) {
      setError("无效的 Memo ID");
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    getMemo(Number(id))
      .then((loaded) => {
        if (active) {
          setMemo(loaded);
        }
      })
      .catch((cause) => {
        if (active) {
          setError(messageOf(cause, "该 Memo 不存在或已被删除"));
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [id]);

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-4 px-6 py-8">
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors"
        >
          <span>←</span>
          <span>回到全部</span>
        </Link>
      </div>

      {loading && (
        <div className="py-12 text-center text-sm text-slate-400">
          载入中…
        </div>
      )}

      {!loading && error && (
        <div className="rounded-lg border border-slate-200 bg-white p-8 text-center text-sm text-slate-500 shadow-xs">
          <p className="text-slate-600">{error}</p>
        </div>
      )}

      {!loading && memo && (
        <ul className="list-none">
          <MemoItem
            memo={memo}
            isExpanded={isExpanded}
            onToggleExpand={() => setIsExpanded((prev) => !prev)}
            onUpdate={(updated) => setMemo(updated)}
            onDelete={() => navigate("/")}
          />
        </ul>
      )}
    </main>
  );
}
