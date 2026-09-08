import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";

import { messageOf } from "../../shared/api";
import { useLoad } from "../../shared/useLoad";
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

export function BookmarkPage() {
  const {
    value: loaded,
    setValue: setLoaded,
    loading,
    error,
    setError,
  } = useLoad<BookmarkListResponse>(() => listBookmarks());

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
      setError(messageOf(cause, "刷新书签失败"));
    }
  }, [setLoaded, setError]);

  const handleRegister = useCallback(
    async (payload: BookmarkCreatePayload) => {
      const created = await createBookmark(payload);
      await refreshList();
      setError(null);
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
        await refreshList();
      } catch (cause) {
        setGroupError(messageOf(cause, "创建组失败"));
      } finally {
        setCreatingGroup(false);
      }
    },
    [newGroupName, creatingGroup, refreshList],
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

  const handleMoveGroup = useCallback(
    async (id: number, to: MoveDirection) => {
      const reordered = await moveBookmarkGroup(id, to);
      setLoaded((curr) =>
        curr
          ? {
              ...curr,
              groups: reordered,
            }
          : null,
      );
    },
    [setLoaded],
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

  const handleMoveBookmark = useCallback(
    async (id: number, to: MoveDirection) => {
      await moveBookmark(id, to);
      await refreshList();
    },
    [refreshList],
  );

  const handleOpenBookmark = useCallback(async (id: number) => {
    try {
      await openBookmark(id);
      setNotice(null);
    } catch (cause) {
      setNotice({
        type: "info",
        message: messageOf(cause, "打开失败"),
      });
    }
  }, []);

  const handleRevealBookmark = useCallback(async (id: number) => {
    try {
      await revealBookmark(id);
      setNotice(null);
    } catch (cause) {
      setNotice({
        type: "info",
        message: messageOf(cause, "定位文件失败"),
      });
    }
  }, []);

  const handleOpenGroup = useCallback(async (id: number) => {
    try {
      const result = await openBookmarkGroup(id);
      if (result.skipped.length === 0) {
        setNotice({
          type: "success",
          message: `已打开全部 ${result.opened.length} 个书签`,
        });
      } else {
        setNotice({
          type: "warning",
          message: `已打开 ${result.opened.length} 个书签，跳过 ${result.skipped.length} 个失效项：`,
          details: result.skipped.map(
            (s) => `「${s.name}」: ${s.reason} (${s.path})`,
          ),
        });
      }
    } catch (cause) {
      setNotice({
        type: "info",
        message: messageOf(cause, "一键打开失败"),
      });
    }
  }, []);

  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-6 px-6 py-6">
      <BookmarkForm groups={groups} onRegister={handleRegister} />

      {/* New Group form */}
      <div className="flex flex-col gap-1.5 rounded-lg border border-slate-200 bg-white p-3 shadow-xs">
        <form
          onSubmit={(e) => void handleCreateGroup(e)}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
            placeholder="新建组 (例如: 每日必开、项目工程)"
            className="min-w-0 flex-1 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-300"
          />
          <button
            type="submit"
            disabled={creatingGroup || newGroupName.trim() === ""}
            className="cursor-pointer shrink-0 rounded-md bg-slate-800 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {creatingGroup ? "创建中…" : "新建组"}
          </button>
        </form>
        {groupError !== null && (
          <p className="text-xs text-red-600">{groupError}</p>
        )}
      </div>

      {notice !== null && (
        <div
          className={`flex items-start justify-between gap-3 rounded-lg border p-3 text-xs ${
            notice.type === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : notice.type === "warning"
                ? "border-amber-200 bg-amber-50 text-amber-800"
                : "border-blue-200 bg-blue-50 text-blue-800"
          }`}
        >
          <div className="flex flex-col gap-1">
            <span className="font-medium">{notice.message}</span>
            {notice.details && notice.details.length > 0 && (
              <ul className="list-disc space-y-0.5 pl-4 text-slate-600">
                {notice.details.map((d, i) => (
                  <li key={i}>{d}</li>
                ))}
              </ul>
            )}
          </div>
          <button
            type="button"
            onClick={() => setNotice(null)}
            className="cursor-pointer text-slate-400 hover:text-slate-700"
          >
            ✕
          </button>
        </div>
      )}

      {error !== null && <p className="text-xs text-red-600">{error}</p>}

      {!hasItems ? (
        <p className="py-8 text-center text-sm text-slate-400">
          {loading ? "载入中…" : "还没有书签。在上方粘贴路径登记第一个。"}
        </p>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="flex items-center justify-between px-1 text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <span>
                共 {groups.reduce((acc, g) => acc + g.bookmarks.length, 0) + loose.length} 个书签
              </span>
              {(() => {
                const all = [...groups.flatMap((g) => g.bookmarks), ...loose];
                const staleCount = all.filter((b) => statusMap[b.id] === "stale").length;
                return staleCount > 0 ? (
                  <span className="rounded border border-rose-200 bg-rose-50 px-1.5 py-0.5 text-[11px] font-medium text-rose-700">
                    {staleCount} 个失效
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
              className="cursor-pointer text-xs text-slate-500 hover:text-slate-800 disabled:opacity-50"
            >
              {checking ? "⏳ 检查中…" : "🔄 重新检查"}
            </button>
          </div>

          {/* Groups list */}
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
              onOpenBookmark={handleOpenBookmark}
              onRevealBookmark={handleRevealBookmark}
            />
          ))}

          {/* Loose bookmarks section */}
          <section className="flex flex-col gap-2 rounded-lg border border-slate-200/90 bg-slate-50/50 p-3.5">
            <div className="flex items-center justify-between border-b border-slate-200/70 pb-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-700">📌</span>
                <h2 className="text-sm font-semibold text-slate-800">散装书签</h2>
                <span className="text-xs text-slate-400">({loose.length})</span>
              </div>
            </div>

            {loose.length === 0 ? (
              <p className="py-4 text-center text-xs text-slate-400">
                暂无散装书签。
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
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
              </ul>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
