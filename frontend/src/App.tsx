import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { AppNav } from "./AppNav";
import { BookmarkPage } from "./features/bookmark/BookmarkPage";
import { EvidenceDetailPage } from "./features/evidence/EvidenceDetailPage";
import { EvidenceListPage } from "./features/evidence/EvidenceListPage";
import { MemoPage } from "./features/memo/MemoPage";
import { TodoPage } from "./features/todo/TodoPage";

/**
 * The route table.
 *
 * `/` is Memo itself, never a redirect to it: F1 claims zero navigation clicks
 * between opening workutil and having written something down
 * (requirements.md §4 F1), and a hop through `<Navigate>` costs a render and
 * blinks the focus away.
 *
 * These are real paths, not a hash (design.md §2) — which is why the server
 * needs `SinglePageApp` (design.md §3.1).
 */
export function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <AppNav />
        <Routes>
          <Route path="/" element={<MemoPage />} />
          <Route path="/evidence" element={<EvidenceListPage />} />
          <Route path="/evidence/:evidenceId" element={<EvidenceDetailPage />} />
          <Route path="/bookmarks" element={<BookmarkPage />} />
          <Route path="/todos" element={<TodoPage />} />
          {/* A mistyped URL lands on the thing you open this tool for. */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
