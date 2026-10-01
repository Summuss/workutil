import { useEffect, useRef, useState } from "react";

import { BoxOverlay, useNaturalSize, type Box, type NaturalSize } from "./BoxOverlay";
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
  /** Where this image's block stands in its case, shown as `#7` after the
      position. Evidence passes it; memo has no such thing. */
  number?: string;
  label?: string | null;
  boxes?: Box[];
  boxSelectActive?: boolean;
  onToggleBoxSelect?: (active: boolean) => void;
  /**
   * Box mode saves through this: the whole set after a stroke, a delete or an
   * undo. Answers whether it was kept, so a refused change is not left as a
   * step to undo.
   */
  onChangeBoxes?: (boxes: Box[]) => Promise<boolean>;
  /** Why the last change to the boxes was refused, shown over the image. */
  error?: string | null;
}

/** Below this many screen pixels on either side, a drag is taken as a click. */
const MIN_DRAG_PX = 5;

/** How far outside a box's line, in screen pixels, a click still picks it. */
const HIT_SLACK_PX = 4;

/**
 * Where a pointer falls on an image, in pixels of the image file and clamped
 * to its edges, so a drag that leaves the picture ends on its border.
 */
function toImagePoint(
  clientX: number,
  clientY: number,
  rect: DOMRect,
  natural: NaturalSize,
): { x: number; y: number } {
  const clamp = (v: number, max: number) => Math.round(Math.max(0, Math.min(max, v)));
  return {
    x: clamp(((clientX - rect.left) / rect.width) * natural.w, natural.w),
    y: clamp(((clientY - rect.top) / rect.height) * natural.h, natural.h),
  };
}

/** The box spanned by two corners, whichever way the drag went. */
function spanned(a: { x: number; y: number }, b: { x: number; y: number }): Box {
  const x = Math.min(a.x, b.x);
  const y = Math.min(a.y, b.y);
  return { x, y, w: Math.max(a.x, b.x) - x, h: Math.max(a.y, b.y) - y };
}

/**
 * The box a click at `at` picks: the newest one where boxes overlap, since it
 * is drawn on top. `slack` widens each box so a click on its line counts.
 */
