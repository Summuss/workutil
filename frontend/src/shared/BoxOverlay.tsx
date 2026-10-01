import { useState, type SyntheticEvent } from "react";

/** A red box on a screenshot, in pixels of the image file (CONTEXT.md 红框). */
export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface NaturalSize {
  w: number;
  h: number;
}

/**
 * The size of the image file behind an `<img>`, known once it has loaded.
 *
 * Boxes are kept in the file's pixels so that no amount of shrinking on
 * screen moves them; drawing them needs that size as the frame to scale from.
 * The size is remembered against `src`, so when the same `<img>` is pointed
 * at another file (the lightbox stepping on) the old size is not used to draw
 * the new image's boxes while it loads.
 */
export function useNaturalSize(src: string | null): {
  naturalSize: NaturalSize | null;
  onLoad: (e: SyntheticEvent<HTMLImageElement>) => void;
} {
  const [loaded, setLoaded] = useState<{ src: string | null; size: NaturalSize } | null>(
    null,
  );
  return {
    naturalSize: loaded?.src === src ? loaded.size : null,
    onLoad: (e) =>
      setLoaded({
        src,
        size: { w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight },
      }),
  };
}

interface BoxOverlayProps {
  boxes: Box[];
  naturalSize: NaturalSize | null;
  strokeWidth: number;
}

/**
 * Red boxes laid over the `<img>` they belong to.
 *
 * The parent must be exactly the image's size (a `relative` wrapper with no
 * border or padding of its own): the SVG fills it, and its `viewBox` is the
 * image file, so the boxes scale with the picture however it is drawn. The
 * stroke does not scale — on a long screenshot shrunk into a card, a stroke
 * scaled with it would thin out to nothing.
 */
export function BoxOverlay({ boxes, naturalSize, strokeWidth }: BoxOverlayProps) {
  if (!naturalSize || boxes.length === 0) {
    return null;
  }

  return (
    <svg
      viewBox={`0 0 ${naturalSize.w} ${naturalSize.h}`}
      className="pointer-events-none absolute inset-0 h-full w-full overflow-visible"
    >
      {boxes.map((box, index) => (
        <rect
          key={index}
          x={box.x}
          y={box.y}
          width={box.w}
          height={box.h}
          fill="none"
          stroke="#FF0000"
          strokeWidth={strokeWidth}
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}
