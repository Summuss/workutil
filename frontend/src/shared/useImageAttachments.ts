import { useCallback, useRef, type RefObject } from "react";

import { imageDropHandlers, readImage, type ImageUpload } from "./images";
import { guardDuplicateImagePaste } from "./pasteDuplicateImage";

/**
 * Screenshots pasted or dragged into a textarea.
 *
 * A pasted image stays in memory as a data URL behind a `temp:` placeholder
 * dropped at the cursor. Nothing reaches the disk until the body and every
 * image it still names go up in one request, so there is never an image on
 * the server belonging to a memo that was never written (spec 图片).
 *
 * This is Memo's way and not Evidence's: a memo names its images from inside a
 * body of Markdown, so an image only exists once that body is saved. An
 * evidence block *is* one image, so it is posted the moment it is pasted.
 *
 * These images are never rendered from here, so they live in a ref: they are
 * cargo for the next save, not state the screen is showing.
 */
/**
 * A body with the screenshots it names taken out of it.
 *
 * For text coming back from storage. A pasted screenshot lives as a data URL
 * in memory behind a `temp:` placeholder and never reaches the disk until the
 * body is saved, so a draft that outlived the page names bytes that no longer
 * exist. Left in, the placeholder would be saved as literal text and the memo
 * would carry a broken image forever: `save_and_link` only rewrites the
 * placeholders an upload actually came with.
 *
 * What was typed is what survives; the pictures have to be pasted again.
 */
export function stripPendingImages(body: string): string {
  return body.replace(/!\[[^\]]*\]\(temp:[^)]*\)\n?/g, "");
}

export function useImageAttachments(
  textareaRef: RefObject<HTMLTextAreaElement | null>,
  onChangeText: (next: string) => void,
) {
  const pendingImages = useRef<ImageUpload[]>([]);

  const insertImages = useCallback(
    async (files: File[]) => {
      if (files.length === 0) {
        return;
      }

      const recordSuccess = await guardDuplicateImagePaste(files);
      if (!recordSuccess) {
        return;
      }

      // Read the files before looking at the textarea. A big screenshot takes
      // long enough to type into, and where the cursor was when the paste
      // landed is not where it is when the bytes arrive.
      const loaded: ImageUpload[] = await Promise.all(
        files.map(async (file, index) => ({
          id: `temp:img_${Date.now()}_${index}_${Math.random().toString(36).slice(2, 7)}`,
          ...(await readImage(file)),
        })),
      );

      await recordSuccess();

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

  const { onPaste, onDrop, onDragOver } = imageDropHandlers<HTMLTextAreaElement>(
    (files) => void insertImages(files),
  );

  /** The images this text still names — the ones the save has to carry. */
  const getImagesForSave = useCallback(
    (textToSave: string): ImageUpload[] =>
      pendingImages.current.filter((image) => textToSave.includes(image.id)),
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
    handlePaste: onPaste,
    handleDrop: onDrop,
    handleDragOver: onDragOver,
    getImagesForSave,
    forgetSavedImages,
  };
}