function boxAt(at: { x: number; y: number }, boxes: Box[], slack: number): number | null {
  for (let index = boxes.length - 1; index >= 0; index--) {
    const one = boxes[index];
    if (
      one &&
      at.x >= one.x - slack &&
      at.x <= one.x + one.w + slack &&
      at.y >= one.y - slack &&
      at.y <= one.y + one.h + slack
    ) {
      return index;
    }
  }
  return null;
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
 * - Box mode (evidence only, when onToggleBoxSelect is given): dragging on the image draws a red box,
 *   in pixels of the image file. Backdrop click does not close while it is on, so a drag released
 *   off the picture cannot close the lightbox. A click (no drag) on a box selects it, Delete or
 *   Backspace removes it, Ctrl/Cmd+Z undoes the last stroke or delete on this image.
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
  number,
  label,
  boxes,
  boxSelectActive = false,
  onToggleBoxSelect,
  onChangeBoxes,
  error,
}: LightboxProps) {
  const { t } = useI18n();
  const overlayRef = useRef<HTMLDivElement>(null);
  const isMouseDownOnBackdropRef = useRef(false);

  const imgRef = useRef<HTMLImageElement>(null);
  const { naturalSize, onLoad } = useNaturalSize(src);
  const [draftBox, setDraftBox] = useState<Box | null>(null);
  const isDraggingRef = useRef(false);
  const startPosRef = useRef<{ clientX: number; clientY: number } | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  // The sets this image's boxes had before each change made here, newest last.
  // Only for this image and this opening: undoing across images would have to
  // step back to the image too, which is more surprise than help.
  const historyRef = useRef<Box[][]>([]);
  const currentBoxes = boxes ?? [];

  // A drag in progress, a selection and the undo steps all belong to the
  // image they were made on.
  useEffect(() => {
    setDraftBox(null);
    setSelected(null);
    historyRef.current = [];
    isDraggingRef.current = false;
    startPosRef.current = null;
  }, [src]);

  function changeBoxes(next: Box[]) {
    const before = currentBoxes;
    setSelected(null);
    void onChangeBoxes?.(next).then((kept) => {
      if (kept) historyRef.current.push(before);
    });
  }

  // Esc key stays on document-level so closing works even if focus moved
  // (see design.md §6 F1).
  // Re-attached on every render, here and for the drag listeners below: the
  // handlers read the boxes, the pick and the undo steps as they are now,
  // and a dependency list naming all of them would change every render anyway.
  // ArrowLeft / ArrowRight step through images when stepping is enabled.
  useEffect(() => {
    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (boxSelectActive) {
        if ((event.key === "Delete" || event.key === "Backspace") && selected !== null) {
          event.preventDefault();
          changeBoxes(currentBoxes.filter((_, index) => index !== selected));
          return;
        }
        if (
          (event.ctrlKey || event.metaKey) &&
          !event.shiftKey &&
          event.key.toLowerCase() === "z"
        ) {
          event.preventDefault();
          // Not through `changeBoxes`: an undo must not become a step to undo,
          // and one that is refused stays available to try again.
          const previous = historyRef.current.pop();
          if (previous) {
            setSelected(null);
            void onChangeBoxes?.(previous).then((kept) => {
              if (!kept) historyRef.current.push(previous);
            });
          }
          return;
        }
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
  });

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
    // A drag that starts on the image and ends on the backdrop clicks their
    // common ancestor, which is this overlay.
    if (boxSelectActive) {
      return;
    }
    if (
      e.target !== e.currentTarget ||
      !isMouseDownOnBackdropRef.current ||
      isEventOnScrollbar(e, e.currentTarget)
    ) {
      return;
    }
    onClose();
  }

  function handleMouseDownImage(e: React.MouseEvent<HTMLImageElement>) {
    if (!boxSelectActive || e.button !== 0) return;
    e.preventDefault();
    e.stopPropagation();

    const img = imgRef.current;
    if (!img || !naturalSize) return;

    isDraggingRef.current = true;
    startPosRef.current = { clientX: e.clientX, clientY: e.clientY };
    setDraftBox(null);
  }

  useEffect(() => {
    if (!boxSelectActive) {
      isDraggingRef.current = false;
      startPosRef.current = null;
      setDraftBox(null);
      setSelected(null);
      return;
    }

    function draftTo(e: MouseEvent): Box | null {
      const start = startPosRef.current;
      const img = imgRef.current;
      if (!isDraggingRef.current || !start || !img || !naturalSize) return null;
      const rect = img.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return null;
      return spanned(
        toImagePoint(start.clientX, start.clientY, rect, naturalSize),
        toImagePoint(e.clientX, e.clientY, rect, naturalSize),
      );
    }

    function handleMouseMove(e: MouseEvent) {
      const box = draftTo(e);
      if (box) setDraftBox(box);
    }

    function handleMouseUp(e: MouseEvent) {
      const box = draftTo(e);
      const img = imgRef.current;
      isDraggingRef.current = false;
      startPosRef.current = null;
      setDraftBox(null);
      if (!box || !img || !naturalSize) return;

      // A drag shorter than a few screen pixels either way is a click, not a
      // box: measured on screen, since a long screenshot is drawn smaller
      // than it is and image pixels would let a twitch through.
      const rect = img.getBoundingClientRect();
      const screenW = (box.w / naturalSize.w) * rect.width;
      const screenH = (box.h / naturalSize.h) * rect.height;
      if (screenW < MIN_DRAG_PX || screenH < MIN_DRAG_PX) {
        // A click picks the box under it, or clears the pick.
        const at = toImagePoint(e.clientX, e.clientY, rect, naturalSize);
        setSelected(boxAt(at, currentBoxes, (HIT_SLACK_PX / rect.width) * naturalSize.w));
        return;
      }

      changeBoxes([...currentBoxes, box]);
    }

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  });

  return (
    <div
      ref={overlayRef}
      tabIndex={-1}
      className="fixed inset-0 z-50 flex flex-col items-center p-4 overflow-y-auto overscroll-contain select-none focus:outline-none"
      style={{ background: "var(--scrim)" }}
      onMouseDown={handleMouseDown}
      onClick={handleClick}
    >
      {/* Position counter, block number and label (evidence only) */}
      {position && (
        <div
          className="fixed top-4 left-1/2 -translate-x-1/2 z-10 flex max-w-[70vw] items-center gap-2 rounded-full px-3.5 py-1.5 text-xs text-white shadow pointer-events-none select-none"
          style={{ background: "rgba(0, 0, 0, 0.5)" }}
        >
          <span className="shrink-0 font-medium">{position}</span>
          {number && (
            <>
              <span className="shrink-0 opacity-50">·</span>
              <span className="shrink-0 tabular-nums" style={{ fontFamily: "var(--mono)" }}>
                {number}
              </span>
            </>
          )}
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

      <div className="fixed top-4 right-4 z-10 flex items-center gap-2">
        {onToggleBoxSelect && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleBoxSelect?.(!boxSelectActive);
            }}
            aria-pressed={boxSelectActive}
            className={`cursor-pointer rounded-full px-3.5 py-1.5 text-xs font-medium text-white ${
              boxSelectActive ? "ring-2 ring-white" : "opacity-80 hover:opacity-100"
            }`}
            style={{
              background: boxSelectActive ? "var(--danger)" : "rgba(0, 0, 0, 0.5)",
            }}
            title={t("evidence.box_select")}
          >
            {t("evidence.box_select")}
          </button>
        )}

        <button
          type="button"
          onClick={onClose}
          className="icon-btn cursor-pointer rounded-full p-2 text-white hover:opacity-80"
          style={{ background: "rgba(0, 0, 0, 0.5)" }}
          aria-label={t("lightbox.close")}
          title={t("lightbox.close")}
        >
          <XIcon size={18} />
        </button>
      </div>

      {error && (
        <div
          role="alert"
          className="fixed top-14 left-1/2 -translate-x-1/2 z-20 rounded-md px-3.5 py-1.5 text-xs text-white shadow-lg pointer-events-none select-none"
          style={{ background: "var(--danger)" }}
        >
          {error}
        </div>
      )}

      <div className="relative my-auto max-w-[90vw] shrink-0 select-none">
        <img
          ref={imgRef}
          src={src}
          alt={alt}
          draggable={!boxSelectActive}
          onClick={(e) => e.stopPropagation()}
          onMouseDown={handleMouseDownImage}
          onLoad={onLoad}
          className={`block max-w-full rounded shadow-2xl ${
            boxSelectActive ? "cursor-crosshair" : ""
          }`}
          style={{
            width: "auto",
            height: "auto",
          }}
        />
        <BoxOverlay
          boxes={draftBox ? [...currentBoxes, draftBox] : currentBoxes}
          selected={selected}
          naturalSize={naturalSize}
          strokeWidth={2}
        />
      </div>
    </div>
  );
}
