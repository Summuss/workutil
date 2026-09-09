import { useEffect } from "react";

import { XIcon } from "./icons";

interface LightboxProps {
  src: string;
  alt?: string;
  onClose: () => void;
}

/**
 * Lightbox displaying the full-size image within viewport bounds:
 * - Esc key closes via document-level listener.
 * - Backdrop click closes.
 * - Top-right X button closes.
 * - Never scales image beyond its natural dimensions.
 */
export function Lightbox({ src, alt = "", onClose }: LightboxProps) {
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

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 select-none"
      style={{ background: "var(--scrim)" }}
      onClick={onClose}
    >
      <button
        type="button"
        onClick={onClose}
        className="icon-btn absolute top-4 right-4 z-10 cursor-pointer rounded-full p-2 text-white hover:opacity-80"
        style={{ background: "rgba(0, 0, 0, 0.5)" }}
        aria-label="Close"
      >
        <XIcon size={18} />
      </button>

      <img
        src={src}
        alt={alt}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[90vh] max-w-[90vw] rounded object-contain shadow-2xl"
        style={{
          width: "auto",
          height: "auto",
        }}
      />
    </div>
  );
}
