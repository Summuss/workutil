import type { ReactNode } from "react";

interface PageLayoutProps {
  /** Fixed top area (e.g. composer, search bar, creation forms) */
  fixedHeader?: ReactNode;
  /** Scrollable content area (or container when scrollable=false) */
  children: ReactNode;
  /** Fixed bottom area (optional) */
  fixedFooter?: ReactNode;
  /** Whether the middle content area should have its own overflow-y-auto (default: true) */
  scrollable?: boolean;
  className?: string;
  contentClassName?: string;
  headerClassName?: string;
  footerClassName?: string;
}

/**
 * Shared page shell ensuring a fixed single-viewport layout:
 * - Shell fills remaining height via flex-1 min-h-0 and never causes window-level scroll.
 * - fixedHeader stays pinned at the top.
 * - children scroll inside their own flex-1 min-h-0 overflow-y-auto container (or manage their own scroll when scrollable=false).
 * - Both areas share max-w-3xl and px-8 to guarantee strict horizontal alignment across pages.
 */
export function PageLayout({
  fixedHeader,
  children,
  fixedFooter,
  scrollable = true,
  className = "",
  contentClassName = "",
  headerClassName = "",
  footerClassName = "",
}: PageLayoutProps) {
  return (
    <main className={`flex flex-1 min-h-0 flex-col ${className}`}>
      {fixedHeader && (
        <div className="shrink-0 z-10" style={{ background: "var(--bg)" }}>
          <div
            className={`mx-auto flex w-full max-w-3xl flex-col gap-3.5 px-8 pt-9 pb-3.5 ${headerClassName}`}
          >
            {fixedHeader}
          </div>
        </div>
      )}

      {scrollable ? (
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div
            className={`mx-auto flex w-full max-w-3xl flex-col gap-3.5 px-8 ${
              fixedHeader ? "pt-1 pb-9" : "py-9"
            } ${contentClassName}`}
          >
            {children}
          </div>
        </div>
      ) : (
        <div className={`flex flex-1 min-h-0 flex-col ${contentClassName}`}>
          {children}
        </div>
      )}

      {fixedFooter && (
        <div className="shrink-0 z-10" style={{ background: "var(--bg)" }}>
          <div
            className={`mx-auto flex w-full max-w-3xl flex-col gap-3.5 px-8 py-3.5 ${footerClassName}`}
          >
            {fixedFooter}
          </div>
        </div>
      )}
    </main>
  );
}
