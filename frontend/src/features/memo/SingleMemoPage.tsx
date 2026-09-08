import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import { messageOf } from "../../shared/api";
import { useI18n } from "../../shared/i18n";
import { ArrowLeftIcon } from "../../shared/icons";
import { getMemo } from "./api";
import { MemoItem } from "./MemoItem";
import type { Memo } from "./types";

export function SingleMemoPage() {
  // Subscribing here re-renders this whole subtree (and its bare `t()` calls
  // below) when the language switches, instead of leaving it stale until some
  // unrelated state change happens to trigger a re-render.
  const { t } = useI18n();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [memo, setMemo] = useState<Memo | null>(null);
  const [isExpanded, setIsExpanded] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id || isNaN(Number(id))) {
      setError(t("memo.invalid_id"));
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
          setError(messageOf(cause, t("memo.not_found")));
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
    <main className="mx-auto flex max-w-3xl flex-col gap-4 px-8 py-9">
      <div>
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm font-medium transition-colors"
          style={{ color: "var(--text-muted)" }}
        >
          <ArrowLeftIcon size={13} />
          <span>{t("memo.back_to_all")}</span>
        </Link>
      </div>

      {loading && (
        <div className="py-12 text-center text-sm" style={{ color: "var(--text-faint)" }}>
          {t("common.loading")}
        </div>
      )}

      {!loading && error && (
        <div className="card p-8 text-center text-sm" style={{ color: "var(--text-muted)" }}>
          <p>{error}</p>
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

