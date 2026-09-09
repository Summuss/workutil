import {
  closestCenter,
  pointerWithin,
  useDroppable,
  type Active,
  type CollisionDetection,
  type DragCancelEvent,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { arrayMove } from "@dnd-kit/sortable";

import { messageOf } from "../../shared/api";
import { SortableContainer, SortableSubList } from "../../shared/sortable";
import { useLoad } from "../../shared/useLoad";
import { DragHandleIcon, FolderIcon, PlusIcon, XIcon } from "../../shared/icons";
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
  Bookmark,
  BookmarkCheckItem,
  BookmarkCreatePayload,
  BookmarkGroup,
  BookmarkListResponse,
  BookmarkStatus,
  BookmarkUpdatePayload,
  MoveDirection,
} from "./types";

/** Where a bookmark currently sits: its group (`null` for loose) and the
 * sibling list it belongs to. `handleDragEnd` and `handleMoveBookmark` both
 * need to resolve this from just an id before they can compute a target
 * index, so it lives in one place instead of being re-derived twice. */
function locateBookmark(
  loaded: BookmarkListResponse,
  bookmarkId: number,
): { groupId: number | null; siblings: Bookmark[] } | null {
  if (loaded.loose.some((b) => b.id === bookmarkId)) {
    return { groupId: null, siblings: loaded.loose };
  }
  const group = loaded.groups.find((g) =>
    g.bookmarks.some((b) => b.id === bookmarkId),
  );
  return group ? { groupId: group.id, siblings: group.bookmarks } : null;
}

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

interface LooseSectionProps {
  loose: Bookmark[];
  groups: BookmarkGroup[];
  getStatus: (id: number) => BookmarkStatus;
  isDraggingBookmark: boolean;
  onUpdateBookmark: (id: number, payload: BookmarkUpdatePayload) => Promise<void>;
  onDeleteBookmark: (id: number) => Promise<void>;
  onMoveBookmark: (id: number, to: MoveDirection) => Promise<void>;
  onOpenBookmark: (id: number) => Promise<void>;
  onRevealBookmark: (id: number) => Promise<void>;
}

