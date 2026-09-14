import { BrowserRouter, Navigate, Route, Routes } from "react-router";

import { AppNav } from "./AppNav";
import { BookmarkPage } from "./features/bookmark/BookmarkPage";
import { EvidenceDetailPage } from "./features/evidence/EvidenceDetailPage";
import { EvidenceListPage } from "./features/evidence/EvidenceListPage";
import { MemoPage } from "./features/memo/MemoPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { SingleMemoPage } from "./features/memo/SingleMemoPage";
import { TodoPage } from "./features/todo/TodoPage";
import { I18nProvider } from "./shared/i18n";

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
    <I18nProvider>
      <BrowserRouter>
        <div className="flex h-dvh overflow-hidden flex-col" style={{ background: "var(--bg)", color: "var(--text)" }}>
          <AppNav />
          <Routes>
            <Route path="/" element={<MemoPage />} />
            <Route path="/memo/:id" element={<SingleMemoPage />} />
            <Route path="/evidence" element={<EvidenceListPage />} />
            <Route path="/evidence/:evidenceId" element={<EvidenceDetailPage />} />
            <Route path="/evidence/:evidenceId/cases/:caseId" element={<EvidenceDetailPage />} />
            <Route path="/bookmarks" element={<BookmarkPage />} />
            <Route path="/todos" element={<TodoPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            {/* A mistyped URL lands on the thing you open this tool for. */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </BrowserRouter>
    </I18nProvider>
  );
}

