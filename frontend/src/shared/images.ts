import type { ClipboardEvent, DragEvent } from "react";

/**
 * Screenshots on their way out of the clipboard, still only data URLs.
 *
 * Mirrors `IncomingImage` / `ImageUpload` in `backend/app/core/images.py`, and
 * lives in `shared/` for the same reason that module does: Memo and Evidence
 * both paste screenshots and share this one wire shape and this one way of
 * getting files out of an event — the mechanism, not the concept (ADR-0001).
 */

/** A screenshot as the server takes it in. */
export interface IncomingImage {
  data: string;
  filename: string;
}

/** An incoming image that some text is holding a `temp:` place for. */
export interface ImageUpload extends IncomingImage {
  id: string;
}

function imageFiles(files: Iterable<File>): File[] {
  return Array.from(files).filter((file) => file.type.startsWith("image/"));
}

/**
 * The images in a paste.
 *
 * Read from `items` rather than `files`: a screenshot pasted from the system
 * clipboard is an item with no file behind it in some browsers, and this is
 * the path that has one either way.
 */
export function pastedImages(clipboard: DataTransfer | null): File[] {
  return imageFiles(
    Array.from(clipboard?.items ?? [])
      .filter((item) => item.type.startsWith("image/"))
      .map((item) => item.getAsFile())
      .filter((file): file is File => file !== null),
  );
}

/** The images in a drop — real files, so straight off `files`. */
export function droppedImages(transfer: DataTransfer | null): File[] {
  return imageFiles(transfer?.files ?? []);
}

/**
 * Whether a drag is carrying an image, for deciding to accept the drop.
 *
 * `files` is empty while a drag is still in the air, so this asks `items` —
 * which during a drag says the type and nothing else.
 */
export function carriesImage(transfer: DataTransfer | null): boolean {
  return Array.from(transfer?.items ?? []).some((item) =>
    item.type.startsWith("image/"),
  );
}

/** One file read into what the server takes. */
export function readImage(file: File): Promise<IncomingImage> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () =>
      resolve({
        data: reader.result as string,
        filename: file.name || "screenshot.png",
      });
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * The three handlers that turn a paste or a drop into image files.
 *
 * Which half of a `DataTransfer` to read depends on the event, and getting it
 * wrong fails silently — so it is decided once, here, rather than at each box
 * that accepts screenshots. Memo drops them into its body as placeholders and
 * Evidence posts them as blocks; what they share is only this translation.
 *
 * Not a hook: there is no state, and the handlers go straight onto an element.
 * Given no `onImages`, they do nothing and the paste stays an ordinary paste.
 */
export function imageDropHandlers<T extends HTMLElement>(
  onImages?: (files: File[]) => void,
) {
  function take(files: File[], event: { preventDefault: () => void }) {
    if (onImages && files.length > 0) {
      event.preventDefault();
      onImages(files);
    }
  }

  return {
    onPaste: (event: ClipboardEvent<T>) =>
      take(onImages ? pastedImages(event.clipboardData) : [], event),
    onDrop: (event: DragEvent<T>) =>
      take(onImages ? droppedImages(event.dataTransfer) : [], event),
    onDragOver: (event: DragEvent<T>) => {
      // Without this the browser refuses the drop and navigates to the file.
      if (onImages && carriesImage(event.dataTransfer)) {
        event.preventDefault();
      }
    },
  };
}
