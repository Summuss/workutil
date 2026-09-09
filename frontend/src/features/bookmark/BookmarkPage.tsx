import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { arrayMove } from "@dnd-kit/sortable";

import { messageOf } from "../../shared/api";
import { SortableList } from "../../shared/sortable";
import { useLoad } from "../../shared/useLoad";
import { PlusIcon, XIcon } from "../../shared/icons";
import { PageLayout } from "../../shared/PageLayout";
import {
  checkBookmarks,
  createBookmark,
  createBookmarkGroup,
  deleteBookmark,
  deleteBookmarkGroup,
  listBookmarks,
  moveBookmark,
  moveBookmarkGroup,
  openBookmark,
  openBookmarkGroup,
  revealBookmark,
  updateBookmark,
  updateBookmarkGroup,
} from "./api";
import { BookmarkForm } from "./BookmarkForm";
import { BookmarkGroupSection } from "./BookmarkGroupSection";
import { BookmarkItem } from "./BookmarkItem";
import { useI18n } from "../../shared/i18n";
import type {
  BookmarkCheckItem,
  BookmarkCreatePayload,
  BookmarkListResponse,
  BookmarkStatus,
  BookmarkUpdatePayload,
  MoveDirection,
} from "./types";

interface Notice {
  type: "info" | "success" | "warning";
  message: string;
  details?: string[];
}

const NOTICE_STYLE: Record<Notice["type"], { border: string; bg: string; color: string }> = {
  success: { border: "var(--success)", bg: "var(--success-tint)", color: "var(--success)" },
  warning: { border: "var(--warn)", bg: "var(--warn-tint)", color: "var(--warn)" },
  info: { border: "var(--accent)", bg: "var(--accent-tint)", color: "var(--accent-strong)" },
};

