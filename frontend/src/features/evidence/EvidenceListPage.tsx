import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import { messageOf } from "../../shared/api";
import { useI18n } from "../../shared/i18n";
import { TrashIcon } from "../../shared/icons";
import { formatTime } from "../../shared/time";
import { useLoad } from "../../shared/useLoad";
import { PageLayout } from "../../shared/PageLayout";
import { createEvidence, deleteEvidence, listEvidence } from "./api";
import { forgetEvidence } from "./lastVisited";
import type { Evidence } from "./types";

/**
 * The evidence you have started, newest first.
 *
 * No search box, and that is a decision rather than a gap: ADR-0001 gives
 * "find it again by searching" to Memo. An evidence is finished and handed
 * over; what a full list eventually wants is archiving, not searching.
 */
export function EvidenceListPage() {
  const { t } = useI18n();
  const {
    value: loaded,
    setValue: setEvidence,
    loading,
    error,
    setError,
  } = useLoad<Evidence[]>(() => listEvidence());
  const evidence = loaded ?? [];

  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (title.trim() === "" || creating) {
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const created = await createEvidence(title.trim());
      // Straight to the top, where the server would have put it — the list is
      // ordered by creation, and this is the newest thing there is.
      setEvidence((current) => [created, ...(current ?? [])]);
      setTitle("");
    } catch (cause) {
      setError(messageOf(cause, t("evidence.create_failed")));
    } finally {
      setCreating(false);
    }
  }

  async function remove(one: Evidence) {
    if (
      !window.confirm(
        t("evidence.delete_confirm", { title: one.title }),
      )
    ) {
      return;
    }

    setError(null);
    try {
      await deleteEvidence(one.id);
      forgetEvidence(one.id);
      setEvidence((current) =>
        (current ?? []).filter((each) => each.id !== one.id),
      );
    } catch (cause) {
      setError(messageOf(cause, t("common.delete_failed")));
    }
  }

  return (
    <PageLayout
      fixedHeader={
        <>
          <form onSubmit={(event) => void create(event)} className="flex items-center gap-2.5">
            <input
              type="text"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder={t("evidence.create_placeholder")}
              className="field-input"
            />
            <button
              type="submit"
              disabled={creating || title.trim() === ""}
              className="btn-primary shrink-0"
            >
              {creating ? t("common.creating") : t("evidence.create_button")}
            </button>
          </form>

          {error !== null && (
            <p className="text-xs" style={{ color: "var(--danger)" }}>
              {error}
            </p>
          )}
        </>
      }
    >
      {evidence.length === 0 ? (
        <p className="py-8 text-center text-[13px]" style={{ color: "var(--text-faint)" }}>
          {loading ? t("common.loading") : t("evidence.empty_state")}
        </p>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {evidence.map((one) => (
            <li key={one.id} className="card group flex items-center justify-between gap-3 px-4 py-2.5">
              <Link to={`/evidence/${one.id}`} className="min-w-0 flex-1 truncate text-[13.5px] hover:underline">
                {one.title}
              </Link>
              <span className="shrink-0 text-xs" style={{ color: "var(--text-faint)" }}>
                {t("evidence.case_count_with_time", {
                  count: one.case_count,
                  time: formatTime(one.created_at),
                })}
              </span>
              <button
                type="button"
                onClick={() => void remove(one)}
                className="icon-btn icon-btn-danger shrink-0 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100"
                title={t("common.delete")}
              >
                <TrashIcon />
              </button>
            </li>
          ))}
        </ul>
      )}
    </PageLayout>
  );
}
