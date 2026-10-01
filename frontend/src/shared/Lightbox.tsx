import { useEffect, useRef } from "react";

import { useI18n } from "./i18n";
import { ChevronLeftIcon, ChevronRightIcon, XIcon } from "./icons";

interface LightboxProps {
  src: string;
  alt?: string;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
  position?: string;
  label?: string | null;
}

function isEventOnScrollbar(e: React.MouseEvent<HTMLElement>, el: HTMLElement): boolean {
  const hasVerticalScrollbar = el.scrollHeight > el.clientHeight;
  const hasHorizontalScrollbar = el.scrollWidth > el.clientWidth;
  const rect = el.getBoundingClientRect();

  if (hasVerticalScrollbar) {
    const onRightScrollbar = e.clientX >= rect.left + el.clientWidth;
    const onLeftScrollbar = e.clientX < rect.left + el.clientLeft;
    if (onRightScrollbar || onLeftScrollbar) {
      return true;
    }
  }
  if (hasHorizontalScrollbar) {
    const onBottomScrollbar = e.clientY >= rect.top + el.clientHeight;
    const onTopScrollbar = e.clientY < rect.top + el.clientTop;
    if (onBottomScrollbar || onTopScrollbar) {
      return true;
    }
  }
  return false;
}

/**
 * Lightbox displaying an image fitted to viewport width with vertical scrolling:
 * - Image width = min(natural width, viewport width - margin), height proportional, never upscaled.
 * - Taller than viewport: overlay scrolls vertically starting from the top;
 *   shorter than viewport: centered vertically.
 * - Over-scroll is contained to avoid scrolling the background page.
 * - Keyboard scroll (Up/Down/Space/PageUp/PageDown) works immediately via focused overlay.
 * - Esc key closes via document-level listener.
 * - ArrowLeft / ArrowRight step through images when onPrev/onNext are provided.
 * - Backdrop click and top-right X button close; dragging/clicking scrollbar does not close.
 */
export function Lightbox({
  src,
  alt = "",
  onClose,
  onPrev,
  onNext,
  hasPrev = false,
  hasNext = false,
  position,
  label,
}: LightboxProps) {
  const { t } = useI18n();
  const overlayRef = useRef<HTMLDivElement>(null);
  const isMouseDownOnBackdropRef = useRef(false);

  // Esc key stays on document-level so closing works even if focus moved
  // (see design.md §6 F1).
  // ArrowLeft / ArrowRight step through images when stepping is enabled.
  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key === "ArrowLeft" || event.key === "Left") {
        if (onPrev) {
          event.preventDefault();
          if (hasPrev) {
            onPrev();
          }
        }
      } else if (event.key === "ArrowRight" || event.key === "Right") {
        if (onNext) {
          event.preventDefault();
          if (hasNext) {
            onNext();
          }
        }
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose, onPrev, onNext, hasPrev, hasNext]);

  // Focus the scroll container and reset scroll position to top on open or when stepped.
  useEffect(() => {
    if (overlayRef.current) {
      overlayRef.current.scrollTop = 0;
      overlayRef.current.focus();
    }
  }, [src, position]);

  function handleMouseDown(e: React.MouseEvent<HTMLDivElement>) {
    if (e.target !== e.currentTarget || isEventOnScrollbar(e, e.currentTarget)) {
      isMouseDownOnBackdropRef.current = false;
      return;
    }
    isMouseDownOnBackdropRef.current = true;
  }

  function handleClick(e: React.MouseEvent<HTMLDivElement>) {
    if (
      e.target !== e.currentTarget ||
      !isMouseDownOnBackdropRef.current ||
      isEventOnScrollbar(e, e.currentTarget)
    ) {
      return;
    }
    onClose();
  }

  return (
    <div
      ref={overlayRef}
      tabIndex={-1}
      className="fixed inset-0 z-50 flex flex-col items-center p-4 overflow-y-auto overscroll-contain select-none focus:outline-none"
      style={{ background: "var(--scrim)" }}
      onMouseDown={handleMouseDown}
      onClick={handleClick}
    >
      {/* Position counter and label (evidence only) */}
      {position && (
        <div
          className="fixed top-4 left-1/2 -translate-x-1/2 z-10 flex max-w-[70vw] items-center gap-2 rounded-full px-3.5 py-1.5 text-xs text-white shadow pointer-events-none select-none"
          style={{ background: "rgba(0, 0, 0, 0.5)" }}
        >
          <span className="shrink-0 font-medium">{position}</span>
          {label && label.trim() !== "" && (
            <>
              <span className="shrink-0 opacity-50">·</span>
              <span className="truncate">{label.trim()}</span>
            </>
          )}
        </div>
      )}

      {/* Prev / Next buttons (evidence only) */}
      {onPrev && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            if (hasPrev) onPrev();
          }}
          disabled={!hasPrev}
          className="icon-btn fixed left-4 top-1/2 -translate-y-1/2 z-10 rounded-full p-2 text-white transition-opacity disabled:cursor-default disabled:opacity-30 enabled:cursor-pointer enabled:hover:opacity-80"
          style={{ background: "rgba(0, 0, 0, 0.5)" }}
          aria-label={t("lightbox.prev")}
          title={t("lightbox.prev")}
        >
          <ChevronLeftIcon size={20} />
        </button>
      )}

      {onNext && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            if (hasNext) onNext();
          }}
          disabled={!hasNext}
          className="icon-btn fixed right-4 top-1/2 -translate-y-1/2 z-10 rounded-full p-2 text-white transition-opacity disabled:cursor-default disabled:opacity-30 enabled:cursor-pointer enabled:hover:opacity-80"
          style={{ background: "rgba(0, 0, 0, 0.5)" }}
          aria-label={t("lightbox.next")}
          title={t("lightbox.next")}
        >
          <ChevronRightIcon size={20} />
        </button>
      )}

      <button
        type="button"
        onClick={onClose}
        className="icon-btn fixed top-4 right-4 z-10 cursor-pointer rounded-full p-2 text-white hover:opacity-80"
        style={{ background: "rgba(0, 0, 0, 0.5)" }}
        aria-label={t("lightbox.close")}
        title={t("lightbox.close")}
      >
        <XIcon size={18} />
      </button>

      <img
        src={src}
        alt={alt}
        onClick={(e) => e.stopPropagation()}
        className="my-auto max-w-[90vw] rounded shadow-2xl"
        style={{
          width: "auto",
          height: "auto",
        }}
      />
    </div>
  );
}