function LooseSection({
  loose,
  groups,
  getStatus,
  isDraggingBookmark,
  onUpdateBookmark,
  onDeleteBookmark,
  onMoveBookmark,
  onOpenBookmark,
  onRevealBookmark,
}: LooseSectionProps) {
  const { t } = useI18n();
  const { setNodeRef: setLooseDroppableRef, isOver: isOverLoose } = useDroppable({
    id: "loose-droppable",
    data: {
      type: "container",
      groupId: null,
    },
  });

  return (
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
        <div
          ref={setLooseDroppableRef}
          className="rounded-md border border-dashed py-4 text-center text-xs transition-colors"
          style={{
            borderColor: isOverLoose ? "var(--accent)" : "var(--border-strong)",
            background: isOverLoose ? "var(--accent-tint)" : "transparent",
            color: isOverLoose ? "var(--accent)" : "var(--text-faint)",
          }}
        >
          {isDraggingBookmark ? t("bookmark.drop_here") : t("bookmark.loose_empty")}
        </div>
      ) : (
        <div ref={setLooseDroppableRef}>
          <SortableSubList
            as="ul"
            className="flex flex-col gap-1.5"
            id="loose-list"
            items={loose}
          >
            {loose.map((bookmark, idx) => (
              <BookmarkItem
                key={bookmark.id}
                bookmark={bookmark}
                status={getStatus(bookmark.id)}
                groups={groups}
                at={idx}
                count={loose.length}
                onUpdate={onUpdateBookmark}
                onDelete={onDeleteBookmark}
                onMove={onMoveBookmark}
                onOpen={onOpenBookmark}
                onReveal={onRevealBookmark}
              />
            ))}
          </SortableSubList>
        </div>
      )}
    </section>
  );
}

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

  const [activeType, setActiveType] = useState<"group" | "bookmark" | null>(null);

  const customCollisionDetection: CollisionDetection = useCallback((args) => {
    const currentActiveType = args.active.data.current?.type;

    if (currentActiveType === "group") {
      const groupContainers = args.droppableContainers.filter(
        (c) => c.data.current?.type === "group",
      );
      return closestCenter({
        ...args,
        droppableContainers: groupContainers,
      });
    }

    if (currentActiveType === "bookmark") {
      const bookmarkContainers = args.droppableContainers.filter(
        (c) => c.data.current?.type !== "group",
      );
      const pointerCollisions = pointerWithin({
        ...args,
        droppableContainers: bookmarkContainers,
      });
      if (pointerCollisions.length > 0) {
        const bookmarkMatch = pointerCollisions.find(
          (c) => c.data?.droppableContainer?.data?.current?.type === "bookmark",
        );
        return bookmarkMatch ? [bookmarkMatch] : pointerCollisions;
      }
      return closestCenter({
        ...args,
        droppableContainers: bookmarkContainers,
      });
    }

    return closestCenter(args);
  }, []);

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const type = event.active.data.current?.type as "group" | "bookmark" | undefined;
    setActiveType(type ?? null);
  }, []);

  const handleDragCancel = useCallback((_event: DragCancelEvent) => {
    setActiveType(null);
  }, []);

  const performMoveBookmark = useCallback(
    async (
      bookmarkId: number,
      sourceGroupId: number | null,
      targetGroupId: number | null,
      oldIndex: number,
      targetIndex: number,
    ) => {
      const prev = loaded;
      if (!prev) return;
      setError(null);

      // Same group: a plain reorder, applied optimistically before the request lands.
      if (sourceGroupId === targetGroupId) {
        if (sourceGroupId === null) {
          const reorderedOptimistic = arrayMove(prev.loose, oldIndex, targetIndex).map(
            (item, idx) => ({ ...item, order: idx }),
          );
          setLoaded({
            ...prev,
            loose: reorderedOptimistic,
          });
        } else {
          const group = prev.groups.find((g) => g.id === sourceGroupId);
          if (!group) return;
          const reorderedOptimistic = arrayMove(group.bookmarks, oldIndex, targetIndex).map(
            (item, idx) => ({ ...item, order: idx }),
          );
          setLoaded({
            ...prev,
            groups: prev.groups.map((g) =>
              g.id === sourceGroupId ? { ...g, bookmarks: reorderedOptimistic } : g,
            ),
          });
        }
      } else {
        // Different groups: move it locally too — group_id changes, it leaves
        // one array and is spliced into the other — so the UI doesn't sit
        // still until the round trip below returns.
        const movingBookmark =
          sourceGroupId === null
            ? prev.loose.find((b) => b.id === bookmarkId)
            : prev.groups
                .find((g) => g.id === sourceGroupId)
                ?.bookmarks.find((b) => b.id === bookmarkId);
        if (!movingBookmark) return;

        const updatedMoving = {
          ...movingBookmark,
          group_id: targetGroupId,
        };

        let nextLoose = prev.loose;
        let nextGroups = prev.groups;

        if (sourceGroupId === null) {
          nextLoose = prev.loose
            .filter((b) => b.id !== bookmarkId)
            .map((b, idx) => ({ ...b, order: idx }));
        } else {
          nextGroups = nextGroups.map((g) => {
            if (g.id !== sourceGroupId) return g;
            return {
              ...g,
              bookmarks: g.bookmarks
                .filter((b) => b.id !== bookmarkId)
                .map((b, idx) => ({ ...b, order: idx })),
            };
          });
        }

        if (targetGroupId === null) {
          const clamped = Math.max(0, Math.min(targetIndex, nextLoose.length));
          const newLoose = [...nextLoose];
          newLoose.splice(clamped, 0, updatedMoving);
          nextLoose = newLoose.map((b, idx) => ({ ...b, order: idx }));
        } else {
          nextGroups = nextGroups.map((g) => {
            if (g.id !== targetGroupId) return g;
            const clamped = Math.max(0, Math.min(targetIndex, g.bookmarks.length));
            const newBookmarks = [...g.bookmarks];
            newBookmarks.splice(clamped, 0, updatedMoving);
            return {
              ...g,
              bookmarks: newBookmarks.map((b, idx) => ({ ...b, order: idx })),
            };
          });
        }

        setLoaded({
          ...prev,
          groups: nextGroups,
          loose: nextLoose,
        });
      }

      // Both branches above are just a preview — confirm with the backend's
      // atomic move endpoint, which also collapses the gap left behind in
      // the source group (spec: bookmark-cross-group-drag ticket 01).
      try {
        const res = await moveBookmark(bookmarkId, targetIndex, targetGroupId);
        setLoaded((curr) => {
          if (!curr) return null;
          let nextGroups = curr.groups;
          let nextLoose = curr.loose;

          if (res.source_group_id === null) {
            nextLoose = res.source;
          } else {
            nextGroups = nextGroups.map((g) =>
              g.id === res.source_group_id ? { ...g, bookmarks: res.source } : g,
            );
          }

          if (res.target_group_id === null) {
            nextLoose = res.target;
          } else {
            nextGroups = nextGroups.map((g) =>
              g.id === res.target_group_id ? { ...g, bookmarks: res.target } : g,
            );
          }

          return {
            ...curr,
            groups: nextGroups,
            loose: nextLoose,
          };
        });
      } catch (cause) {
        setLoaded(prev);
        setError(messageOf(cause, t("bookmark.move_failed")));
      }
    },
    [loaded, setLoaded, t, setError],
  );

  const handleDragEnd = useCallback(
    async (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveType(null);

      if (!over) return;
      const currentActiveType = active.data.current?.type;

      // Dragging a group: reorder among groups only.
      if (currentActiveType === "group") {
        if (active.id === over.id) return;
        const overGroupId = over.data.current?.id ?? over.id;
        const oldIndex = (loaded?.groups ?? []).findIndex(
          (g) => String(g.id) === String(active.id),
        );
        const newIndex = (loaded?.groups ?? []).findIndex(
          (g) => String(g.id) === String(overGroupId),
        );
        if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
          await handleReorderGroup(Number(active.id), newIndex);
        }
        return;
      }

      // Dragging a bookmark: same-group reorder or a cross-group move,
      // depending on where the drop landed.
      if (currentActiveType === "bookmark") {
        const bookmarkId = Number(active.id);
        const prev = loaded;
        if (!prev) return;

        const source = locateBookmark(prev, bookmarkId);
        if (!source) return;
        const sourceGroupId = source.groupId;

        let targetGroupId: number | null = null;
        let targetIndex = 0;

        const overData = over.data.current;

        if (overData?.type === "container") {
          targetGroupId = overData.groupId ?? null;
          const targetList =
            targetGroupId === null
              ? prev.loose
              : (prev.groups.find((g) => g.id === targetGroupId)?.bookmarks ?? []);
          targetIndex = targetList.length;
        } else if (overData?.type === "bookmark") {
          const overBookmarkId = Number(over.id);
          const target = locateBookmark(prev, overBookmarkId);
          if (!target) return;
          targetGroupId = target.groupId;

          const overIdx = target.siblings.findIndex((b) => b.id === overBookmarkId);
          targetIndex = overIdx === -1 ? target.siblings.length : overIdx;
        } else {
          return;
        }

        const isSameGroup = sourceGroupId === targetGroupId;
        const oldIndex = source.siblings.findIndex((b) => b.id === bookmarkId);

        if (isSameGroup && oldIndex === targetIndex) {
          return;
        }

        await performMoveBookmark(
          bookmarkId,
          sourceGroupId,
          targetGroupId,
          oldIndex,
          targetIndex,
        );
      }
    },
    [loaded, handleReorderGroup, performMoveBookmark],
  );

  const handleMoveBookmark = useCallback(
    async (id: number, to: MoveDirection) => {
      const prev = loaded;
      if (!prev) return;

      const location = locateBookmark(prev, id);
      if (!location) return;
      const { groupId, siblings } = location;
      const oldIndex = siblings.findIndex((b) => b.id === id);
      if (oldIndex === -1) return;

      const targetIndex =
        typeof to === "number"
          ? to
          : to === "top"
            ? 0
            : siblings.length - 1;
      return performMoveBookmark(id, groupId, groupId, oldIndex, targetIndex);
    },
    [loaded, performMoveBookmark],
  );

  const renderOverlay = useCallback(
    (active: Active) => {
      const type = active.data.current?.type;
      if (type === "group") {
        const group = (loaded?.groups ?? []).find((g) => g.id === Number(active.id));
        if (!group) return null;
        return (
          <div className="card flex items-center gap-2.5 p-3 shadow-2xl opacity-95 bg-[var(--surface)] border border-[var(--border-strong)] rounded-lg min-w-[280px]">
            <FolderIcon />
            <span className="font-medium text-sm">{group.name}</span>
            <span className="text-xs text-[var(--text-faint)]">
              ({group.bookmarks.length})
            </span>
          </div>
        );
      }
      if (type === "bookmark") {
        const all = [
          ...(loaded?.groups ?? []).flatMap((g) => g.bookmarks),
          ...(loaded?.loose ?? []),
        ];
        const bookmark = all.find((b) => b.id === Number(active.id));
        if (!bookmark) return null;
        return (
          <div className="card flex items-center gap-2.5 p-2.5 shadow-2xl opacity-95 bg-[var(--surface)] border border-[var(--border-strong)] rounded-lg min-w-[260px]">
            <DragHandleIcon size={12} className="opacity-40" />
            <span className="font-medium text-xs">{bookmark.name}</span>
            <span className="text-[11px] text-[var(--text-faint)] truncate max-w-[200px]">
              {bookmark.path}
            </span>
          </div>
        );
      }
      return null;
    },
    [loaded],
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

          {(notice !== null || error !== null) && (
            <div className="relative w-full h-0 z-20 pointer-events-none">
              <div className="absolute top-2 left-0 right-0 flex flex-col gap-2 pointer-events-auto">
                {notice !== null && (
                  <div
                    className="flex items-start justify-between gap-3 rounded-lg p-3 text-xs shadow-lg"
                    style={{
                      border: `1px solid ${NOTICE_STYLE[notice.type].border}`,
                      background: NOTICE_STYLE[notice.type].bg,
                      color: NOTICE_STYLE[notice.type].color,
                    }}
                  >
                    <div className="flex flex-col gap-1 min-w-0 flex-1">
                      <span className="font-medium">{notice.message}</span>
                      {notice.details && notice.details.length > 0 && (
                        <ul
                          className="list-disc space-y-0.5 pl-4 max-h-48 overflow-y-auto"
                          style={{ color: "var(--text-muted)" }}
                        >
                          {notice.details.map((d, i) => (
                            <li key={i}>{d}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => setNotice(null)}
                      className="icon-btn shrink-0 cursor-pointer"
                    >
                      <XIcon size={11} />
                    </button>
                  </div>
                )}

                {error !== null && (
                  <div
                    className="flex items-center justify-between gap-2 rounded-lg p-3 text-xs shadow-lg"
                    style={{
                      border: "1px solid var(--danger-tint)",
                      background: "var(--danger-tint)",
                      color: "var(--danger)",
                    }}
                  >
                    <span className="min-w-0 flex-1">{error}</span>
                    <button
                      type="button"
                      onClick={() => setError(null)}
                      className="icon-btn shrink-0 cursor-pointer"
                    >
                      <XIcon size={11} />
                    </button>
                  </div>
                )}
              </div>
            </div>
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

          <SortableContainer
            collisionDetection={customCollisionDetection}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            onDragCancel={handleDragCancel}
            renderOverlay={renderOverlay}
          >
            {/* Groups list */}
            <SortableSubList
              id="groups-list"
              items={groups}
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
                  isDraggingBookmark={activeType === "bookmark"}
                  onRenameGroup={handleRenameGroup}
                  onDeleteGroup={handleDeleteGroup}
                  onMoveGroup={handleMoveGroup}
                  onOpenGroup={handleOpenGroup}
                  onUpdateBookmark={handleUpdateBookmark}
                  onDeleteBookmark={handleDeleteBookmark}
                  onMoveBookmark={handleMoveBookmark}
                  onOpenBookmark={handleOpenBookmark}
                  onRevealBookmark={handleRevealBookmark}
                />
              ))}
            </SortableSubList>

            {/* Loose bookmarks section */}
            <LooseSection
              loose={loose}
              groups={groups}
              getStatus={getStatus}
              isDraggingBookmark={activeType === "bookmark"}
              onUpdateBookmark={handleUpdateBookmark}
              onDeleteBookmark={handleDeleteBookmark}
              onMoveBookmark={handleMoveBookmark}
              onOpenBookmark={handleOpenBookmark}
              onRevealBookmark={handleRevealBookmark}
            />
          </SortableContainer>
        </div>
      )}
    </PageLayout>
  );
}