export function BookmarkPage() {
  const { t } = useI18n();
  const {
    value: loaded,
    setValue: setLoaded,
    loading,
    error,
    setError,
  } = useLoad<BookmarkListResponse>(() => listBookmarks());

  const [showAddForm, setShowAddForm] = useState(false);
  const [showNewGroupForm, setShowNewGroupForm] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");
  const [creatingGroup, setCreatingGroup] = useState(false);
  const [groupError, setGroupError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [statusMap, setStatusMap] = useState<Record<number, BookmarkStatus>>({});
  const [checking, setChecking] = useState(false);
  const didInitialCheckRef = useRef(false);
  //: ids currently on screen, kept fresh by the effect below — read by
  //: runCheck() so a full check can stamp every id it covers without making
  //: runCheck itself depend on (and be re-created by) `groups`/`loose`.
  const knownIdsRef = useRef<number[]>([]);
  //: The sequence number most recently issued for each bookmark id. Lets a
  //: response recognize a newer check for the same id was issued after it
  //: (e.g. a fast targeted checkOne racing a slow full check on a network
  //: drive) and drop itself instead of overwriting fresher data — last
  //: issued wins, not last to answer.
  const lastIssuedRef = useRef<Record<number, number>>({});
  const nextSeqRef = useRef(0);

  const groups = loaded?.groups ?? [];
  const loose = loaded?.loose ?? [];
  const hasItems = groups.length > 0 || loose.length > 0;

  useEffect(() => {
    knownIdsRef.current = [...groups.flatMap((g) => g.bookmarks), ...loose].map(
      (b) => b.id,
    );
  }, [groups, loose]);

  const getStatus = useCallback(
    (id: number): BookmarkStatus => statusMap[id] ?? "unknown",
    [statusMap],
  );

  const applyCheckResults = useCallback(
    (items: BookmarkCheckItem[], issuedAt: Record<number, number>) => {
      setStatusMap((prev) => {
        const next = { ...prev };
        for (const item of items) {
          if (lastIssuedRef.current[item.id] === issuedAt[item.id]) {
            next[item.id] = item.exists ? "valid" : "stale";
          }
        }
        return next;
      });
    },
    [],
  );

  // Full check: every bookmark currently on screen. Only for first load and
  // the manual "重新检查" button — routine edits use checkOne below, because
  // re-verifying everything on every click is exactly the stall ticket 05's
  // separate endpoint exists to avoid (a broken network drive can take
  // seconds, and it would flash every badge back to "unknown" each time).
  const runCheck = useCallback(async () => {
    setChecking(true);
    const issuedAt: Record<number, number> = {};
    for (const id of knownIdsRef.current) {
      issuedAt[id] = ++nextSeqRef.current;
      lastIssuedRef.current[id] = issuedAt[id];
    }
    try {
      const res = await checkBookmarks();
      applyCheckResults(res.items, issuedAt);
    } catch {
      // Non-blocking: existence check failure does not block list usage
    } finally {
      setChecking(false);
    }
  }, [applyCheckResults]);

  // Targeted check: the one bookmark a register/edit could actually affect.
  const checkOne = useCallback(
    async (id: number) => {
      const seq = ++nextSeqRef.current;
      lastIssuedRef.current[id] = seq;
      try {
        const res = await checkBookmarks([id]);
        applyCheckResults(res.items, { [id]: seq });
      } catch {
        // Non-blocking; the badge just stays at its last known state.
      }
    },
    [applyCheckResults],
  );

  useEffect(() => {
    if (loaded !== null && !didInitialCheckRef.current) {
      didInitialCheckRef.current = true;
      void runCheck();
    }
  }, [loaded, runCheck]);

  // Refetch the list alone — for actions (reordering, renaming, regrouping,
  // deleting a group) that cannot change whether any path exists on disk,
  // so there is nothing here for a status check to tell us.
  const refreshList = useCallback(async () => {
    try {
      const data = await listBookmarks();
      setLoaded(data);
    } catch (cause) {
      setError(messageOf(cause, t("bookmark.refresh_failed")));
    }
  }, [setLoaded, setError, t]);

  const handleRegister = useCallback(
    async (payload: BookmarkCreatePayload) => {
      const created = await createBookmark(payload);
      await refreshList();
      setError(null);
      setShowAddForm(false);
      void checkOne(created.id);
    },
    [refreshList, setError, checkOne],
  );

  const handleCreateGroup = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const cleanName = newGroupName.trim();
      if (!cleanName || creatingGroup) return;

      setCreatingGroup(true);
      setGroupError(null);
      try {
        await createBookmarkGroup({ name: cleanName });
        setNewGroupName("");
        setShowNewGroupForm(false);
        await refreshList();
      } catch (cause) {
        setGroupError(messageOf(cause, t("bookmark.create_group_failed")));
      } finally {
        setCreatingGroup(false);
      }
    },
    [newGroupName, creatingGroup, refreshList, t],
  );

  const handleRenameGroup = useCallback(
    async (id: number, name: string) => {
      const updated = await updateBookmarkGroup(id, { name });
      setLoaded((curr) =>
        curr
          ? {
              ...curr,
              groups: curr.groups.map((g) =>
                g.id === id ? { ...g, name: updated.name } : g,
              ),
            }
          : null,
      );
    },
    [setLoaded],
  );

  const handleDeleteGroup = useCallback(
    async (id: number) => {
      await deleteBookmarkGroup(id);
      await refreshList();
    },
    [refreshList],
  );

  const handleReorderGroup = useCallback(
    async (id: number | string, targetIndex: number) => {
      const groupId = Number(id);
      setError(null);
      const prev = loaded;
      if (!prev) return;

      const oldIndex = prev.groups.findIndex((g) => g.id === groupId);
      if (oldIndex === -1 || oldIndex === targetIndex) return;

      const reorderedOptimistic = arrayMove(prev.groups, oldIndex, targetIndex).map(
        (group, idx) => ({ ...group, order: idx }),
      );

      setLoaded({
        ...prev,
        groups: reorderedOptimistic,
      });

      try {
        const reordered = await moveBookmarkGroup(groupId, targetIndex);
        setLoaded((curr) => (curr ? { ...curr, groups: reordered } : null));
      } catch (cause) {
        setLoaded(prev);
        setError(messageOf(cause, t("bookmark.move_group_failed")));
      }
    },
    [loaded, setLoaded, t],
  );

  const handleMoveGroup = useCallback(
    (id: number, to: MoveDirection) => {
      if (typeof to === "number") return handleReorderGroup(id, to);
      const targetIndex = to === "top" ? 0 : (loaded?.groups.length ?? 1) - 1;
      return handleReorderGroup(id, targetIndex);
    },
    [loaded, handleReorderGroup],
  );

  const handleUpdateBookmark = useCallback(
    async (id: number, payload: BookmarkUpdatePayload) => {
      await updateBookmark(id, payload);
      await refreshList();
      void checkOne(id);
    },
    [refreshList, checkOne],
  );

  const handleDeleteBookmark = useCallback(
    async (id: number) => {
      await deleteBookmark(id);
      await refreshList();
      setStatusMap((prev) => {
        if (!(id in prev)) return prev;
        const next = { ...prev };
        delete next[id];
        return next;
      });
    },
    [refreshList],
  );

  const handleReorderBookmark = useCallback(
    async (groupId: number | null, id: number | string, targetIndex: number) => {
      const bookmarkId = Number(id);
      setError(null);
      const prev = loaded;
      if (!prev) return;

      if (groupId === null) {
        const oldIndex = prev.loose.findIndex((b) => b.id === bookmarkId);
        if (oldIndex === -1 || oldIndex === targetIndex) return;

        const reorderedOptimistic = arrayMove(prev.loose, oldIndex, targetIndex).map(
          (item, idx) => ({ ...item, order: idx }),
        );
        setLoaded({
          ...prev,
          loose: reorderedOptimistic,
        });

        try {
          const reordered = await moveBookmark(bookmarkId, targetIndex);
          setLoaded((curr) => (curr ? { ...curr, loose: reordered } : null));
        } catch (cause) {
          setLoaded(prev);
          setError(messageOf(cause, t("bookmark.move_failed")));
        }
      } else {
        const group = prev.groups.find((g) => g.id === groupId);
        if (!group) return;

        const oldIndex = group.bookmarks.findIndex((b) => b.id === bookmarkId);
        if (oldIndex === -1 || oldIndex === targetIndex) return;

        const reorderedOptimistic = arrayMove(group.bookmarks, oldIndex, targetIndex).map(
          (item, idx) => ({ ...item, order: idx }),
        );

        setLoaded({
          ...prev,
          groups: prev.groups.map((g) =>
            g.id === groupId ? { ...g, bookmarks: reorderedOptimistic } : g,
          ),
        });

        try {
          const reordered = await moveBookmark(bookmarkId, targetIndex);
          setLoaded((curr) =>
            curr
              ? {
                  ...curr,
                  groups: curr.groups.map((g) =>
                    g.id === groupId ? { ...g, bookmarks: reordered } : g,
                  ),
                }
              : null,
          );
        } catch (cause) {
          setLoaded(prev);
          setError(messageOf(cause, t("bookmark.move_failed")));
        }
      }
    },
    [loaded, setLoaded, t],
  );

  const handleMoveBookmark = useCallback(
    async (id: number, to: MoveDirection) => {
      const prev = loaded;
      if (!prev) return;

      const inLoose = prev.loose.some((b) => b.id === id);
      const group = inLoose
        ? null
        : prev.groups.find((g) => g.bookmarks.some((b) => b.id === id));
      if (!inLoose && !group) return;

      const groupId = group?.id ?? null;
      if (typeof to === "number") {
        return handleReorderBookmark(groupId, id, to);
      }

      const siblings = inLoose ? prev.loose : (group?.bookmarks ?? []);
      const targetIndex = to === "top" ? 0 : siblings.length - 1;
      return handleReorderBookmark(groupId, id, targetIndex);
    },
    [loaded, handleReorderBookmark],
  );

  const handleOpenBookmark = useCallback(async (id: number) => {
    try {
      await openBookmark(id);
      setNotice(null);
    } catch (cause) {
      setNotice({
        type: "info",
        message: messageOf(cause, t("bookmark.open_failed")),
      });
    }
  }, [t]);

  const handleRevealBookmark = useCallback(async (id: number) => {
    try {
      await revealBookmark(id);
      setNotice(null);
    } catch (cause) {
      setNotice({
        type: "info",
        message: messageOf(cause, t("bookmark.reveal_failed")),
      });
    }
  }, [t]);

  const handleOpenGroup = useCallback(async (id: number) => {
    try {
      const result = await openBookmarkGroup(id);
      if (result.skipped.length === 0) {
        setNotice({
          type: "success",
          message: t("bookmark.opened_all", { count: result.opened.length }),
        });
      } else {
        setNotice({
          type: "warning",
          message: t("bookmark.opened_with_skipped", {
            opened: result.opened.length,
            skipped: result.skipped.length,
          }),
          details: result.skipped.map(
            (s) => `「${s.name}」: ${s.reason} (${s.path})`,
          ),
        });
      }
    } catch (cause) {
      setNotice({
        type: "info",
        message: messageOf(cause, t("bookmark.open_group_failed")),
      });
    }
  }, [t]);

  return (
    <PageLayout
      fixedHeader={
        <>
          <div className="flex gap-2.5">
            <button
              type="button"
              onClick={() => setShowAddForm((prev) => !prev)}
              className="btn-ghost"
            >
              <PlusIcon />
              {t("bookmark.submit_button")}
            </button>
            <button
              type="button"
              onClick={() => setShowNewGroupForm((prev) => !prev)}
              className="btn-ghost"
            >
              <PlusIcon />
              {t("bookmark.create_group_button")}
            </button>
          </div>

          {showAddForm && (
            <BookmarkForm groups={groups} onRegister={handleRegister} onCancel={() => setShowAddForm(false)} />
          )}

          {showNewGroupForm && (
            <div className="card flex items-center gap-2.5 p-3.5">
              <form
                onSubmit={(e) => void handleCreateGroup(e)}
                className="flex flex-1 items-center gap-2.5"
              >
                <input
                  type="text"
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  placeholder={t("bookmark.new_group_placeholder")}
                  autoFocus
                  className="field-input flex-1"
                />
                <button
                  type="button"
                  onClick={() => setShowNewGroupForm(false)}
                  className="btn-ghost"
                  style={{ fontSize: "12px", padding: "6px 13px", borderRadius: "6px" }}
                >
                  {t("common.cancel")}
                </button>
                <button
                  type="submit"
                  disabled={creatingGroup || newGroupName.trim() === ""}
                  className="btn-primary"
                  style={{ fontSize: "12px", padding: "6px 13px", borderRadius: "6px" }}
                >
                  {creatingGroup ? t("common.creating") : t("bookmark.create_group_button")}
                </button>
              </form>
            </div>
          )}
          {groupError !== null && (
            <p className="text-xs" style={{ color: "var(--danger)" }}>
              {groupError}
            </p>
          )}

          {notice !== null && (
            <div
              className="flex items-start justify-between gap-3 rounded-lg p-3 text-xs"
              style={{ border: `1px solid ${NOTICE_STYLE[notice.type].border}`, background: NOTICE_STYLE[notice.type].bg, color: NOTICE_STYLE[notice.type].color }}
            >
              <div className="flex flex-col gap-1">
                <span className="font-medium">{notice.message}</span>
                {notice.details && notice.details.length > 0 && (
                  <ul className="list-disc space-y-0.5 pl-4" style={{ color: "var(--text-muted)" }}>
                    {notice.details.map((d, i) => (
                      <li key={i}>{d}</li>
                    ))}
                  </ul>
                )}
              </div>
              <button type="button" onClick={() => setNotice(null)} className="icon-btn">
                <XIcon size={11} />
              </button>
            </div>
          )}

          {error !== null && (
            <p className="text-xs" style={{ color: "var(--danger)" }}>
              {error}
            </p>
          )}
        </>
      }
    >
      {!hasItems ? (
        <p className="py-8 text-center text-[13px]" style={{ color: "var(--text-faint)" }}>
          {loading ? t("common.loading") : t("bookmark.empty_state")}
        </p>
      ) : (
        <div className="flex flex-col gap-5">
          <div className="flex items-center justify-between px-1 text-xs" style={{ color: "var(--text-muted)" }}>
            <div className="flex items-center gap-2">
              <span>
                {t("bookmark.total_count", {
                  count:
                    groups.reduce((acc, g) => acc + g.bookmarks.length, 0) +
                    loose.length,
                })}
              </span>
              {(() => {
                const all = [...groups.flatMap((g) => g.bookmarks), ...loose];
                const staleCount = all.filter((b) => statusMap[b.id] === "stale").length;
                return staleCount > 0 ? (
                  <span
                    className="rounded-full px-2 py-0.5 text-[11px] font-medium"
                    style={{ border: "1px solid var(--danger-tint)", background: "var(--danger-tint)", color: "var(--danger)" }}
                  >
                    {t("bookmark.stale_count", { count: staleCount })}
                  </span>
                ) : null;
              })()}
            </div>
            <button
              type="button"
              onClick={() => {
                setStatusMap({});
                void runCheck();
              }}
              disabled={checking}
              className="text-btn"
            >
              {checking ? t("bookmark.checking") : t("bookmark.recheck")}
            </button>
          </div>

          {/* Groups list */}
          <SortableList
            items={groups}
            onReorder={handleReorderGroup}
            className="flex flex-col gap-5"
          >
            {groups.map((group, idx) => (
              <BookmarkGroupSection
                key={group.id}
                group={group}
                groups={groups}
                at={idx}
                count={groups.length}
                getStatus={getStatus}
                onRenameGroup={handleRenameGroup}
                onDeleteGroup={handleDeleteGroup}
                onMoveGroup={handleMoveGroup}
                onOpenGroup={handleOpenGroup}
                onUpdateBookmark={handleUpdateBookmark}
                onDeleteBookmark={handleDeleteBookmark}
                onMoveBookmark={handleMoveBookmark}
                onReorderBookmark={handleReorderBookmark}
                onOpenBookmark={handleOpenBookmark}
                onRevealBookmark={handleRevealBookmark}
              />
            ))}
          </SortableList>

          {/* Loose bookmarks section */}
          <section className="card flex flex-col gap-2.5 p-4">
            <div className="flex items-center justify-between pb-2" style={{ borderBottom: "1px solid var(--border)" }}>
              <div className="flex items-center gap-2">
                <h2 className="text-[13.5px] font-medium">{t("bookmark.loose_bookmarks")}</h2>
                <span className="text-xs" style={{ color: "var(--text-faint)" }}>
                  ({loose.length})
                </span>
              </div>
            </div>

            {loose.length === 0 ? (
              <p className="py-4 text-center text-xs" style={{ color: "var(--text-faint)" }}>
                {t("bookmark.loose_empty")}
              </p>
            ) : (
              <SortableList
                as="ul"
                className="flex flex-col gap-1.5"
                items={loose}
                onReorder={(id, newIndex) => handleReorderBookmark(null, id, newIndex)}
              >
                {loose.map((bookmark, idx) => (
                  <BookmarkItem
                    key={bookmark.id}
                    bookmark={bookmark}
                    status={getStatus(bookmark.id)}
                    groups={groups}
                    at={idx}
                    count={loose.length}
                    onUpdate={handleUpdateBookmark}
                    onDelete={handleDeleteBookmark}
                    onMove={handleMoveBookmark}
                    onOpen={handleOpenBookmark}
                    onReveal={handleRevealBookmark}
                  />
                ))}
              </SortableList>
            )}
          </section>
        </div>
      )}
    </PageLayout>
  );
}
