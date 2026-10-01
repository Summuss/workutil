import { useEffect, useRef } from "react";

import { XIcon } from "./icons";

interface LightboxProps {
  src: string;
  alt?: string;
  onClose: () => void;
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
 * - Backdrop click and top-right X button close; dragging/clicking scrollbar does not close.
 */
export function Lightbox({ src, alt = "", onClose }: LightboxProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const isMouseDownOnBackdropRef = useRef(false);

  // Esc key stays on document-level so closing works even if focus moved
  // (see design.md §6 F1).
  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  // Focus the scroll container and reset scroll position to top on open.
  useEffect(() => {
    if (overlayRef.current) {
      overlayRef.current.scrollTop = 0;
      overlayRef.current.focus();
    }
  }, [src]);

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
      <button
        type="button"
        onClick={onClose}
        className="icon-btn fixed top-4 right-4 z-10 cursor-pointer rounded-full p-2 text-white hover:opacity-80"
        style={{ background: "rgba(0, 0, 0, 0.5)" }}
        aria-label="Close"
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
