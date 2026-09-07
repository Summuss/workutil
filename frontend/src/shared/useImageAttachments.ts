import {
  useCallback,
  useRef,
  type ClipboardEvent,
  type DragEvent,
  type RefObject,
} from "react";

import type { ImageUpload } from "../features/memo/types";

interface PendingImage {
  id: string;
  file: File;
  dataUrl: string;
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/**
 * Screenshots pasted or dragged into a textarea.
 *
 * A pasted image stays in memory as a data URL behind a `temp:` placeholder
 * dropped at the cursor. Nothing reaches the disk until the body and every
 * image it still names go up in one request, so there is never an image on
 * the server belonging to a memo that was never written (spec 图片).
 *
 * These images are never rendered from here, so they live in a ref: they are
 * cargo for the next save, not state the screen is showing.
 */
export function useImageAttachments(
  textareaRef: RefObject<HTMLTextAreaElement | null>,
  onChangeText: (next: string) => void,
) {
  const pendingImages = useRef<PendingImage[]>([]);

  const insertImages = useCallback(
    async (files: File[]) => {
      if (files.length === 0) {
        return;
      }

      // Read the files before looking at the textarea. A big screenshot takes
      // long enough to type into, and where the cursor was when the paste
      // landed is not where it is when the bytes arrive.
      const loaded: PendingImage[] = await Promise.all(
        files.map(async (file, index) => ({
          id: `temp:img_${Date.now()}_${index}_${Math.random().toString(36).slice(2, 7)}`,
          file,
          dataUrl: await fileToDataUrl(file),
        })),
      );

      const element = textareaRef.current;
      const text = element ? element.value : "";
      const start = element ? element.selectionStart : text.length;
      const end = element ? element.selectionEnd : text.length;

      const onOwnLine = start === 0 || text.slice(0, start).endsWith("\n");
      const insert =
        (onOwnLine ? "" : "\n") +
        loaded.map((image) => `![image](${image.id})\n`).join("\n");

      pendingImages.current = [...pendingImages.current, ...loaded];
      onChangeText(text.slice(0, start) + insert + text.slice(end));

      requestAnimationFrame(() => {
        if (element) {
          element.focus();
          const caret = start + insert.length;
          element.setSelectionRange(caret, caret);
        }
      });
    },
    [textareaRef, onChangeText],
  );

  const handlePaste = useCallback(
    (event: ClipboardEvent<HTMLTextAreaElement>) => {
      const files = Array.from(event.clipboardData?.items ?? [])
        .filter((item) => item.type.startsWith("image/"))
        .map((item) => item.getAsFile())
        .filter((file): file is File => file !== null);

      if (files.length > 0) {
        event.preventDefault();
        void insertImages(files);
      }
    },
    [insertImages],
  );

  const handleDrop = useCallback(
    (event: DragEvent<HTMLTextAreaElement>) => {
      const files = Array.from(event.dataTransfer?.files ?? []).filter((file) =>
        file.type.startsWith("image/"),
      );
      if (files.length > 0) {
        event.preventDefault();
        void insertImages(files);
      }
    },
    [insertImages],
  );

  const handleDragOver = useCallback((event: DragEvent<HTMLTextAreaElement>) => {
    const hasImage = Array.from(event.dataTransfer?.items ?? []).some((item) =>
      item.type.startsWith("image/"),
    );
    if (hasImage) {
      event.preventDefault();
    }
  }, []);

  /** The images this text still names — the ones the save has to carry. */
  const getImagesForSave = useCallback(
    (textToSave: string): ImageUpload[] =>
      pendingImages.current
        .filter((image) => textToSave.includes(image.id))
        .map((image) => ({
          id: image.id,
          data: image.dataUrl,
          filename: image.file.name || "screenshot.png",
        })),
    [],
  );

  /**
   * Forget the images that just went to the server, and only those.
   *
   * Anything pasted while the save was in flight is still only in memory, and
   * dropping it would leave its placeholder in the body pointing at nothing.
   */
  const forgetSavedImages = useCallback((savedText: string) => {
    pendingImages.current = pendingImages.current.filter(
      (image) => !savedText.includes(image.id),
    );
  }, []);

  return {
    handlePaste,
    handleDrop,
    handleDragOver,
    getImagesForSave,
    forgetSavedImages,
  };
}
