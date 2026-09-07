/**
 * Evidence lives here from ticket 03 onwards.
 *
 * For now it is the far end of the route, so that navigation, history and the
 * server-side fallback can be exercised before there is anything to navigate
 * to.
 */
export function EvidencePage() {
  return (
    <main className="mx-auto flex max-w-3xl flex-col gap-2 px-6 py-8">
      <h1 className="text-base font-semibold text-slate-900">Evidence</h1>
      <p className="text-xs text-slate-500">
        还没建好。列表、用例与导出在后续 ticket 里。
      </p>
    </main>
  );
}
